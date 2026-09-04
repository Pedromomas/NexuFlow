from fastapi.testclient import TestClient
from app import api_server
from app.security import API_TOKEN


def test_readonly_centers_are_wired(monkeypatch):
    monkeypatch.setattr(api_server, 'scan_connection', lambda: {'kind': 'connection_scan', 'read_only': True})
    monkeypatch.setattr(api_server, 'rank_dns', lambda: {'kind': 'dns_ranking', 'read_only': True})
    client = TestClient(api_server.app, base_url='http://127.0.0.1')
    assert client.get('/api/v1/connection/scan').json()['kind'] == 'connection_scan'
    assert client.get('/api/v1/connection/dns-ranking').json()['kind'] == 'dns_ranking'


def test_overlapping_scan_returns_conflict(monkeypatch):
    def busy(): raise RuntimeError('Um diagnóstico já está em andamento')
    monkeypatch.setattr(api_server, 'scan_connection', busy)
    client = TestClient(api_server.app, base_url='http://127.0.0.1')
    assert client.get('/api/v1/connection/scan').status_code == 409


def test_settings_require_token_and_fixed_destination():
    client = TestClient(api_server.app, base_url='http://127.0.0.1')
    assert client.post('/api/v1/pc/settings/game_mode').status_code == 401
    assert client.post('/api/v1/pc/settings/powershell', headers={'X-NexuFlow-Token': API_TOKEN}).status_code == 400
