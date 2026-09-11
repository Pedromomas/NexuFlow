from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nexuflow_cloud.security import normalize_email, opaque_hash, sign_license, verify_mp_webhook
from nexuflow_cloud.services import PLAN_CATALOG


def test_email_normalization_and_opaque_hash_are_bounded() -> None:
    assert normalize_email(" User@Example.COM ") == "user@example.com"
    with pytest.raises(ValueError):
        normalize_email("not-an-email")
    digest = opaque_hash("secret-code", b"p" * 32)
    assert len(digest) == 64
    assert "secret-code" not in digest


def test_mercado_pago_signature_checks_manifest_and_freshness() -> None:
    secret = "webhook-secret"
    timestamp = 1_700_000_000
    manifest = f"id:12345;request-id:req-7;ts:{timestamp};"
    signature = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    header = f"ts={timestamp},v1={signature}"
    assert verify_mp_webhook(header=header, request_id="req-7", data_id="12345", secret=secret, now=timestamp)
    assert not verify_mp_webhook(header=header, request_id="req-changed", data_id="12345", secret=secret, now=timestamp)
    assert not verify_mp_webhook(header=header, request_id="req-7", data_id="12345", secret=secret, now=timestamp + 301)


def test_license_is_canonical_ed25519() -> None:
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes_raw()
    payload = {"status": "trial", "expiresAt": "2026-09-06T00:00:00Z", "entitlements": ["latency-lab"]}
    signed = sign_license(payload, raw)
    signature = base64.b64decode(signed["signature"])
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    key.public_key().verify(signature, canonical)
    assert signed["algorithm"] == "Ed25519"


def test_prices_are_server_authoritative_and_match_the_app() -> None:
    assert {key: value["amount"] for key, value in PLAN_CATALOG.items()} == {
        "day": 0.99, "week": 4.99, "month": 9.99, "year": 79.99,
    }
    assert {key: value["days"] for key, value in PLAN_CATALOG.items()} == {
        "day": 1, "week": 7, "month": 30, "year": 365,
    }

