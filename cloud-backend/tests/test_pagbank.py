import hashlib

import pytest

from nexuflow_cloud.pagbank import checkout_payload, sandbox_api_base, verify_notification
from nexuflow_cloud.pagbank import payment_state, sandbox_transition, hosted_url


def payload(**changes):
    args = dict(order_id="a" * 32, plan_id="week", return_url="https://example.com/return",
                payment_notification_url="https://example.com/v1/webhooks/pagbank")
    return checkout_payload(**(args | changes))


@pytest.mark.parametrize("plan,cents", [("day", 99), ("week", 499), ("month", 999), ("year", 7999)])
def test_server_prices_in_cents(plan, cents):
    data = payload(plan_id=plan)
    assert data["items"][0]["unit_amount"] == cents
    assert "customer" not in data
    assert "recurrence_plan" not in data
    assert "shipping" not in data


@pytest.mark.parametrize("changes", [
    {"plan_id": "free"}, {"order_id": "../other"},
    {"return_url": "http://example.com"},
    {"return_url": "https://user:secret@example.com"},
    {"payment_notification_url": "https://example.com/" + "x" * 100},
])
def test_bad_checkout_input(changes):
    with pytest.raises(ValueError):
        payload(**changes)


def test_only_sandbox_allowed():
    assert sandbox_api_base("sandbox") == "https://sandbox.api.pagseguro.com"
    for environment in ("production", "live", "", "https://attacker.example"):
        with pytest.raises(ValueError):
            sandbox_api_base(environment)


def test_signature_uses_exact_bytes():
    body = b'{"id": "test"}'
    signature = hashlib.sha256(b"test-token-" + body).hexdigest()
    assert verify_notification(raw_body=body, signature=signature, token="test-token")
    assert not verify_notification(raw_body=body + b" ", signature=signature, token="test-token")
    assert not verify_notification(raw_body=body, signature=signature, token="other")


@pytest.mark.parametrize("signature", [None, "", "x" * 64, "0" * 63, "0" * 65])
def test_unsigned_or_malformed_notification_rejected(signature):
    assert not verify_notification(raw_body=b"{}", signature=signature, token="test-token")


def test_missing_key_or_oversized_body_rejected():
    assert not verify_notification(raw_body=b"{}", signature="0" * 64, token="")
    assert not verify_notification(raw_body=b"x" * 262145, signature="0" * 64, token="test")


@pytest.mark.parametrize("status,refunded,expected", [
    ("PAID", 0, "paid"), ("DECLINED", 0, "declined"), ("WAITING", 0, "pending"),
    ("PAID", 1, "revoked"), ("CANCELED", 499, "revoked"),
])
def test_payment_states(status, refunded, expected):
    order = {"referenceId": "a" * 32, "amountCents": 499}
    provider = {"reference_id": "a" * 32, "charges": [{"status": status,
        "amount": {"currency": "BRL", "value": 499, "summary": {"paid": 499, "refunded": refunded}}}]}
    assert payment_state(provider, order) == expected
    provider["charges"][0]["amount"]["value"] = 99
    with pytest.raises(ValueError):
        payment_state(provider, order)


def test_replay_does_not_extend_or_reactivate_access():
    paid = sandbox_transition({}, "paid")
    assert sandbox_transition(paid, "paid") == paid
    revoked = sandbox_transition(paid, "revoked")
    assert not revoked["testAccessActive"]
    assert sandbox_transition(revoked, "paid") == revoked


@pytest.mark.parametrize("url", ["http://pagamento.pagbank.com.br/", "https://pagbank.com.br.evil.test/", "https://evil.test/", "https://secret@pagbank.com.br/"])
def test_checkout_domain_rejected(url):
    with pytest.raises(ValueError):
        hosted_url({"links": [{"rel": "PAY", "href": url}]})


def test_create_uses_sandbox_only_and_keeps_personal_data_out():
    import asyncio
    from unittest.mock import MagicMock, AsyncMock
    from nexuflow_cloud.pagbank import SandboxGateway
    http, db = MagicMock(), MagicMock()
    http.post = AsyncMock(return_value=MagicMock(status_code=200))
    http.post.return_value.json.return_value = {'id': 'CHEC_test', 'links': [
        {'rel': 'PAY', 'href': 'https://pagamento.pagbank.com.br/pagamento?code=test'}]}
    result = asyncio.run(SandboxGateway(http, db, 'test-token', 'sandbox',
        'https://example.com').create('admin-test', 'week'))
    assert result['environment'] == 'sandbox'
    assert http.post.call_args.args[0] == 'https://sandbox.api.pagseguro.com/checkouts'
    assert 'admin-test' not in str(http.post.call_args.kwargs['json'])
    assert all(c.args == ('pagbankSandboxOrders',) for c in db.collection.call_args_list)


def test_reconciliation_does_not_touch_real_licenses(monkeypatch):
    import asyncio
    from unittest.mock import MagicMock, AsyncMock
    from google.cloud import firestore
    from nexuflow_cloud.pagbank import SandboxGateway
    monkeypatch.setattr(firestore, 'transactional', lambda f: f)
    http, db = MagicMock(), MagicMock()
    http.get = AsyncMock(return_value=MagicMock(status_code=200))
    http.get.return_value.json.return_value = {'id': 'ORDE_test', 'reference_id': 'a'*32,
        'charges': [{'status': 'PAID', 'amount': {'value': 499, 'currency': 'BRL',
            'summary': {'paid': 499, 'refunded': 0}}}]}
    db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'environment': 'sandbox', 'referenceId': 'a'*32, 'amountCents': 499, 'status': 'revoked'}
    asyncio.run(SandboxGateway(http, db, 'test-token', 'sandbox',
        'https://example.com').reconcile('ORDE_test'))
    update = db.transaction.return_value.set.call_args.args[1]
    assert update['status'] == 'revoked' and not update['testAccessActive']
    assert all(c.args == ('pagbankSandboxOrders',) for c in db.collection.call_args_list)
