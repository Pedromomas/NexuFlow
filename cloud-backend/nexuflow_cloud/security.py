from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > 254 or not EMAIL_RE.fullmatch(normalized):
        raise ValueError("Digite um e-mail válido.")
    return normalized


def opaque_hash(value: str, pepper: bytes) -> str:
    return hmac.new(pepper, value.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def parse_mp_signature(header: str) -> tuple[int, str]:
    values: dict[str, str] = {}
    for part in header.split(","):
        key, separator, value = part.strip().partition("=")
        if separator and key and value:
            values[key] = value
    try:
        timestamp = int(values["ts"])
        signature = values["v1"].lower()
    except (KeyError, ValueError) as exc:
        raise ValueError("Assinatura do webhook ausente ou inválida.") from exc
    if not re.fullmatch(r"[0-9a-f]{64}", signature):
        raise ValueError("Assinatura do webhook inválida.")
    return timestamp, signature


def verify_mp_webhook(
    *, header: str, request_id: str, data_id: str, secret: str,
    now: int | None = None, tolerance_seconds: int = 300,
) -> bool:
    try:
        timestamp, supplied = parse_mp_signature(header)
    except ValueError:
        return False
    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > tolerance_seconds:
        return False
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{timestamp};"
    expected = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def sign_license(payload: dict[str, Any], private_key_bytes: bytes) -> dict[str, Any]:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = Ed25519PrivateKey.from_private_bytes(private_key_bytes).sign(canonical)
    return {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
        "algorithm": "Ed25519",
    }
