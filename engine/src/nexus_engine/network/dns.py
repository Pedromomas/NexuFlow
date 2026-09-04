from __future__ import annotations

import asyncio
import ipaddress
import secrets
import socket
import statistics
import struct
import time
from dataclasses import dataclass

from ..anti_cheat import assert_mutation_allowed
from ..policy_runtime import assert_feature_enabled
from ..winexec import powershell_json, run_command


@dataclass(frozen=True, slots=True)
class DNSProvider:
    name: str
    servers: tuple[str, ...]


@dataclass(slots=True)
class DNSScore:
    provider: DNSProvider
    samples_ms: list[float | None]

    @property
    def successful(self) -> list[float]:
        return [x for x in self.samples_ms if x is not None]

    @property
    def success_rate(self) -> float:
        return len(self.successful) / len(self.samples_ms) if self.samples_ms else 0.0

    @property
    def median_ms(self) -> float | None:
        return float(statistics.median(self.successful)) if self.successful else None

    @property
    def score(self) -> float:
        return float("inf") if self.median_ms is None else self.median_ms + (1.0 - self.success_rate) * 150.0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider.name,
            "servers": list(self.provider.servers),
            "success_rate": round(self.success_rate, 3),
            "median_ms": None if self.median_ms is None else round(self.median_ms, 2),
            "score": None if self.score == float("inf") else round(self.score, 2),
        }


PUBLIC_PROVIDERS = (
    DNSProvider("Cloudflare", ("1.1.1.1", "1.0.0.1")),
    DNSProvider("Google", ("8.8.8.8", "8.8.4.4")),
    DNSProvider("Quad9", ("9.9.9.9", "149.112.112.112")),
)


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.rstrip(".").split("."):
        raw = label.encode("idna")
        if len(raw) > 63:
            raise ValueError("Invalid DNS label")
        out.append(len(raw)); out.extend(raw)
    out.append(0)
    return bytes(out)


def _query_latency(server: str, hostname: str, timeout: float = 1.0) -> float | None:
    address = ipaddress.ip_address(server)
    if address.version != 4:
        return None
    tx = secrets.randbelow(65536)
    packet = struct.pack("!HHHHHH", tx, 0x0100, 1, 0, 0, 0) + _encode_name(hostname) + struct.pack("!HH", 1, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.settimeout(timeout)
    try:
        started = time.perf_counter(); sock.sendto(packet, (str(address), 53)); response, source = sock.recvfrom(4096)
        elapsed = (time.perf_counter() - started) * 1000
        if len(response) < 12 or source != (str(address), 53):
            return None
        returned, flags = struct.unpack("!HH", response[:4])
        if returned != tx or not (flags & 0x8000) or (flags & 0xF) != 0:
            return None
        return elapsed
    except (OSError, TimeoutError, socket.timeout):
        return None
    finally:
        sock.close()


def _benchmark(provider: DNSProvider) -> DNSScore:
    samples = []
    for server in provider.servers:
        for hostname in ("example.com", "www.microsoft.com", "www.cloudflare.com"):
            samples.append(_query_latency(server, hostname))
    return DNSScore(provider, samples)


class DNSManager:
    @staticmethod
    def snapshot(interface_index: int, interface_guid: str) -> dict:
        guid = interface_guid if interface_guid.startswith("{") else "{" + interface_guid + "}"
        script = rf"""
$dns = Get-DnsClientServerAddress -InterfaceIndex {int(interface_index)} -AddressFamily IPv4 -ErrorAction Stop
$key = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{guid}'
$raw = (Get-ItemProperty -Path $key -Name NameServer -ErrorAction SilentlyContinue).NameServer
[PSCustomObject]@{{ InterfaceIndex={int(interface_index)}; InterfaceGuid='{guid}'; StaticConfigured=-not [string]::IsNullOrWhiteSpace([string]$raw); ServerAddresses=@($dns.ServerAddresses | Where-Object {{$_}}) }} | ConvertTo-Json -Depth 4 -Compress
"""
        return powershell_json(script)

    async def benchmark(self, current_servers: list[str]) -> list[DNSScore]:
        providers = list(PUBLIC_PROVIDERS)
        valid = []
        for value in current_servers:
            try:
                ip = ipaddress.ip_address(value)
                if ip.version == 4:
                    valid.append(str(ip))
            except ValueError:
                pass
        if valid:
            providers.insert(0, DNSProvider("Current", tuple(valid)))
        return list(await asyncio.gather(*(asyncio.to_thread(_benchmark, p) for p in providers)))

    @staticmethod
    def select_best(scores: list[DNSScore], minimum_improvement_ms: float = 3.0) -> DNSProvider | None:
        viable = [s for s in scores if s.success_rate >= 0.75 and s.median_ms is not None]
        if not viable:
            return None
        winner = min(viable, key=lambda x: x.score)
        current = next((x for x in viable if x.provider.name == "Current"), None)
        if winner.provider.name == "Current":
            return None
        if current is not None and current.score - winner.score < minimum_improvement_ms:
            return None
        return winner.provider

    @staticmethod
    def apply(interface_index: int, provider: DNSProvider) -> None:
        assert_mutation_allowed("dns_mutation")
        assert_feature_enabled("dns_apply")
        servers = [str(ipaddress.ip_address(x)) for x in provider.servers]
        args = ",".join(f"'{x}'" for x in servers)
        powershell_json(rf"Set-DnsClientServerAddress -InterfaceIndex {int(interface_index)} -ServerAddresses @({args}) -ErrorAction Stop; @{{ok=$true}} | ConvertTo-Json -Compress")
        run_command(["ipconfig", "/flushdns"], check=False)

    @staticmethod
    def restore(snapshot: dict) -> None:
        index = int(snapshot["InterfaceIndex"])
        servers = [str(ipaddress.ip_address(x)) for x in snapshot.get("ServerAddresses", [])]
        if snapshot.get("StaticConfigured") and servers:
            run_command([
                "netsh", "interface", "ipv4", "set", "dnsservers",
                f"name={index}", "source=static", f"address={servers[0]}",
                "register=primary", "validate=no",
            ])
            for order, server in enumerate(servers[1:], start=2):
                run_command([
                    "netsh", "interface", "ipv4", "add", "dnsservers",
                    f"name={index}", f"address={server}", f"index={order}", "validate=no",
                ])
        else:
            run_command([
                "netsh", "interface", "ipv4", "set", "dnsservers",
                f"name={index}", "source=dhcp",
            ])
        run_command(["ipconfig", "/flushdns"], check=False)
