from __future__ import annotations

import hashlib
import ipaddress
from pathlib import Path

from ..anti_cheat import assert_mutation_allowed
from ..policy_runtime import assert_feature_enabled
from ..winexec import run_command


class FirewallManager:
    PREFIX = "NexuFlow"
    MAX_IPS_PER_RULE = 48

    @staticmethod
    def _chunks(values: list[str], size: int):
        for i in range(0, len(values), size):
            yield values[i:i + size]

    def prepare(self, game_id: str, pool_id: str, program: str, remote_ips: list[str]) -> list[dict]:
        assert_mutation_allowed("endpoint_firewall_steering", game_id=game_id)
        assert_feature_enabled("endpoint_steering")
        exe = Path(program).resolve()
        if not exe.is_file():
            raise FileNotFoundError(exe)
        ips: list[str] = []
        for value in remote_ips:
            parsed = ipaddress.ip_address(value)
            if parsed.version != 4:
                raise ValueError("Firewall endpoint steering currently supports IPv4 only")
            ips.append(str(parsed))
        ips = sorted(set(ips))
        rules = []
        for chunk in self._chunks(ips, self.MAX_IPS_PER_RULE):
            digest = hashlib.sha256((game_id + pool_id + str(exe) + ",".join(chunk)).encode()).hexdigest()[:10]
            rules.append({"name": f"{self.PREFIX}::{game_id}::{pool_id}::{digest}", "game_id": game_id, "program": str(exe), "ips": chunk})
        return rules

    @staticmethod
    def delete(name: str) -> None:
        # Rollback state is persistent input. Only a NexuFlow-generated rule may
        # be removed, and netsh is used directly so a protected transition never
        # needs to start PowerShell.
        safe = str(name)
        if not safe.startswith(FirewallManager.PREFIX + "::") or len(safe) > 240:
            raise ValueError("Refusing to delete a non-NexuFlow firewall rule")
        run_command(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={safe}"],
            check=False,
        )

    def apply(self, rule: dict) -> None:
        assert_mutation_allowed("endpoint_firewall_steering", game_id=str(rule.get("game_id") or ""))
        assert_feature_enabled("endpoint_steering")
        self.delete(rule["name"])
        run_command([
            "netsh", "advfirewall", "firewall", "add", "rule", f"name={rule['name']}",
            "dir=out", "action=block", "protocol=any", f"program={rule['program']}",
            "remoteip=" + ",".join(rule["ips"]), "profile=any", "enable=yes",
        ])
