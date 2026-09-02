from __future__ import annotations

from pathlib import Path

import pytest

from nexus_engine.investigator import investigator_snapshot, record_event
from nexus_engine.network.allowlist import assert_local_api_url, network_contract
from nexus_engine.report_signing import sign_report, verify_report


def test_network_allowlist_is_default_deny() -> None:
    assert assert_local_api_url("http://127.0.0.1:8000/api/v1/telemetry")
    with pytest.raises(ValueError):
        assert_local_api_url("https://example.com/api/v1/telemetry")
    with pytest.raises(ValueError):
        assert_local_api_url("http://localhost:8000/api/v1/telemetry")
    contract = network_contract()
    assert contract["default"] == "deny"
    assert contract["analytics"] is False
    assert contract["remote_commands"] is False


def test_local_report_signature_detects_tampering(tmp_path: Path) -> None:
    payload = {"schema": 4, "product": "NexuFlow 1.6 Trust Edition", "privacy": {"local_only": True}}
    envelope = sign_report(payload, tmp_path / "report-key.pem")
    assert envelope["algorithm"] == "Ed25519"
    assert envelope["trust_scope"] == "local_installation"
    assert verify_report(envelope)
    envelope["payload"]["product"] = "alterado"
    assert not verify_report(envelope)


def test_signer_rejects_foreign_payload(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        sign_report({"product": "Outro app"}, tmp_path / "key.pem")


def test_investigator_is_explicitly_read_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from nexus_engine import investigator

    monkeypatch.setattr(investigator, "_event_path", lambda: tmp_path / "events.jsonl")
    record_event("rede", "diagnóstico", "1.1.1.1", details="somente leitura")
    snapshot = investigator_snapshot()
    assert snapshot["read_only"] is True
    assert snapshot["events"][0]["target"] == "1.1.1.1"
    assert snapshot["network_contract"]["default"] == "deny"
