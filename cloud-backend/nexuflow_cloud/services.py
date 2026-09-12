from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from .config import Settings
from .codes import redemption_updates, unused_code_revocation
from .security import normalize_email, opaque_hash


PLAN_CATALOG: dict[str, dict[str, Any]] = {
    "day": {"label": "NexuFlow — Passe diário", "amount": 0.99, "days": 1},
    "week": {"label": "NexuFlow — Passe semanal", "amount": 4.99, "days": 7},
    "month": {"label": "NexuFlow — Plano mensal", "amount": 9.99, "days": 30},
    "year": {"label": "NexuFlow — Plano anual", "amount": 79.99, "days": 365},
}


class CloudServices:
    def __init__(self, settings: Settings):
        self.settings = settings
        try:
            import firebase_admin
            from firebase_admin import auth, firestore
        except ImportError as exc:
            raise RuntimeError("Install the cloud-backend dependencies before starting the API") from exc
        if not firebase_admin._apps:  # type: ignore[attr-defined]
            firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
        self.auth = auth
        self.db = firestore.client()
        self.http = httpx.AsyncClient(timeout=15.0, follow_redirects=False)

    async def close(self) -> None:
        await self.http.aclose()

    async def _identity(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:{operation}?key={self.settings.firebase_web_api_key}"
        response = await self.http.post(url, json=payload)
        if response.status_code >= 400:
            # Do not expose provider details that permit e-mail enumeration.
            raise HTTPException(status_code=400, detail="Não foi possível concluir a autenticação com esses dados.")
        return response.json()

    async def register(self, display_name: str, email: str, password: str, *, legal_version: str = '') -> dict[str, str]:
        email = normalize_email(email)
        name = display_name.strip()
        if not 2 <= len(name) <= 50 or not 10 <= len(password) <= 128:
            raise HTTPException(status_code=400, detail="Nome ou senha fora dos limites permitidos.")
        result = await self._identity("signUp", {"email": email, "password": password, "returnSecureToken": True})
        uid = result["localId"]
        self.auth.update_user(uid, display_name=name)
        now = datetime.now(UTC)
        self.db.collection("profiles").document(uid).set({
            "displayName": name,
            "legalAcceptance": {"version": legal_version, "acceptedAt": now},
            "email": email,
            "plan": "free",
            "subscriptionStatus": "trial",
            "trialStartedAt": now,
            "trialEndsAt": now + timedelta(days=7),
            "subscriptionEndsAt": None,
            "duoInviteEmail": None,
            "createdAt": now,
            "updatedAt": now,
        }, merge=True)
        try:
            await self._identity("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": result["idToken"]})
        except (HTTPException, httpx.HTTPError):
            # Sign-up already succeeded. Do not invite a duplicate sign-up or
            # claim the message was delivered when the mail request failed.
            return {"message": "Conta criada, mas não foi possível enviar a confirmação agora. Entre na conta e use Enviar confirmação de e-mail."}
        return {"message": "Conta criada. Confira seu e-mail para confirmar o cadastro."}

    async def login(self, email: str, password: str) -> dict[str, Any]:
        email = normalize_email(email)
        if not 10 <= len(password) <= 128:
            raise HTTPException(status_code=400, detail="Não foi possível concluir a autenticação com esses dados.")
        result = await self._identity("signInWithPassword", {
            "email": email, "password": password, "returnSecureToken": True,
        })
        decoded = self.auth.verify_id_token(result["idToken"], check_revoked=True)
        profile = self.profile(decoded["uid"])
        return {
            "accessToken": result["idToken"],
            "refreshToken": result["refreshToken"],
            "expiresInSeconds": min(int(result.get("expiresIn", 3600)), 3600),
            "profile": profile,
        }

    async def reset_password(self, email: str) -> dict[str, str]:
        try:
            await self._identity("sendOobCode", {"requestType": "PASSWORD_RESET", "email": normalize_email(email)})
        except HTTPException:
            pass
        return {"message": "Se a conta existir, o e-mail de redefinição será enviado."}

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        if not 20 <= len(refresh_token) <= 4096:
            raise HTTPException(status_code=400, detail="Sessão inválida.")
        response = await self.http.post(
            f"https://securetoken.googleapis.com/v1/token?key={self.settings.firebase_web_api_key}",
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=401, detail="A sessão expirou. Entre novamente.")
        result = response.json()
        decoded = self.auth.verify_id_token(result["id_token"], check_revoked=True)
        return {
            "accessToken": result["id_token"],
            "refreshToken": result["refresh_token"],
            "expiresInSeconds": min(int(result.get("expires_in", 3600)), 3600),
            "profile": self.profile(decoded["uid"]),
        }

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            return self.auth.verify_id_token(token, check_revoked=True)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.") from exc

    def _accept_duo_if_available(self, uid: str, email: str) -> None:
        invite_id = opaque_hash(normalize_email(email), self.settings.code_hash_pepper)
        invite_ref = self.db.collection("duoInvites").document(invite_id)
        invite = invite_ref.get()
        if not invite.exists:
            return
        data = invite.to_dict() or {}
        if data.get("status") != "pending" or data.get("ownerUid") == uid:
            return
        owner = self.db.collection("profiles").document(str(data.get("ownerUid"))).get()
        owner_data = owner.to_dict() or {}
        if owner_data.get("subscriptionStatus") not in {"active", "trial"}:
            return
        self.db.collection("profiles").document(uid).set({"duoOwnerUid": data["ownerUid"], "updatedAt": datetime.now(UTC)}, merge=True)
        invite_ref.set({"status": "accepted", "memberUid": uid, "acceptedAt": datetime.now(UTC)}, merge=True)

    def profile(self, uid: str) -> dict[str, Any]:
        user = self.auth.get_user(uid)
        if user.email and user.email_verified:
            self._accept_duo_if_available(uid, user.email)
        ref = self.db.collection("profiles").document(uid)
        snapshot = ref.get()
        data = snapshot.to_dict() if snapshot.exists else {}
        now = datetime.now(UTC)
        if not data:
            data = {
                "displayName": user.display_name or "Explorador",
                "email": user.email or "",
                "plan": "free", "subscriptionStatus": "trial",
                "trialStartedAt": now, "trialEndsAt": now + timedelta(days=7),
                "subscriptionEndsAt": None, "duoInviteEmail": None,
                "createdAt": now, "updatedAt": now,
            }
            ref.set(data)
        trial_end = data.get("trialEndsAt")
        paid_end = data.get("subscriptionEndsAt")
        status = data.get("subscriptionStatus", "free")
        if status == "trial" and isinstance(trial_end, datetime) and trial_end <= now:
            status = "free"
        if status == "active" and isinstance(paid_end, datetime) and paid_end <= now:
            status = "cancelled"
        duo_owner_uid = data.get("duoOwnerUid")
        if duo_owner_uid and user.email_verified:
            owner_data = self.db.collection("profiles").document(str(duo_owner_uid)).get().to_dict() or {}
            owner_status = owner_data.get("subscriptionStatus", "free")
            owner_end = owner_data.get("subscriptionEndsAt")
            owner_trial_end = owner_data.get("trialEndsAt")
            if owner_status == "trial" and isinstance(owner_trial_end, datetime) and owner_trial_end <= now:
                owner_status = "free"
            if owner_status == "active" and isinstance(owner_end, datetime) and owner_end <= now:
                owner_status = "cancelled"
            if owner_status in {"active", "trial"}:
                status = owner_status
                paid_end = owner_end
                trial_end = owner_trial_end
                data["plan"] = owner_data.get("plan", "free")
        code_end = data.get("codeAccessEndsAt")
        if isinstance(code_end, datetime) and code_end > now and status not in {"active", "trial"}:
            status, paid_end = "active", code_end
            data["plan"] = "access-code"
        return {
            "id": uid,
            "email": user.email or "",
            "displayName": data.get("displayName") or user.display_name or "Explorador",
            "emailVerified": bool(user.email_verified),
            "isAdmin": (user.custom_claims or {}).get("admin") is True,
            "plan": data.get("plan", "free") if status == "active" else "free",
            "subscriptionStatus": status,
            "accessEndsAt": (trial_end.isoformat() if status == "trial" and isinstance(trial_end, datetime)
                             else paid_end.isoformat() if isinstance(paid_end, datetime) else None),
            "subscriptionEndsAt": paid_end.isoformat() if isinstance(paid_end, datetime) else None,
            "duoInviteEmail": data.get("duoInviteEmail"),
        }

    def require_verified(self, claims: dict[str, Any]) -> None:
        if not claims.get("email_verified"):
            raise HTTPException(status_code=403, detail="Confirme seu e-mail antes de continuar.")

    def rate_limit(self, scope: str, key: str, *, limit: int, window_seconds: int) -> None:
        from google.cloud import firestore as google_firestore

        now = int(time.time())
        doc_id = opaque_hash(f"{scope}:{key}", self.settings.code_hash_pepper)
        ref = self.db.collection("rateLimits").document(doc_id)
        transaction = self.db.transaction()

        @google_firestore.transactional
        def increment(txn):
            snapshot = ref.get(transaction=txn)
            data = snapshot.to_dict() if snapshot.exists else {}
            window_start = int(data.get("windowStart", now))
            count = int(data.get("count", 0))
            if now - window_start >= window_seconds:
                window_start, count = now, 0
            if count >= limit:
                raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde e tente novamente.")
            txn.set(ref, {"scope": scope, "windowStart": window_start, "count": count + 1, "expiresAt": now + window_seconds})

        increment(transaction)

    def invite_duo(self, uid: str, email: str) -> dict[str, Any]:
        email = normalize_email(email)
        owner = self.profile(uid)
        if email == owner["email"].lower():
            raise HTTPException(status_code=400, detail="Use o e-mail de outra pessoa.")
        if owner["subscriptionStatus"] not in {"active", "trial"}:
            raise HTTPException(status_code=403, detail="O plano atual não inclui convite Duo.")
        profile_ref = self.db.collection("profiles").document(uid)
        current = profile_ref.get().to_dict() or {}
        previous = current.get("duoInviteEmail")
        changed_at = current.get("duoChangedAt")
        if previous and previous != email and isinstance(changed_at, datetime) and changed_at > datetime.now(UTC) - timedelta(days=7):
            raise HTTPException(status_code=409, detail="A troca do amigo possui carência de sete dias.")
        if previous and previous != email:
            previous_ref = self.db.collection("duoInvites").document(opaque_hash(previous, self.settings.code_hash_pepper))
            previous_data = previous_ref.get().to_dict() or {}
            if previous_data.get("memberUid"):
                self.db.collection("profiles").document(previous_data["memberUid"]).set({"duoOwnerUid": None}, merge=True)
            previous_ref.delete()
        invite_id = opaque_hash(email, self.settings.code_hash_pepper)
        self.db.collection("duoInvites").document(invite_id).set({
            "ownerUid": uid, "emailHash": invite_id, "status": "pending", "createdAt": datetime.now(UTC),
        })
        profile_ref.set({"duoInviteEmail": email, "duoChangedAt": datetime.now(UTC), "updatedAt": datetime.now(UTC)}, merge=True)
        return self.profile(uid)

    def remove_duo(self, uid: str) -> dict[str, Any]:
        ref = self.db.collection("profiles").document(uid)
        data = ref.get().to_dict() or {}
        email = data.get("duoInviteEmail")
        if email:
            invite_ref = self.db.collection("duoInvites").document(opaque_hash(email, self.settings.code_hash_pepper))
            invite_data = invite_ref.get().to_dict() or {}
            if invite_data.get("memberUid"):
                self.db.collection("profiles").document(invite_data["memberUid"]).set({"duoOwnerUid": None}, merge=True)
            invite_ref.delete()
        ref.set({"duoInviteEmail": None, "duoChangedAt": datetime.now(UTC), "updatedAt": datetime.now(UTC)}, merge=True)
        return self.profile(uid)

    async def create_checkout(self, uid: str, plan_id: str) -> str:
        plan = PLAN_CATALOG.get(plan_id)
        if not plan:
            raise HTTPException(status_code=400, detail="Plano inválido.")
        order_id = uuid.uuid4().hex
        self.db.collection("orders").document(order_id).set({
            "uid": uid, "plan": plan_id, "amount": plan["amount"], "currency": "BRL",
            "status": "pending", "createdAt": datetime.now(UTC),
        })
        payload = {
            "items": [{"id": plan_id, "title": plan["label"], "quantity": 1, "currency_id": "BRL", "unit_price": plan["amount"]}],
            "external_reference": order_id,
            "notification_url": f"{self.settings.public_api_base}/v1/webhooks/mercado-pago",
            "back_urls": {
                "success": self.settings.public_app_return_url,
                "pending": self.settings.public_app_return_url,
                "failure": self.settings.public_app_return_url,
            },
            "auto_return": "approved",
        }
        response = await self.http.post(
            "https://api.mercadopago.com/checkout/preferences",
            json=payload,
            headers={"Authorization": f"Bearer {self.settings.mercado_pago_access_token}", "X-Idempotency-Key": order_id},
        )
        if response.status_code >= 400:
            self.db.collection("orders").document(order_id).set({"status": "creation_failed"}, merge=True)
            raise HTTPException(status_code=502, detail="O Mercado Pago não criou o checkout.")
        checkout = response.json().get("init_point", "")
        parsed = urlparse(checkout)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host in {"mercadopago.com", "mercadopago.com.br"} or host.endswith(".mercadopago.com") or host.endswith(".mercadopago.com.br")):
            raise HTTPException(status_code=502, detail="Checkout recusado por domínio inesperado.")
        self.db.collection("orders").document(order_id).set({"preferenceId": response.json().get("id")}, merge=True)
        return checkout

    async def payment(self, payment_id: str) -> dict[str, Any]:
        response = await self.http.get(
            f"https://api.mercadopago.com/v1/payments/{payment_id}",
            headers={"Authorization": f"Bearer {self.settings.mercado_pago_access_token}"},
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail="Pagamento não confirmado no provedor.")
        return response.json()

    def apply_payment(self, payment: dict[str, Any]) -> None:
        from google.cloud import firestore as google_firestore

        order_id = str(payment.get("external_reference", ""))
        if not order_id or payment.get("status") != "approved":
            return
        order_ref = self.db.collection("orders").document(order_id)
        transaction = self.db.transaction()

        @google_firestore.transactional
        def activate(txn):
            order = order_ref.get(transaction=txn)
            if not order.exists:
                raise HTTPException(status_code=400, detail="Pedido desconhecido.")
            data = order.to_dict() or {}
            if data.get("status") == "approved":
                return
            if payment.get("currency_id") != "BRL" or abs(float(payment.get("transaction_amount", -1)) - float(data["amount"])) > 0.001:
                raise HTTPException(status_code=400, detail="Valor do pagamento não corresponde ao pedido.")
            if bool(payment.get("live_mode")) != self.settings.mercado_pago_live_mode:
                raise HTTPException(status_code=400, detail="Ambiente do pagamento incompatível.")
            plan = PLAN_CATALOG[data["plan"]]
            profile_ref = self.db.collection("profiles").document(data["uid"])
            profile = profile_ref.get(transaction=txn).to_dict() or {}
            now = datetime.now(UTC)
            current_end = profile.get("subscriptionEndsAt")
            start = current_end if isinstance(current_end, datetime) and current_end > now else now
            new_end = start + timedelta(days=plan["days"])
            txn.set(profile_ref, {"plan": data["plan"], "subscriptionStatus": "active", "subscriptionEndsAt": new_end, "updatedAt": now}, merge=True)
            txn.set(order_ref, {"status": "approved", "paymentId": str(payment.get("id")), "approvedAt": now}, merge=True)

        activate(transaction)

    def revoke_unused_code(self, admin_uid: str, code: str) -> dict[str, bool]:
        from google.cloud import firestore as google_firestore
        code_id = opaque_hash(code.strip().upper(), self.settings.code_hash_pepper)
        ref = self.db.collection('accessCodes').document(code_id)

        @google_firestore.transactional
        def revoke(txn):
            snapshot = ref.get(transaction=txn)
            if not snapshot.exists:
                raise HTTPException(404, 'Código não encontrado.')
            try:
                update = unused_code_revocation(snapshot.to_dict() or {}, admin_uid, datetime.now(UTC))
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
            if update:
                txn.set(ref, update, merge=True)
        revoke(self.db.transaction())
        return {'revoked': True}

    def redeem_code(self, uid: str, code: str) -> dict[str, Any]:
        from google.cloud import firestore as google_firestore

        normalized = code.strip().upper()
        if not 12 <= len(normalized) <= 128:
            raise HTTPException(status_code=400, detail="Código inválido.")
        code_id = opaque_hash(normalized, self.settings.code_hash_pepper)
        ref = self.db.collection("accessCodes").document(code_id)
        profile_ref = self.db.collection("profiles").document(uid)
        transaction = self.db.transaction()

        @google_firestore.transactional
        def consume(txn):
            snapshot = ref.get(transaction=txn)
            if not snapshot.exists:
                raise HTTPException(status_code=400, detail="Código inválido.")
            data = snapshot.to_dict() or {}
            profile = profile_ref.get(transaction=txn).to_dict() or {}
            try:
                profile_update, code_update, rewards = redemption_updates(data, profile, uid, datetime.now(UTC))
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            txn.set(ref, code_update, merge=True)
            txn.set(profile_ref, profile_update, merge=True)
            return {"ok": True, "rewards": rewards, "codeType": data.get("type", "access")}

        return consume(transaction)

    def delete_account(self, claims: dict[str, Any]) -> None:
        now = int(time.time())
        if now - int(claims.get("auth_time", 0)) > 600:
            raise HTTPException(status_code=401, detail="Entre novamente antes de excluir a conta.")
        uid = claims["uid"]
        uid_hash = opaque_hash(uid, self.settings.code_hash_pepper)
        for order in self.db.collection("orders").where("uid", "==", uid).stream():
            order.reference.set({"uid": None, "deletedAccountHash": uid_hash}, merge=True)
        for invite in self.db.collection("duoInvites").where("ownerUid", "==", uid).stream():
            invite_data = invite.to_dict() or {}
            if invite_data.get("memberUid"):
                self.db.collection("profiles").document(invite_data["memberUid"]).set({"duoOwnerUid": None}, merge=True)
            invite.reference.delete()
        for invitation in self.db.collection("duoInvites").where("memberUid", "==", uid).stream():
            invitation.reference.set({"memberUid": None, "status": "revoked"}, merge=True)
        for code in self.db.collection("accessCodes").where("usedBy", "==", uid).stream():
            code.reference.set({"usedBy": None, "deletedAccountHash": uid_hash}, merge=True)
        self.db.collection("profiles").document(uid).delete()
        self.auth.revoke_refresh_tokens(uid)
        self.auth.delete_user(uid)

    def export_account(self, uid: str) -> dict[str, Any]:
        profile_snapshot = self.db.collection("profiles").document(uid).get()
        profile = profile_snapshot.to_dict() or {}
        orders = []
        for order in self.db.collection("orders").where("uid", "==", uid).stream():
            data = order.to_dict() or {}
            orders.append({
                "id": order.id,
                "plan": data.get("plan"),
                "amount": data.get("amount"),
                "currency": data.get("currency"),
                "status": data.get("status"),
                "createdAt": data.get("createdAt"),
                "approvedAt": data.get("approvedAt"),
            })
        redemptions = []
        for code in self.db.collection("accessCodes").where("usedBy", "==", uid).stream():
            data = code.to_dict() or {}
            redemptions.append({
                "type": data.get("type"),
                "rewards": list(data.get("rewards") or []),
                "usedAt": data.get("usedAt"),
            })
        # Device hashes and internal anti-abuse keys are deliberately omitted.
        return {
            "schema": 1,
            "exportedAt": datetime.now(UTC),
            "account": {
                "uid": uid,
                "email": self.auth.get_user(uid).email or "",
                "displayName": profile.get("displayName"),
                "plan": profile.get("plan"),
                "subscriptionStatus": profile.get("subscriptionStatus"),
                "trialStartedAt": profile.get("trialStartedAt"),
                "trialEndsAt": profile.get("trialEndsAt"),
                "subscriptionEndsAt": profile.get("subscriptionEndsAt"),
                "createdAt": profile.get("createdAt"),
            },
            "orders": orders,
            "redemptions": redemptions,
        }
