from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandExecutionError(RuntimeError):
    pass


class ProtectedPowerShellError(CommandExecutionError):
    """Raised before PowerShell can start during a protected session."""


_POWERSHELL_EXECUTABLES = frozenset({"powershell", "powershell.exe", "pwsh", "pwsh.exe"})
_PROTECTED_STATE_PROFILES = frozenset({
    "riot_safe",
    "valve_safe",
    "protected_safe",
    "unknown_safe",
    "hardcore_safe",
})


def _protected_session_active() -> bool:
    """Fail closed on live protection signals or an active protected snapshot.

    Imports stay local to keep the low-level command runner free of import
    cycles. Reading the snapshot never contacts a game or anti-cheat process.
    """
    try:
        from .anti_cheat import running_protected_games

        if running_protected_games():
            return True
    except Exception:
        # A process enumeration failure alone is not proof that gameplay is
        # active. The persistent session snapshot below remains a second signal.
        pass

    try:
        from .state import StateStore

        state = StateStore().load()
        profile = str(state.get("profile") or "").strip().lower()
        return bool(state.get("active") and profile in _PROTECTED_STATE_PROFILES)
    except Exception:
        return False


def _assert_command_allowed(args: Sequence[str]) -> None:
    if not args:
        raise ValueError("Command cannot be empty")
    executable = Path(str(args[0])).name.lower()
    if executable in _POWERSHELL_EXECUTABLES and _protected_session_active():
        raise ProtectedPowerShellError(
            "PowerShell is disabled while an anti-cheat protected session is active"
        )


def run_command(args: Sequence[str], *, check: bool = True, timeout: float = 20.0) -> CommandResult:
    _assert_command_allowed(args)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.run(list(args), capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False, creationflags=flags, timeout=timeout)
    result = CommandResult(proc.returncode, proc.stdout, proc.stderr)
    if check and proc.returncode != 0:
        raise CommandExecutionError(f"Command failed ({proc.returncode}): {args!r}\n{proc.stderr or proc.stdout}")
    return result


def powershell(script: str, *, check: bool = True, timeout: float = 20.0) -> CommandResult:
    if os.name != "nt":
        raise OSError("PowerShell Windows operation requested on non-Windows platform")
    wrapped = "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script
    return run_command(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", wrapped], check=check, timeout=timeout)


def powershell_json(script: str, *, timeout: float = 20.0):
    output = powershell(script, timeout=timeout).stdout.strip()
    return None if not output else json.loads(output)
