from __future__ import annotations

import json
import os

from app import _bootstrap  # noqa: F401
from nexus_engine.anti_cheat import running_protected_games
from nexus_engine.network.interfaces import InterfaceManager
from nexus_engine.network.tcp_tweaks import TcpTweaks
from nexus_engine.state import program_data_dir


class TcpTweaksService:
    def __init__(self) -> None:
        self.state_path = program_data_dir() / "state" / "manual-tcp.json"

    def snapshot(self) -> list[dict]:
        interface = InterfaceManager.primary_ipv4()
        return TcpTweaks(interface.guid).snapshot()

    def apply(self) -> dict:
        protected = running_protected_games()
        if protected:
            raise RuntimeError("TCP registry tweaks are disabled while anti-cheat protected games are running: " + ", ".join(protected))
        if os.name != "nt":
            raise RuntimeError("TCP registry mutation requires Windows")
        if self.state_path.exists():
            raise RuntimeError("A manual TCP snapshot already exists. Revert it before applying another change.")

        interface = InterfaceManager.primary_ipv4()
        tweaks = TcpTweaks(interface.guid)
        snapshot = tweaks.snapshot()
        self._save({"interface_guid": interface.guid, "snapshot": snapshot})
        try:
            tweaks.apply()
        except Exception:
            self.state_path.unlink(missing_ok=True)
            raise
        return {"changed": True, "interface": interface.alias}

    def revert(self) -> dict:
        state = self._load()
        if not state:
            return {"restored": False, "message": "No manual TCP snapshot"}
        TcpTweaks.restore(state.get("snapshot", []))
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
