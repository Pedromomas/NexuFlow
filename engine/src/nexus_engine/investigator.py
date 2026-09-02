from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path

from .network.allowlist import network_contract


_LOCK = threading.RLock()
_MAX_EVENTS = 500


def _event_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    else:
        base = Path(tempfile.gettempdir())
    return base / "NexuFlow" / "investigator" / "events.jsonl"


def _safe_target(target: object) -> str:
    value = str(target or "").strip()
    home = str(Path.home())
    if home and home.lower() in value.lower():
        value = value.lower().replace(home.lower(), "%USERPROFILE%")
    return value[:240]


def record_event(
    category: str,
    action: str,
    target: object,
    *,
    result: str = "ok",
    details: str = "",
    session_id: str | None = None,
) -> None:
    event = {
        "timestamp": int(time.time() * 1000),
        "category": str(category)[:32],
        "action": str(action)[:80],
        "target": _safe_target(target),
        "result": str(result)[:24],
        "details": str(details)[:280],
        "session_id": str(session_id) if session_id else None,
    }
    path = _event_path()
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[str] = []
        try:
            existing = path.read_text(encoding="utf-8").splitlines()[-(_MAX_EVENTS - 1):]
        except OSError:
            pass
        existing.append(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        tmp = path.with_suffix(".tmp")
        tmp.write_text("\n".join(existing) + "\n", encoding="utf-8")
        tmp.replace(path)


def investigator_snapshot(limit: int = 100) -> dict:
    limit = max(1, min(200, int(limit)))
    events: list[dict] = []
    path = _event_path()
    with _LOCK:
        try:
            for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        events.append(item)
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass
    return {
        "schema": 1,
        "read_only": True,
        "scope": "Operações iniciadas pelo NexuFlow; não é um monitor global do Windows.",
        "privacy": "Registro local, sanitizado e sem conteúdo de arquivos pessoais.",
        "network_contract": network_contract(),
        "events": list(reversed(events)),
    }
