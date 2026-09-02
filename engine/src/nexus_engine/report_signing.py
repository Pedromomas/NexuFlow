from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


MAX_REPORT_BYTES = 256 * 1024


def _key_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    else:
        base = Path(tempfile.gettempdir())
    return base / "NexuFlow" / "trust" / "session-report-ed25519.pem"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_or_create_private_key(path: Path | None = None) -> Ed25519PrivateKey:
    key_path = path or _key_path()
    try:
        loaded = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        if isinstance(loaded, Ed25519PrivateKey):
            return loaded
    except (OSError, ValueError, TypeError):
        pass
    key = Ed25519PrivateKey.generate()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    raw = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    tmp = key_path.with_suffix(".tmp")
    tmp.write_bytes(raw)
    tmp.replace(key_path)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


def sign_report(payload: dict, key_path: Path | None = None) -> dict:
    if not isinstance(payload, dict) or not str(payload.get("product", "")).startswith("NexuFlow"):
        raise ValueError("Only a NexuFlow session report can be signed")
    raw = _canonical(payload)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("Session report exceeds the signing size limit")
    key = _load_or_create_private_key(key_path)
    public_raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "schema": 1,
        "algorithm": "Ed25519",
        "trust_scope": "local_installation",
        "trust_note": "Prova integridade e origem nesta instalação; não é assinatura comercial do fornecedor.",
        "public_key_base64": base64.b64encode(public_raw).decode("ascii"),
        "key_fingerprint_sha256": hashlib.sha256(public_raw).hexdigest(),
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
        "payload": payload,
        "signature_base64": base64.b64encode(key.sign(raw)).decode("ascii"),
    }


def verify_report(envelope: dict) -> bool:
    try:
        payload = envelope["payload"]
        raw = _canonical(payload)
        public_raw = base64.b64decode(envelope["public_key_base64"], validate=True)
        signature = base64.b64decode(envelope["signature_base64"], validate=True)
        if hashlib.sha256(raw).hexdigest() != envelope["payload_sha256"]:
            return False
        Ed25519PublicKey.from_public_bytes(public_raw).verify(signature, raw)
        return True
    except (KeyError, TypeError, ValueError):
        return False
    except Exception:
        return False
