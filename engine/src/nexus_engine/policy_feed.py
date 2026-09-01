from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

LOCAL_FEATURES = frozenset({"dns_apply", "mtu_apply", "power_plan", "process_priority", "cpu_sets", "standby_purge", "service_pause", "tcp_tweaks", "endpoint_steering"})


class PolicyError(ValueError):
    pass


def canonical_payload(document: dict) -> bytes:
    payload = {k: v for k, v in document.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _require_int(value: object, name: str) -> int:
    if type(value) is not int:
        raise PolicyError(f"{name} must be an integer")
    return value


def _parse_expiration(value: object) -> datetime:
    if not isinstance(value, str):
        raise PolicyError("expires_at must be a timestamp")
    try:
        expires = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PolicyError("invalid expires_at timestamp") from exc
    if expires.tzinfo is None or expires.utcoffset() is None:
        raise PolicyError("expires_at must include a timezone")
    return expires


def validate_feed(document: dict, public_key: bytes, *, minimum_version: int = 0, now: datetime | None = None) -> dict:
    """Validate an Ed25519-signed, disable-only policy feed.

    ``public_key`` is the 32-byte raw Ed25519 verification key. The corresponding
    private signing key never belongs in the client. No commands, enable lists,
    tracking URL parameters, or closable entries are accepted. Invalid input
    fails closed by raising :class:`PolicyError`.
    """
    if not isinstance(document, dict):
        raise PolicyError("policy feed must be an object")
    allowed_fields = {"schema", "version", "expires_at", "disabled_features", "warnings", "signature"}
    required_fields = {"schema", "version", "expires_at", "disabled_features", "signature"}
    if set(document) - allowed_fields:
        raise PolicyError("unsupported policy fields")
    if not required_fields <= set(document):
        raise PolicyError("missing required policy fields")

    schema = _require_int(document["schema"], "schema")
    version = _require_int(document["version"], "version")
    minimum = _require_int(minimum_version, "minimum_version")
    if schema != 1 or version < 0 or minimum < 0 or version < minimum:
        raise PolicyError("schema/version rollback rejected")

    expires = _parse_expiration(document["expires_at"])
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise PolicyError("current time must include a timezone")
    if expires <= current_time:
        raise PolicyError("policy expired")

    disabled_values = document["disabled_features"]
    if not isinstance(disabled_values, list) or any(not isinstance(item, str) for item in disabled_values):
        raise PolicyError("disabled_features must be a list of feature names")
    disabled = set(disabled_values)
    if len(disabled) != len(disabled_values):
        raise PolicyError("duplicate feature in disable list")
    if not disabled <= LOCAL_FEATURES:
        raise PolicyError("unknown feature in disable list")

    warnings = document.get("warnings", [])
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise PolicyError("warnings must be a list of strings")

    signature_value = document["signature"]
    if not isinstance(signature_value, str):
        raise PolicyError("signature must be base64 text")
    try:
        supplied = base64.b64decode(signature_value, validate=True)
    except (ValueError, TypeError) as exc:
        raise PolicyError("invalid signature encoding") from exc
    if len(supplied) != 64:
        raise PolicyError("invalid Ed25519 signature length")

    if not isinstance(public_key, bytes) or len(public_key) != 32:
        raise PolicyError("invalid Ed25519 public key")
    try:
        verifier = Ed25519PublicKey.from_public_bytes(public_key)
        verifier.verify(supplied, canonical_payload(document))
    except (InvalidSignature, ValueError) as exc:
        raise PolicyError("signature verification failed")

    return {
        "version": version,
        "disabled_features": sorted(disabled),
        "warnings": [item[:240] for item in warnings[:20]],
    }


def validate_feed_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PolicyError("policy feed must be tracking-free HTTPS")
