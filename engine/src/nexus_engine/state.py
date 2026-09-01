from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from pathlib import Path


_lock = threading.RLock()


def _base_program_data() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
    return Path(tempfile.gettempdir())


def program_data_dir() -> Path:
    """
    Current persistent state root.

    On first run, migrate a previous NexusBooster state directory when possible
    so an interrupted older boost can still be rolled back by NexuFlow.
    """
    base = _base_program_data()
    current = base / "NexuFlow"
    legacy = base / "NexusBooster"

    if not current.exists() and legacy.exists():
        try:
            current.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(legacy, current, dirs_exist_ok=True)
        except OSError:
            # Rollback safety is more important than branding. Fall back to the
            # legacy directory if migration is denied.
            return legacy
    return current


def pending_manual_state() -> list[str]:
    """Return manual FastAPI rollback files that must be resolved before BOOST."""
    names = ("manual-dns.json", "manual-tcp.json", "manual-process.json", "api-route-rules.json")
    state_dir = program_data_dir() / "state"
    return [name for name in names if (state_dir / name).exists()]


class StateStore:
    def __init__(self, path: Path | None = None):
        self.path = path or program_data_dir() / "state" / "boost-state.json"

    def load(self) -> dict:
        with _lock:
            candidates = (self.path, self.path.with_suffix(self.path.suffix + ".bak"))
            saw_corrupt = False
            for candidate in candidates:
                if not candidate.exists():
                    continue
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        if saw_corrupt:
                            data["recovered_from_backup"] = True
                        return data
                except (OSError, json.JSONDecodeError):
                    saw_corrupt = True
            return {"schema": 2, "active": False, "corrupt_state_detected": saw_corrupt}

    def save(self, state: dict) -> None:
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            backup = self.path.with_suffix(self.path.suffix + ".bak")
            tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
            if self.path.exists():
                try:
                    backup.write_bytes(self.path.read_bytes())
                except OSError:
                    pass
            tmp.replace(self.path)

    def clear(self) -> None:
        self.save({"schema": 2, "active": False})
        try:
            self.path.with_suffix(self.path.suffix + ".bak").unlink(missing_ok=True)
        except OSError:
            pass


def daemon_file() -> Path:
    return program_data_dir() / "state" / "daemon.json"


def stop_file() -> Path:
    # Stop is deliberately a user-writable one-way signal. A medium-integrity
    # process may request rollback, but it cannot use this channel to apply new
    # privileged mutations. Keeping it in LOCALAPPDATA lets the desktop app
    # disable an active boost without another UAC prompt.
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    else:
        base = Path(tempfile.gettempdir())
    return base / "NexuFlow" / "control" / "stop.request"
