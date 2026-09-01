from nexus_engine.network.dns import DNSManager, DNSProvider, DNSScore
from nexus_engine.network.mtu import MTUManager


def test_dns_keeps_current_when_gain_is_too_small():
    current = DNSScore(DNSProvider("Current", ("192.0.2.53",)), [20.0, 20.0, 20.0, 20.0])
    candidate = DNSScore(DNSProvider("Cloudflare", ("1.1.1.1",)), [18.5, 18.5, 18.5, 18.5])
    assert DNSManager.select_best([current, candidate], minimum_improvement_ms=3.0) is None


def test_dns_switches_for_clear_reliable_gain():
    current = DNSScore(DNSProvider("Current", ("192.0.2.53",)), [31.0, 30.0, 32.0, 31.0])
    candidate = DNSScore(DNSProvider("Cloudflare", ("1.1.1.1",)), [12.0, 13.0, 12.0, 12.0])
    assert DNSManager.select_best([current, candidate]).name == "Cloudflare"


def test_mtu_only_reduces_on_consensus(monkeypatch):
    manager = MTUManager()
    values = iter([1432, 1434, 1433])
    monkeypatch.setattr(manager, "_max_payload", lambda _ip: next(values))
    result = manager.recommend(1500)
    assert result["apply"] is True
    assert result["recommended"] == 1460


def test_mtu_skips_when_targets_disagree(monkeypatch):
    manager = MTUManager()
    values = iter([1200, 1472, 1472])
    monkeypatch.setattr(manager, "_max_payload", lambda _ip: next(values))
    result = manager.recommend(1500)
    assert result["apply"] is False
    assert result["reason"] == "PMTU targets disagree"


def test_mtu_skips_abnormally_low_path(monkeypatch):
    manager = MTUManager()
    values = iter([1200, 1202, 1201])
    monkeypatch.setattr(manager, "_max_payload", lambda _ip: next(values))
    result = manager.recommend(1500)
    assert result["apply"] is False
    assert "safety floor" in result["reason"]


def test_mtu_preserves_custom_jumbo_configuration(monkeypatch):
    manager = MTUManager()
    monkeypatch.setattr(manager, "_max_payload", lambda _ip: 1472)
    result = manager.recommend(9000)
    assert result["apply"] is False
    assert result["recommended"] == 9000
    assert "Custom/jumbo" in result["reason"]
