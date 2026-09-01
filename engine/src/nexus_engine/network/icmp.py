from __future__ import annotations

import asyncio
import ctypes
import os
import socket
import struct
from ctypes import wintypes

from ..models import Endpoint, ProbeStats

IP_SUCCESS = 0
IP_REQ_TIMED_OUT = 11010
IP_TTL_EXPIRED_TRANSIT = 11013
IP_TTL_EXPIRED_REASSEM = 11014
IP_FLAG_DF = 2


class IP_OPTION_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Ttl", ctypes.c_ubyte),
        ("Tos", ctypes.c_ubyte),
        ("Flags", ctypes.c_ubyte),
        ("OptionsSize", ctypes.c_ubyte),
        ("OptionsData", ctypes.c_void_p),
    ]


class ICMP_ECHO_REPLY(ctypes.Structure):
    _fields_ = [
        ("Address", ctypes.c_uint32),
        ("Status", ctypes.c_uint32),
        ("RoundTripTime", ctypes.c_uint32),
        ("DataSize", ctypes.c_uint16),
        ("Reserved", ctypes.c_uint16),
        ("Data", ctypes.c_void_p),
        ("Options", IP_OPTION_INFORMATION),
    ]


def _address_from_u32(value: int) -> str | None:
    if not value:
        return None
    try:
        return socket.inet_ntoa(struct.pack("=I", value))
    except (OSError, struct.error):
        return None


def icmp_echo_detail(
    ip: str,
    timeout_ms: int = 700,
    payload_size: int = 16,
    dont_fragment: bool = False,
    ttl: int = 128,
) -> dict:
    """Perform an ICMPv4 echo and return status/address/RTT details.

    The TTL parameter is used by the read-only route diagnostic engine. On
    Windows this calls the documented IP Helper ICMP API; it does not inspect,
    intercept, or modify game packets.
    """
    ttl = max(1, min(255, int(ttl)))
    if os.name != "nt":
        # Cross-platform fallback is intentionally limited to destination RTT;
        # route tracing itself is Windows-only in NexuFlow.
        try:
            import time
            start = time.perf_counter()
            with socket.create_connection((ip, 443), timeout=timeout_ms / 1000):
                pass
            return {
                "latency_ms": (time.perf_counter() - start) * 1000,
                "status": IP_SUCCESS,
                "address": ip,
                "ttl": ttl,
            }
        except OSError:
            return {"latency_ms": None, "status": None, "address": None, "ttl": ttl}

    dll = ctypes.WinDLL("iphlpapi.dll")
    dll.IcmpCreateFile.restype = wintypes.HANDLE
    dll.IcmpSendEcho.argtypes = [
        wintypes.HANDLE,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.POINTER(IP_OPTION_INFORMATION),
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    dll.IcmpSendEcho.restype = ctypes.c_uint32
    dll.IcmpCloseHandle.argtypes = [wintypes.HANDLE]

    handle = dll.IcmpCreateFile()
    if handle == ctypes.c_void_p(-1).value:
        return {"latency_ms": None, "status": None, "address": None, "ttl": ttl}

    try:
        destination = struct.unpack("=I", socket.inet_aton(ip))[0]
        payload_size = max(1, min(int(payload_size), 65500))
        payload = ctypes.create_string_buffer(b"N" * payload_size)
        reply_size = ctypes.sizeof(ICMP_ECHO_REPLY) + payload_size + 64
        reply_buffer = ctypes.create_string_buffer(reply_size)
        options = IP_OPTION_INFORMATION(ttl, 0, IP_FLAG_DF if dont_fragment else 0, 0, None)
        count = dll.IcmpSendEcho(
            handle,
            destination,
            payload,
            payload_size,
            ctypes.byref(options),
            reply_buffer,
            reply_size,
            timeout_ms,
        )
        if count == 0:
            return {"latency_ms": None, "status": None, "address": None, "ttl": ttl}
        reply = ICMP_ECHO_REPLY.from_buffer_copy(reply_buffer)
        status = int(reply.Status)
        rtt = float(reply.RoundTripTime)
        return {
            "latency_ms": rtt if status in {IP_SUCCESS, IP_TTL_EXPIRED_TRANSIT, IP_TTL_EXPIRED_REASSEM} else None,
            "status": status,
            "address": _address_from_u32(int(reply.Address)),
            "ttl": ttl,
        }
    finally:
        dll.IcmpCloseHandle(handle)


def icmp_echo_ipv4(
    ip: str,
    timeout_ms: int = 700,
    payload_size: int = 16,
    dont_fragment: bool = False,
) -> tuple[float | None, int | None]:
    detail = icmp_echo_detail(ip, timeout_ms, payload_size, dont_fragment, 128)
    return detail["latency_ms"] if detail.get("status") == IP_SUCCESS else None, detail.get("status")


async def probe_endpoint(endpoint: Endpoint, attempts: int = 5, timeout_ms: int = 700) -> ProbeStats:
    samples: list[float | None] = []
    for _ in range(attempts):
        latency, _ = await asyncio.to_thread(icmp_echo_ipv4, endpoint.ip, timeout_ms, 16, False)
        samples.append(latency)
        await asyncio.sleep(0.035)
    return ProbeStats(endpoint, samples)


async def probe_many(
    endpoints: tuple[Endpoint, ...],
    attempts: int = 5,
    timeout_ms: int = 700,
    concurrency: int = 20,
) -> list[ProbeStats]:
    sem = asyncio.Semaphore(concurrency)

    async def one(ep: Endpoint):
        async with sem:
            return await probe_endpoint(ep, attempts, timeout_ms)

    return list(await asyncio.gather(*(one(ep) for ep in endpoints)))
