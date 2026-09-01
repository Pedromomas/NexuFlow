from __future__ import annotations

import hmac
import os
import secrets
from pathlib import Path

from fastapi import Header, HTTPException, status


def _token_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    return base / "NexuFlow" / "api-token.txt"


def load_or_create_token() -> str:
    env_token = os.environ.get("NEXUFLOW_API_TOKEN", "").strip()
    if env_token:
        return env_token

    path = _token_path()
    try:
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if len(value) >= 32:
                return value
        path.parent.mkdir(parents=True, exist_ok=True)
        token = secrets.token_urlsafe(36)
        path.write_text(token, encoding="utf-8")
        return token
    except OSError:
        # Ephemeral fallback. The launch script exposes it to the current session.
        return secrets.token_urlsafe(36)


API_TOKEN = load_or_create_token()


def require_api_token(x_nexuflow_token: str | None = Header(default=None)) -> None:
    if not x_nexuflow_token or not hmac.compare_digest(x_nexuflow_token, API_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid NexuFlow API token.",
        )
