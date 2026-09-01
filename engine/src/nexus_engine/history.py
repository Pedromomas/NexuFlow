from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path

from .network.quality import quality_delta

_HISTORY_LOCK = threading.RLock()


def _history_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    else:
        base = Path(tempfile.gettempdir())
    return base / "NexuFlow" / "history" / "sessions.json"


class SessionHistory:
    def __init__(self, path: Path | None = None, max_sessions: int = 200) -> None:
        self.path = path or _history_path()
        self.max_sessions = max(20, int(max_sessions))

    def _load_unlocked(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def list(self, limit: int = 50) -> list[dict]:
        with _HISTORY_LOCK:
            data = self._load_unlocked()
        return list(reversed(data[-max(1, min(200, int(limit))) :]))

    def append(self, record: dict) -> bool:
        session_id = str(record.get("session_id") or "")
        if not session_id:
            raise ValueError("History record requires session_id")
        with _HISTORY_LOCK:
            data = self._load_unlocked()
            if any(str(x.get("session_id")) == session_id for x in data):
                return False
            data.append(record)
            data = data[-self.max_sessions :]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
        return True

    def record_state(self, state: dict, *, ended_at: float | None = None) -> dict:
        ended = float(ended_at if ended_at is not None else time.time())
        before = state.get("quality_before")
        after = state.get("quality_after")
        record = {
            "session_id": state.get("session_id"),
            "game": state.get("game"),
            "requested_profile": state.get("requested_profile"),
            "effective_profile": state.get("profile"),
            "objective_mode": state.get("objective_mode"),
            "anti_cheat": state.get("anti_cheat"),
            "started_at": state.get("started_at"),
            "ended_at": ended,
            "duration_seconds": round(max(0.0, ended - float(state.get("started_at") or ended)), 1),
            "quality_before": before,
            "quality_after": after,
            "quality_delta": quality_delta(before, after),
            "adaptive_events": state.get("adaptive_events", []),
            "gaming_health_before": state.get("gaming_health_before"),
            "gaming_health_after": state.get("gaming_health_after"),
            # FPS intentionally remains null until a non-invasive, anti-cheat-safe
            # source is integrated. NexuFlow will not hook graphics APIs just to
            # populate this field.
            "fps_average": None,
            "fps_source": "not_collected_to_avoid_game_hooks",
            "warnings": state.get("warnings", []),
        }
        self.append(record)
        return record
