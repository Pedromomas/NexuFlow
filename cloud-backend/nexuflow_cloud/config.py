from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from urllib.parse import urlparse


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _https_url(name: str) -> str:
    value = _required(name).rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise RuntimeError(f"{name} must be a public HTTPS URL")
    return value


def _secret_bytes(name: str, minimum: int = 32) -> bytes:
    try:
        value = base64.b64decode(_required(name), validate=True)
    except Exception as exc:
        raise RuntimeError(f"{name} must be valid base64") from exc
    if len(value) < minimum:
        raise RuntimeError(f"{name} must decode to at least {minimum} bytes")
    return value


@dataclass(frozen=True)
class Settings:
    firebase_project_id: str
    firebase_web_api_key: str
    public_api_base: str
    public_app_return_url: str
    mercado_pago_access_token: str
    mercado_pago_webhook_secret: str
    mercado_pago_live_mode: bool
    code_hash_pepper: bytes
    license_private_key: bytes
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        origins = tuple(
            item.strip().rstrip("/")
            for item in os.environ.get("ALLOWED_ORIGINS", "https://tauri.localhost,http://tauri.localhost").split(",")
            if item.strip()
        )
        private_key = _secret_bytes("LICENSE_ED25519_PRIVATE_KEY")
        if len(private_key) != 32:
            raise RuntimeError("LICENSE_ED25519_PRIVATE_KEY must decode to exactly 32 bytes")
        return cls(
            firebase_project_id=_required("FIREBASE_PROJECT_ID"),
            firebase_web_api_key=_required("FIREBASE_WEB_API_KEY"),
            public_api_base=_https_url("PUBLIC_API_BASE"),
            public_app_return_url=_https_url("PUBLIC_APP_RETURN_URL"),
            mercado_pago_access_token=_required("MERCADO_PAGO_ACCESS_TOKEN") if os.getenv("NEXUFLOW_BILLING_ENABLED", "false").lower() == "true" else "",
            mercado_pago_webhook_secret=_required("MERCADO_PAGO_WEBHOOK_SECRET") if os.getenv("NEXUFLOW_BILLING_ENABLED", "false").lower() == "true" else "",
            mercado_pago_live_mode=os.environ.get("MERCADO_PAGO_LIVE_MODE", "false").lower() == "true",
            code_hash_pepper=_secret_bytes("CODE_HASH_PEPPER"),
            license_private_key=private_key,
            allowed_origins=origins,
        )
