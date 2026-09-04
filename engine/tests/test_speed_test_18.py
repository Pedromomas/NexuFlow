from contextlib import nullcontext

import pytest

from nexus_engine.network import speed_test


def test_speed_test_is_bounded_read_only_and_uses_fixed_host(monkeypatch):
    downloads = []
    uploads = []
    monkeypatch.setattr(speed_test, "running_protected_games", lambda: [])
    monkeypatch.setattr(speed_test, "daemon_is_running", lambda: False)
    monkeypatch.setattr(speed_test, "_scan_lock", nullcontext)
    monkeypatch.setattr(speed_test, "_download", lambda size: downloads.append(size) or 123.4)
    monkeypatch.setattr(speed_test, "_upload", lambda size: uploads.append(size) or 45.6)

    result = speed_test.run_speed_test()

    assert downloads == list(speed_test.DOWNLOAD_SIZES)
    assert uploads == list(speed_test.UPLOAD_SIZES)
    assert result["transferred_bytes_max"] == 30 * 1024 * 1024
    assert result["endpoint"] == "speed.cloudflare.com"
    assert result["download_mbps"] == 123.4
    assert result["upload_mbps"] == 45.6
    assert result["read_only"] is True
    assert result["mutation_performed"] is False


def test_speed_test_refuses_protected_or_boost_sessions(monkeypatch):
    monkeypatch.setattr(speed_test, "running_protected_games", lambda: ["valorant"])
    monkeypatch.setattr(speed_test, "daemon_is_running", lambda: False)
    with pytest.raises(RuntimeError, match="partida protegida"):
        speed_test.run_speed_test()

    monkeypatch.setattr(speed_test, "running_protected_games", lambda: [])
    monkeypatch.setattr(speed_test, "daemon_is_running", lambda: True)
    with pytest.raises(RuntimeError, match="Desative o BOOST"):
        speed_test.run_speed_test()
