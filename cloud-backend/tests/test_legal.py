import pytest
from fastapi.testclient import TestClient
from nexuflow_cloud import main
from nexuflow_cloud.legal import document


@pytest.mark.parametrize('path', ['/legal/terms', '/legal/privacy'])
def test_legal_preview_is_closed_by_default(monkeypatch, path):
    monkeypatch.delenv('NEXUFLOW_LEGAL_REVIEW_PREVIEW', raising=False)
    assert TestClient(main.app).get(path).status_code == 503


@pytest.mark.parametrize('path', ['/legal/terms', '/legal/privacy'])
def test_legal_preview_is_static_and_independent_of_accounts(monkeypatch, path):
    monkeypatch.setenv('NEXUFLOW_LEGAL_REVIEW_PREVIEW', 'true')
    monkeypatch.setenv('NEXUFLOW_API_ENABLED', 'false')
    def forbidden():
        pytest.fail('Legal pages must not access credentials or user data')
    monkeypatch.setattr(main, 'services', forbidden)
    result = TestClient(main.app).get(path)
    assert result.status_code == 200
    assert 'Pedro Fernandes Bahia Rocha' in result.text
    assert 'guilhermefudido5@gmail.com' in result.text
    assert 'Rascunho' in result.text
    assert '<script' not in result.text
    assert "default-src 'none'" in result.headers['content-security-policy']
    assert result.headers['cache-control'] == 'no-store'
    assert result.headers['x-robots-tag'] == 'noindex, nofollow'


def test_privacy_does_not_claim_password_bypasses_own_server():
    assert 'pelo backend' in document('privacy')
    assert 'não garante anonimização' in document('privacy')
