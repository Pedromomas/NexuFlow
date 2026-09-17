from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.api_server import app
from app.security import API_TOKEN


def test_health_is_loopback_control_plane():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["name"] == "NexuFlow"
        assert body["mutation_auth"] == "X-NexuFlow-Token"


def test_mutation_requires_token():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/v1/boost/start", json={"profile": "complete"})
        assert response.status_code == 401


def test_mutation_with_token_is_platform_guarded(monkeypatch):
    # Never start a real privileged daemon if the test runner is elevated.
    from app import api_server
    monkeypatch.setattr(api_server, '_start_detached_daemon', lambda _: {'ok': True})
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/v1/boost/start",
            json={"profile": "complete"},
            headers={"X-NexuFlow-Token": API_TOKEN},
        )
        if os.name == "nt":
            # On Windows this may proceed to daemon startup depending on privileges.
            assert response.status_code in {200, 403, 500}
        else:
            assert response.status_code == 409


def test_untrusted_host_is_rejected():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/v1/health", headers={"Host": "evil.example"})
        assert response.status_code == 400


def test_stop_reports_pending_rollback(monkeypatch):
    from app import api_server
    monkeypatch.setattr(api_server, '_require_windows_admin', lambda: None)
    monkeypatch.setattr(api_server, 'stop_daemon', lambda: {'stopped': True, 'restore_pending': True})
    assert api_server.boost_stop()['ok'] is False


def test_restore_waits_for_the_daemon_before_touching_manual_state(monkeypatch):
    from app import api_server
    monkeypatch.setattr(api_server, '_require_windows_admin', lambda: None)
    monkeypatch.setattr(api_server, 'stop_daemon', lambda: {'stopped': False, 'restore_pending': True})
    def forbidden():
        raise AssertionError('A running daemon must remain the only rollback writer')
    monkeypatch.setattr(api_server.route_selector, 'restore', forbidden)
    assert api_server.restore_all()['ok'] is False


def test_cors_does_not_allow_arbitrary_origin():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.options(
            "/api/v1/boost/start",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-NexuFlow-Token, Content-Type",
            },
        )
        assert response.status_code == 400
        assert response.headers.get("access-control-allow-origin") is None


def test_boost_schema_exposes_only_four_user_profiles():
    from app.schemas import BoostRequest
    from pydantic import ValidationError

    for profile in ("ping", "pc", "complete", "hardcore_safe"):
        assert BoostRequest(profile=profile).profile == profile
    for internal in ("auto", "safe", "aggressive", "riot_safe", "valve_safe", "unknown_safe"):
        try:
            BoostRequest(profile=internal)
        except ValidationError:
            continue
        raise AssertionError(f"internal profile escaped the public boundary: {internal}")


def test_route_benchmark_requires_token():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/v1/routes/benchmark",
            json={"ips": ["1.1.1.1", "8.8.8.8"], "attempts": 2},
        )
        assert response.status_code == 401


def test_driver_scan_is_read_only_and_on_demand(monkeypatch):
    import app.api_server as api_module

    monkeypatch.setattr(
        api_module,
        "scan_driver_updates",
        lambda: {
            "available": True,
            "deferred": False,
            "read_only": True,
            "status": "no_updates_offered",
            "updates_offered": 0,
            "updates": [],
            "download_performed": False,
            "installation_performed": False,
        },
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/v1/drivers/scan")
        assert response.status_code == 200
        assert response.json()["installation_performed"] is False


def test_open_driver_updates_requires_local_api_token():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post("/api/v1/drivers/open-updates", json={})
        assert response.status_code == 401


def test_protected_route_diagnostic_rejects_arbitrary_target(monkeypatch):
    import app.api_server as api_module

    monkeypatch.setattr(api_module, "running_protected_games", lambda: ["valorant"])
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/v1/route-diagnostics", params={"target": "192.0.2.50"})
        assert response.status_code == 409
