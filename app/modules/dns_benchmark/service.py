from __future__ import annotations

import asyncio
import json
import os

from app import _bootstrap  # noqa: F401
from nexus_engine.anti_cheat import running_protected_games
from nexus_engine.network.dns import DNSManager
from nexus_engine.network.interfaces import InterfaceManager
from nexus_engine.state import program_data_dir


class DNSBenchmarkService:
    def __init__(self) -> None:
        self.manager = DNSManager()
        self.state_path = program_data_dir() / "state" / "manual-dns.json"

    async def benchmark(self) -> dict:
        protected = running_protected_games()
        if protected:
            scores = await self.manager.benchmark([])
            public_winner = min(
                (score for score in scores if score.median_ms is not None and score.success_rate >= 0.75),
                key=lambda score: score.score,
                default=None,
            )
            return {
                "interface": {"deferred": True, "reason": "protected_game_no_powershell"},
                "current": [],
                "current_queried": False,
                "winner": public_winner.provider.name if public_winner else None,
                "diagnostic_only": True,
                "protected_games": protected,
                "benchmarks": [score.to_dict() for score in scores],
            }

        interface = InterfaceManager.primary_ipv4()
        snapshot = self.manager.snapshot(interface.index, interface.guid) if os.name == "nt" else {
            "InterfaceIndex": interface.index,
            "InterfaceGuid": interface.guid,
            "ServerAddresses": [],
            "StaticConfigured": False,
        }
        scores = await self.manager.benchmark(snapshot.get("ServerAddresses", []))
        winner = self.manager.select_best(scores)
        return {
            "interface": {
                "index": interface.index,
                "alias": interface.alias,
                "description": interface.description,
                "mtu": interface.mtu,
            },
            "current": snapshot.get("ServerAddresses", []),
            "winner": winner.name if winner else "Current",
            "benchmarks": [score.to_dict() for score in scores],
        }

    def apply_best(self) -> dict:
        return asyncio.run(self._apply_best())

    async def _apply_best(self) -> dict:
        protected = running_protected_games()
        if protected:
            raise RuntimeError("Live DNS mutation is disabled while anti-cheat protected games are running: " + ", ".join(protected))
        if os.name != "nt":
            raise RuntimeError("DNS mutation requires Windows")
        if self.state_path.exists():
            raise RuntimeError("A manual DNS snapshot already exists. Restore it before applying another change.")

        interface = InterfaceManager.primary_ipv4()
        if interface.probably_virtual or interface.network_category == "DomainAuthenticated":
            raise RuntimeError("DNS mutation skipped on virtual/VPN/domain-managed interface")

        snapshot = self.manager.snapshot(interface.index, interface.guid)
        scores = await self.manager.benchmark(snapshot.get("ServerAddresses", []))
        winner = self.manager.select_best(scores)
        if not winner:
            return {"changed": False, "winner": "Current", "benchmarks": [s.to_dict() for s in scores]}

        self._save({"snapshot": snapshot, "winner": winner.name})
        try:
            self.manager.apply(interface.index, winner)
        except Exception:
            self.state_path.unlink(missing_ok=True)
            raise
        return {"changed": True, "winner": winner.name, "benchmarks": [s.to_dict() for s in scores]}

    def restore(self) -> dict:
        state = self._load()
        if not state:
            return {"restored": False, "message": "No manual DNS snapshot"}
        self.manager.restore(state["snapshot"])
        self.state_path.unlink(missing_ok=True)
        return {"restored": True}

    def _load(self) -> dict | None:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _save(self, data: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)
