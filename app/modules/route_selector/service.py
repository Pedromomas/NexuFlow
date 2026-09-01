from __future__ import annotations

import concurrent.futures
import ipaddress
import json
import statistics
from pathlib import Path

from app import _bootstrap  # noqa: F401
from nexus_engine.anti_cheat import is_protected_game
from nexus_engine.network.firewall import FirewallManager
from nexus_engine.network.icmp import icmp_echo_ipv4
from nexus_engine.state import program_data_dir


class RouteSelectorService:
    """
    Endpoint selector, not a BGP route optimizer.

    Firewall steering is only allowed when the caller explicitly confirms that
    all supplied endpoints are functionally interchangeable.
    """

    def __init__(self) -> None:
        self.firewall = FirewallManager()
        self.state_path = program_data_dir() / "state" / "api-route-rules.json"

    @staticmethod
    def _validated_ips(values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            parsed = ipaddress.ip_address(value)
            if parsed.version != 4:
                raise ValueError("Only IPv4 endpoints are supported")
            normalized = str(parsed)
            if normalized not in result:
                result.append(normalized)
        if len(result) < 2:
            raise ValueError("At least two unique IPv4 endpoints are required")
        if len(result) > 64:
            raise ValueError("At most 64 endpoints are accepted")
        return result

    @staticmethod
    def _probe_one(ip: str, attempts: int) -> dict:
        samples: list[float | None] = []
        for _ in range(attempts):
            latency, _status = icmp_echo_ipv4(ip, 800, 16, False)
            samples.append(latency)
        successes = [x for x in samples if x is not None]
        return {
            "ip": ip,
            "samples_ms": [None if x is None else round(x, 2) for x in samples],
            "received": len(successes),
            "loss_percent": round((1 - len(successes) / attempts) * 100, 2),
            "median_ms": round(statistics.median(successes), 2) if successes else None,
        }

    def benchmark(self, ips: list[str], attempts: int = 4) -> list[dict]:
        validated = self._validated_ips(ips)
        attempts = max(2, min(int(attempts), 10))
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, len(validated))) as pool:
            return list(pool.map(lambda ip: self._probe_one(ip, attempts), validated))

    def apply_best(
        self,
        *,
        game_id: str,
        program: str,
        ips: list[str],
        attempts: int = 4,
        interchangeable: bool,
        confirmed: bool,
        keep_best: int = 1,
    ) -> dict:
        if is_protected_game(game_id):
            raise ValueError("Endpoint firewall steering is disabled for Riot/Vanguard and CS2/VAC protected games")
        if not interchangeable or not confirmed:
            raise ValueError("Firewall steering requires interchangeable=true and confirmed=true")

        results = self.benchmark(ips, attempts)
        comparable = [r for r in results if r["received"] >= max(2, attempts // 2) and r["median_ms"] is not None]
        if len(comparable) < 2:
            return {"changed": False, "reason": "Insufficient comparable ICMP responders", "benchmarks": results}

        comparable.sort(key=lambda item: (item["loss_percent"], item["median_ms"]))
        keep = {r["ip"] for r in comparable[: max(1, min(keep_best, len(comparable) - 1))]}
        blocked = [r["ip"] for r in comparable if r["ip"] not in keep]

        rules = self.firewall.prepare(game_id, "api-steering", program, blocked)
        if self._load_state():
            raise RuntimeError("Manual route steering rules are already tracked. Restore them before applying a new selection.")

        # Checkpoint every intended rule before touching Windows Firewall. If the
        # process crashes after the first rule, the restore endpoint still knows
        # every name it may need to remove. Deleting a non-existent rule is
        # intentionally idempotent.
        state = [
            {"name": rule["name"], "game_id": game_id, "program": program}
            for rule in rules
        ]
        self._save_state(state)
        for rule in rules:
            self.firewall.apply(rule)

        return {
            "changed": bool(rules),
            "kept": sorted(keep),
            "blocked": blocked,
            "benchmarks": results,
            "rules": [rule["name"] for rule in rules],
        }

    def restore(self) -> dict:
        state = self._load_state()
        removed: list[str] = []
        for item in state:
            name = str(item.get("name", ""))
            if name:
                self.firewall.delete(name)
                removed.append(name)
        self._save_state([])
        return {"restored": True, "removed": removed}

    def _load_state(self) -> list[dict]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_state(self, state: list[dict]) -> None:
        if not state:
            self.state_path.unlink(missing_ok=True)
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)
