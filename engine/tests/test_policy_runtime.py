from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nexus_engine.policy_feed import canonical_payload
from nexus_engine.policy_runtime import FeatureDisabledByPolicy, PolicyRuntime


def _signed_document(private_key: Ed25519PrivateKey, version: int, disabled: list[str]) -> dict:
    document = {
        "schema": 1,
        "version": version,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "disabled_features": disabled,
        "warnings": ["release safety policy"],
    }
    document["signature"] = base64.b64encode(private_key.sign(canonical_payload(document))).decode()
    return document


def _runtime(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    runtime = PolicyRuntime(
        cache_path=tmp_path / "policy.json",
        state_path=tmp_path / "accepted.json",
        public_key=public_key,
    )
    return private_key, runtime


def test_signed_cache_disables_only_and_persists_monotonic_version(tmp_path):
    private_key, runtime = _runtime(tmp_path)
    runtime.cache_path.write_text(json.dumps(_signed_document(private_key, 8, ["power_plan"])), encoding="utf-8")

    status = runtime.status()
    assert status["verified"] is True
    assert status["disabled_features"] == ["power_plan"]
    assert json.loads(runtime.state_path.read_text(encoding="utf-8"))["highest_accepted_version"] == 8
    with pytest.raises(FeatureDisabledByPolicy):
        runtime.assert_feature_enabled("power_plan")
    assert runtime.feature_enabled("dns_apply") is True


def test_cached_policy_rollback_and_tampering_fall_back_to_local_safe_defaults(tmp_path):
    private_key, runtime = _runtime(tmp_path)
    runtime.cache_path.write_text(json.dumps(_signed_document(private_key, 9, ["dns_apply"])), encoding="utf-8")
    assert runtime.status()["verified"] is True

    runtime.cache_path.write_text(json.dumps(_signed_document(private_key, 8, ["power_plan"])), encoding="utf-8")
    rejected = runtime.status()
    assert rejected["verified"] is False
    assert rejected["disabled_features"] == []
    assert "rollback" in rejected["reason"]


def test_duplicate_json_keys_are_rejected_before_policy_use(tmp_path):
    _private_key, runtime = _runtime(tmp_path)
    runtime.cache_path.write_text(
        '{"schema":1,"schema":1,"version":1,"expires_at":"2099-01-01T00:00:00Z","disabled_features":[],"signature":"AA=="}',
        encoding="utf-8",
    )
    status = runtime.status()
    assert status["verified"] is False
    assert "duplicate JSON key" in status["reason"]
