from __future__ import annotations

import os

from app import _bootstrap  # noqa: F401
from nexus_engine.admin import require_admin
from nexus_engine.anti_cheat import assert_mutation_allowed, running_protected_games
from nexus_engine.winexec import run_command


class NetworkFlushService:
    """
    Explicit recovery tool. It is never called by BOOST automatically because
    release/renew and IP/Winsock reset can interrupt active network sessions.
    """

    def execute(self, *, confirm_disconnect: bool, include_ip_reset: bool = False) -> dict:
        assert_mutation_allowed("network_reset")
        protected = running_protected_games()
        if protected:
            raise RuntimeError("Network reset is disabled while anti-cheat protected games are running: " + ", ".join(protected))
        if os.name != "nt":
            return {"ok": False, "reason": "Windows only", "steps": [], "restart_required": False}
        require_admin()
        if not confirm_disconnect:
            raise ValueError("confirm_disconnect=true is required for network reset operations")

        commands: list[tuple[str, list[str], bool]] = [
            ("flushdns", ["ipconfig", "/flushdns"], False),
            ("release", ["ipconfig", "/release"], False),
            ("renew", ["ipconfig", "/renew"], False),
            ("winsock_reset", ["netsh", "winsock", "reset"], True),
        ]
        if include_ip_reset:
            commands.append(("ip_reset", ["netsh", "int", "ip", "reset"], True))

        steps: list[dict] = []
        restart_required = False
        for name, command, reboot_on_success in commands:
            try:
                result = run_command(command, check=False)
                ok = result.returncode == 0
                steps.append({
                    "name": name,
                    "ok": ok,
                    "returncode": result.returncode,
                    "stdout": result.stdout[-1500:],
                    "stderr": result.stderr[-1500:],
                })
                restart_required = restart_required or (ok and reboot_on_success)
            except Exception as exc:
                steps.append({"name": name, "ok": False, "error": str(exc)})

        return {
            "ok": any(step.get("ok") for step in steps),
            "steps": steps,
            "restart_required": restart_required,
        }
