"""PagBank sandbox checkout and reconciliation.

This stage deliberately cannot activate a license or send a live charge.
Provider reference: https://developer.pagbank.com.br/reference/criar-checkout
"""
from __future__ import annotations

import hashlib
import hmac
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit


PLAN_CENTS = {"day": 99, "week": 499, "month": 999, "year": 7999}


def hosted_url(data: dict) -> str:
    for link in data.get("links", []):
        if link.get("rel") != "PAY":
            continue
        value = _https(link.get("href", ""), 2048)
        host = urlsplit(value).hostname or ""
        if any(host == root or host.endswith("." + root)
               for root in ("pagbank.com.br", "pagseguro.uol.com.br")):
            return value
    raise ValueError("Unexpected checkout domain")


def payment_state(data: dict, order: dict) -> str:
    """Interpret freshly fetched provider data; never the redirect or webhook alone."""
    if data.get("reference_id") != order["referenceId"]:
        raise ValueError("Order reference mismatch")
    charges = data.get("charges", [])
    if not isinstance(charges, list) or len(charges) > 1:
        raise ValueError("Unsupported charge set; manual review required")
    if not charges:
        return "pending"
    charge = charges[0]
    amount = charge.get("amount", {})
    if (amount.get("currency") != "BRL" or type(amount.get("value")) is not int
            or amount["value"] != order["amountCents"]):
        raise ValueError("Payment amount mismatch")
    summary = amount.get("summary", {})
    refunded = summary.get("refunded")
    if type(refunded) is not int or refunded < 0:
        raise ValueError("Missing payment summary")
    if refunded > 0 or charge.get("status") == "CANCELED":
        return "revoked"
    if charge.get("status") == "PAID" and summary.get("paid") == order["amountCents"]:
        return "paid"
    if charge.get("status") == "DECLINED":
        return "declined"
    return "pending"


def sandbox_transition(previous: dict, observed: str) -> dict:
    # A delayed PAID notification cannot restore a refunded pass.
    state = "revoked" if previous.get("status") == "revoked" else observed
    return {"status": state, "testAccessActive": state == "paid"}


class SandboxGateway:
    """Isolated sandbox ledger: deliberately NEVER writes profiles or licenses."""
    def __init__(self, http, db, token: str, environment: str, api_base: str):
        self.http, self.db = http, db
        self.base = sandbox_api_base(environment)
        if not token:
            raise ValueError("Missing PagBank sandbox token")
        self.token, self.api_base = token, _https(api_base, 255).rstrip("/")

    async def create(self, uid: str, plan: str) -> dict:
        import uuid
        from fastapi import HTTPException
        ref = uuid.uuid4().hex
        payload = checkout_payload(order_id=ref, plan_id=plan,
            return_url=self.api_base + "/billing/return",
            payment_notification_url=self.api_base + "/v1/webhooks/pagbank")
        doc = self.db.collection("pagbankSandboxOrders").document(ref)
        doc.create({"referenceId": ref, "uid": uid, "plan": plan,
            "amountCents": PLAN_CENTS[plan], "status": "pending", "environment": "sandbox",
            "createdAt": datetime.now(UTC)})
        response = await self.http.post(self.base + "/checkouts", json=payload,
            headers={"Authorization": "Bearer " + self.token})
        if response.status_code >= 300:
            doc.set({"status": "creation_failed"}, merge=True)
            raise HTTPException(502, "PagBank não criou o checkout de testes.")
        data = response.json()
        url = hosted_url(data)
        doc.set({"checkoutId": data["id"]}, merge=True)
        return {"checkoutUrl": url, "orderId": ref, "environment": "sandbox"}

    async def reconcile(self, provider_id: str) -> None:
        from fastapi import HTTPException
        from google.cloud import firestore
        if not re.fullmatch(r"ORDE_[A-Za-z0-9-]{1,64}", provider_id):
            raise HTTPException(400, "Identificador PagBank inválido.")
        response = await self.http.get(self.base + "/orders/" + provider_id,
            headers={"Authorization": "Bearer " + self.token})
        if response.status_code != 200:
            raise HTTPException(502, "Confirmação PagBank indisponível.")
        data = response.json()
        ref = data.get("reference_id", "")
        if data.get("id") != provider_id or not re.fullmatch(r"[a-f0-9]{32}", ref):
            raise HTTPException(400, "Referência PagBank inválida.")
        doc = self.db.collection("pagbankSandboxOrders").document(ref)

        @firestore.transactional
        def apply(txn):
            previous = doc.get(transaction=txn).to_dict() or {}
            if previous.get("environment") != "sandbox":
                raise HTTPException(400, "Pedido de testes desconhecido.")
            if previous.get("providerId") not in (None, provider_id):
                raise HTTPException(400, "Pedido já associado a outra transação.")
            try:
                observed = payment_state(data, previous)
            except ValueError as exc:
                raise HTTPException(400, "Pagamento requer revisão.") from exc
            update = sandbox_transition(previous, observed)
            txn.set(doc, {**update, "providerId": provider_id,
                          "checkedAt": datetime.now(UTC)}, merge=True)
        apply(self.db.transaction())


def sandbox_api_base(environment: str) -> str:
    # Fail closed until production approval and end-to-end tests are recorded.
    if environment != "sandbox":
        raise ValueError("PagBank production is not enabled")
    return "https://sandbox.api.pagseguro.com"


def _https(value: str, max_length: int) -> str:
    parsed = urlsplit(value)
    if (len(value) > max_length or parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password or parsed.fragment
            or any(c.isspace() for c in value)):
        raise ValueError("Expected a valid HTTPS URL")
    return value


def checkout_payload(*, order_id: str, plan_id: str, return_url: str,
                     payment_notification_url: str) -> dict:
    """Server-selected price, no card/customer data, no recurring debit mandate.

Durations are prepaid passes. A checkout redirect is never proof of payment.
Caller must persist the order before sending and reconcile payments separately.
"""
    if not re.fullmatch(r"[a-f0-9]{32}", order_id):
        raise ValueError("Invalid internal order ID")
    if plan_id not in PLAN_CENTS:
        raise ValueError("Invalid plan")
    return {
        "reference_id": order_id,
        "customer_modifiable": True,
        "items": [{"reference_id": plan_id, "name": f"NexuFlow - {plan_id}",
                   "quantity": 1, "unit_amount": PLAN_CENTS[plan_id]}],
        "payment_methods": [{"type": "PIX"}, {"type": "CREDIT_CARD"}],
        "payment_methods_configs": [{"type": "CREDIT_CARD", "config_options": [
            {"option": "INSTALLMENTS_LIMIT", "value": "1"}]}],
        "redirect_url": _https(return_url, 255),
        "return_url": _https(return_url, 255),
        "payment_notification_urls": [_https(payment_notification_url, 100)],
    }


def verify_notification(*, raw_body: bytes, signature: str | None, token: str) -> bool:
    """Verify SHA256(token + '-' + exact raw body), not reserialized JSON.

https://developer.pagbank.com.br/reference/confirmar-autenticidade-da-notificacao
Authenticity alone does not establish payment, freshness, or prevent replays.
The handler fetches provider state and applies an idempotent transaction.
"""
    if (not token or not signature or len(raw_body) > 262144
            or not re.fullmatch(r"[a-fA-F0-9]{64}", signature)):
        return False
    expected = hashlib.sha256(token.encode("utf-8") + b"-" + raw_body).hexdigest()
    return hmac.compare_digest(expected, signature.lower())
