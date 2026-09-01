import base64
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nexus_engine.anti_cheat import anti_cheat_policy_report, boost_objective, effective_profile
from nexus_engine.models import BoostProfile
from nexus_engine.policy_feed import PolicyError, canonical_payload, validate_feed, validate_feed_url


def _key_pair() -> tuple[Ed25519PrivateKey, bytes]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_key, public_key


def _signed_policy(private_key: Ed25519PrivateKey, **overrides) -> dict:
    document = {
        "schema": 1,
        "version": 7,
        "expires_at": "2099-01-01T00:00:00Z",
        "disabled_features": ["cpu_sets"],
        "warnings": [],
        **overrides,
    }
    document["signature"] = base64.b64encode(
        private_key.sign(canonical_payload(document))
    ).decode("ascii")
    return document


def test_unknown_game_is_fail_closed():
    assert effective_profile(BoostProfile.AGGRESSIVE, "some-new-game") is BoostProfile.UNKNOWN_SAFE


def test_four_modes_are_explicit():
    assert {BoostProfile.PING, BoostProfile.PC, BoostProfile.COMPLETE, BoostProfile.HARDCORE_SAFE}


def test_vanguard_safety_overlay_preserves_user_objective():
    assert boost_objective(BoostProfile.PING) == "ping"
    assert boost_objective(BoostProfile.PC) == "pc"
    assert boost_objective(BoostProfile.COMPLETE) == "complete"
    ping = anti_cheat_policy_report("lol", BoostProfile.PING, BoostProfile.RIOT_SAFE)
    pc = anti_cheat_policy_report("valorant", BoostProfile.PC, BoostProfile.RIOT_SAFE)
    assert ping["objective_mode"] == "ping"
    assert pc["objective_mode"] == "pc"
    assert ping["capabilities"]["process_optimization"] is False
    assert pc["capabilities"]["power_plan"] is True
    assert "temporary_system_power_plan" not in ping["allowed_features"]
    assert "temporary_system_power_plan" in pc["allowed_features"]
    assert "dns_benchmark_without_live_resolver_change" in ping["allowed_features"]


def test_disable_only_signed_policy():
    private_key, public_key = _key_pair()
    doc = _signed_policy(private_key)
    assert validate_feed(doc, public_key, minimum_version=6, now=datetime.now(timezone.utc))["disabled_features"] == ["cpu_sets"]


def test_policy_rejects_tampering_and_wrong_public_key():
    private_key, public_key = _key_pair()
    doc = _signed_policy(private_key)
    doc["disabled_features"] = ["power_plan"]
    with pytest.raises(PolicyError, match="signature verification failed"):
        validate_feed(doc, public_key)

    other_private_key, _ = _key_pair()
    doc = _signed_policy(other_private_key)
    with pytest.raises(PolicyError, match="signature verification failed"):
        validate_feed(doc, public_key)


def test_policy_rejects_expiration_and_version_rollback():
    private_key, public_key = _key_pair()
    expired = _signed_policy(private_key, expires_at="2020-01-01T00:00:00Z")
    with pytest.raises(PolicyError, match="policy expired"):
        validate_feed(expired, public_key, now=datetime.now(timezone.utc))

    old = _signed_policy(private_key, version=6)
    with pytest.raises(PolicyError, match="rollback rejected"):
        validate_feed(old, public_key, minimum_version=7)


def test_policy_rejects_enable_or_commands():
    _, public_key = _key_pair()
    for forbidden in ("enable", "commands", "closable"):
        document = {
            "schema": 1,
            "version": 1,
            "expires_at": "2099-01-01T00:00:00Z",
            "disabled_features": [],
            forbidden: [],
            "signature": "AA==",
        }
        with pytest.raises(PolicyError, match="unsupported policy fields"):
            validate_feed(document, public_key)


def test_policy_rejects_invalid_key_signature_and_field_types():
    private_key, public_key = _key_pair()
    document = _signed_policy(private_key)
    with pytest.raises(PolicyError, match="invalid Ed25519 public key"):
        validate_feed(document, b"not-a-public-key")

    document["signature"] = base64.b64encode(b"too short").decode("ascii")
    with pytest.raises(PolicyError, match="signature length"):
        validate_feed(document, public_key)

    invalid_schema = _signed_policy(private_key, schema=True)
    with pytest.raises(PolicyError, match="schema must be an integer"):
        validate_feed(invalid_schema, public_key)

    duplicate_disable = _signed_policy(private_key, disabled_features=["cpu_sets", "cpu_sets"])
    with pytest.raises(PolicyError, match="duplicate feature"):
        validate_feed(duplicate_disable, public_key)


def test_policy_url_is_https_and_tracking_free():
    validate_feed_url("https://policy.nexuflow.example/v1.json")
    for url in ("http://policy.example/v1", "https://policy.example/v1?device=1"):
        try:
            validate_feed_url(url)
        except PolicyError:
            continue
        raise AssertionError(url)
