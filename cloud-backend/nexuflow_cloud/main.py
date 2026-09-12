from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field

from .config import Settings
from .admin import require_admin_claims, make_code_document
from .security import opaque_hash, sign_license, verify_mp_webhook
from .services import CloudServices
from .pagbank import SandboxGateway, verify_notification
from .legal import router as legal_router


class RegisterBody(BaseModel):
    displayName: str = Field(min_length=2, max_length=50)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    acceptedTerms: bool = Field(default=False, strict=True)
    legalVersion: str = Field(default='', max_length=80)


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)


class ResetBody(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class RefreshBody(BaseModel):
    refreshToken: str = Field(min_length=20, max_length=4096)


class EmailBody(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class CheckoutBody(BaseModel):
    plan: str = Field(min_length=3, max_length=16)


class CodeBody(BaseModel):
    code: str = Field(min_length=12, max_length=128)


class LicenseBody(BaseModel):
    installationToken: str = Field(min_length=32, max_length=256)


class AdminCodeBody(BaseModel):
    theme: str | None = None
    days: int | None = Field(default=None, ge=1, le=365, strict=True)
    lifetime: bool = False
    redeemBefore: datetime | None = None


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings.from_env()


@lru_cache(maxsize=1)
def services() -> CloudServices:
    return CloudServices(settings())


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    if services.cache_info().currsize:
        await services().close()


app = FastAPI(
    title="NexuFlow Cloud API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.include_router(legal_router)


@app.middleware("http")
async def deployment_gate(request: Request, call_next):
    # A first deployment must not expose unfinished account/payment integrations.
    if request.url.path.startswith("/v1/") and os.getenv("NEXUFLOW_API_ENABLED", "false").lower() != "true":
        return JSONResponse(status_code=503, content={"detail": "Servico em configuracao. Tente novamente mais tarde."})
    if request.url.path.rstrip('/') == "/v1/auth/register" and os.getenv("NEXUFLOW_REGISTRATION_ENABLED", "false") != "true":
        return JSONResponse(status_code=503, content={"detail": "Novos cadastros ainda não liberados. Contas existentes podem entrar normalmente."})
    sandbox_path = request.url.path.startswith("/v1/admin/pagbank/") or request.url.path == "/v1/webhooks/pagbank"
    if sandbox_path and os.getenv("NEXUFLOW_PAGBANK_SANDBOX_ENABLED", "false") != "true":
        return JSONResponse(status_code=503, content={"detail": "Testes PagBank ainda não disponíveis."})
    if not sandbox_path and request.url.path.startswith(("/v1/billing/", "/v1/webhooks/")) and os.getenv("NEXUFLOW_BILLING_ENABLED", "false").lower() != "true":
        return JSONResponse(status_code=503, content={"detail": "Pagamentos ainda nao disponiveis."})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in os.environ.get("ALLOWED_ORIGINS", "https://tauri.localhost,http://tauri.localhost").split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Signature"],
    max_age=600,
)


def client_key(request: Request, email: str = "") -> str:
    # Cloud Run appends the actual client address to X-Forwarded-For. Reading
    # the right-most value avoids trusting an address prepended by the caller.
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[-1].strip()
    address = forwarded or (request.client.host if request.client else "unknown")
    return f"{address}:{email.strip().lower()}"


def bearer_claims(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Entre na sua conta para continuar.")
    return services().verify_token(authorization.removeprefix("Bearer ").strip())


def admin_claims(claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, Any]:
    try:
        require_admin_claims(claims, int(time.time()))
        # Check the current record too, so removing the role takes effect without
        # waiting for an old ID token to expire.
        user = services().auth.get_user(claims['uid'])
        if user.disabled or not user.email_verified or (user.custom_claims or {}).get('admin') is not True:
            raise PermissionError('Permissão administrativa removida.')
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return claims


@app.get('/v1/admin/users')
def admin_find_user(request: Request, email: str = Query(min_length=3, max_length=254),
                    claims: dict[str, Any] = Depends(admin_claims)) -> dict[str, Any]:
    from .security import normalize_email
    gateway = services()
    gateway.rate_limit('admin-search', claims['uid'], limit=30, window_seconds=900)
    try:
        normalized = normalize_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        user = gateway.auth.get_user_by_email(normalized)
    except gateway.auth.UserNotFoundError:
        return {'users': []}
    # Read-only: do not call profile(), which may start a trial or accept a Duo invite.
    data = gateway.db.collection('profiles').document(user.uid).get().to_dict() or {}
    return {'users': [{'id': user.uid, 'email': user.email, 'displayName': user.display_name,
                      'emailVerified': user.email_verified, 'disabled': user.disabled,
                      'plan': data.get('plan', 'free'),
                      'subscriptionEndsAt': data.get('subscriptionEndsAt'),
                      'codeAccessEndsAt': data.get('codeAccessEndsAt')}]}


@app.post('/v1/admin/codes', status_code=201)
def admin_create_code(body: AdminCodeBody, claims: dict[str, Any] = Depends(admin_claims)) -> dict[str, Any]:
    gateway = services()
    gateway.rate_limit('admin-create-code', claims['uid'], limit=20, window_seconds=3600)
    try:
        code, data = make_code_document(theme=body.theme, days=body.days, lifetime=body.lifetime,
                                       redeem_before=body.redeemBefore, now=datetime.now(UTC),
                                       admin_uid=claims['uid'])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    code_id = opaque_hash(code, settings().code_hash_pepper)
    gateway.db.collection('accessCodes').document(code_id).create(data)
    return {'id': code_id, 'code': code, 'type': data['type'], 'durationDays': data['durationDays']}


@app.post('/v1/admin/codes/revoke')
def admin_revoke_code(body: CodeBody, claims: dict[str, Any] = Depends(admin_claims)) -> dict[str, bool]:
    gateway = services()
    gateway.rate_limit('admin-revoke-code', claims['uid'], limit=20, window_seconds=3600)
    return gateway.revoke_unused_code(claims['uid'], body.code)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "nexuflow-cloud", "version": app.version}


def pagbank_sandbox() -> SandboxGateway:
    gateway = services()
    try:
        return SandboxGateway(gateway.http, gateway.db,
            os.getenv("PAGBANK_ACCESS_TOKEN", ""), os.getenv("PAGBANK_ENVIRONMENT", "sandbox"),
            settings().public_api_base)
    except ValueError as exc:
        raise HTTPException(503, "PagBank de testes não configurado.") from exc


@app.get("/billing/return", response_class=HTMLResponse)
def billing_return():
    return """<!doctype html><html lang="pt-BR"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NexuFlow — Pagamento</title><main><h1>Volte ao NexuFlow</h1>
    <p>Esta página não confirma o pagamento. A confirmação depende da consulta ao PagBank.</p>
    <p>Compras no ambiente de testes não liberam uma assinatura real.</p></main></html>"""


@app.post("/v1/admin/pagbank/checkout")
async def sandbox_checkout(body: CheckoutBody, claims: dict[str, Any] = Depends(admin_claims)):
    services().rate_limit("sandbox-checkout", claims["uid"], limit=5, window_seconds=900)
    try:
        return await pagbank_sandbox().create(claims["uid"], body.plan)
    except ValueError as exc:
        raise HTTPException(400, "Checkout de testes inválido.") from exc


@app.post("/v1/webhooks/pagbank")
async def pagbank_webhook(request: Request):
    import json
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 262144:
            raise HTTPException(413, "Notificação muito grande.")
    if not verify_notification(raw_body=bytes(raw),
            signature=request.headers.get("x-authenticity-token"),
            token=os.getenv("PAGBANK_ACCESS_TOKEN", "")):
        raise HTTPException(401, "Notificação não autenticada.")
    try:
        data = json.loads(raw)
        provider_id = data["id"]
        if not isinstance(provider_id, str):
            raise ValueError()
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, "Notificação inválida.") from exc
    await pagbank_sandbox().reconcile(provider_id)
    return {"ok": True}


@app.post("/v1/auth/register", status_code=201)
async def register(body: RegisterBody, request: Request) -> dict[str, str]:
    published_version = os.getenv("NEXUFLOW_PUBLISHED_LEGAL_VERSION", "")
    if not published_version or 'draft' in published_version.lower():
        raise HTTPException(503, "Documentos de cadastro ainda em revisão.")
    if not body.acceptedTerms or body.legalVersion != published_version:
        raise HTTPException(409, "Leia os documentos atuais e confirme antes de criar a conta.")
    gateway = services()
    gateway.rate_limit("register", client_key(request, body.email), limit=5, window_seconds=3600)
    return await gateway.register(body.displayName, body.email, body.password, legal_version=published_version)


@app.post("/v1/auth/login")
async def login(body: LoginBody, request: Request) -> dict[str, Any]:
    gateway = services()
    gateway.rate_limit("login", client_key(request, body.email), limit=5, window_seconds=900)
    return await gateway.login(body.email, body.password)


@app.post("/v1/auth/password-reset")
async def password_reset(body: ResetBody, request: Request) -> dict[str, str]:
    gateway = services()
    gateway.rate_limit("password-reset", client_key(request, body.email), limit=3, window_seconds=3600)
    return await gateway.reset_password(body.email)


@app.post("/v1/auth/verify-email")
async def resend_verification(authorization: Annotated[str | None, Header()] = None,
                              claims: dict[str, Any] = Depends(bearer_claims)):
    gateway = services()
    if claims.get("email_verified"):
        return {"message": "Seu e-mail já está confirmado."}
    gateway.rate_limit("verify-email", claims["uid"], limit=3, window_seconds=3600)
    # Only the authenticated user's token determines the recipient.
    await gateway._identity("sendOobCode", {
        "requestType": "VERIFY_EMAIL", "idToken": authorization.removeprefix("Bearer ").strip(),
    })
    return {"message": "Confirmação enviada. Confira sua caixa de entrada e spam."}


@app.post("/v1/auth/refresh")
async def refresh(body: RefreshBody, request: Request) -> dict[str, Any]:
    gateway = services()
    gateway.rate_limit("refresh", client_key(request), limit=30, window_seconds=3600)
    return await gateway.refresh(body.refreshToken)


@app.get("/v1/account/profile")
def profile(claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, Any]:
    return services().profile(claims["uid"])


@app.post("/v1/account/duo-invite")
def duo_invite(body: EmailBody, claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, Any]:
    gateway = services()
    gateway.require_verified(claims)
    return gateway.invite_duo(claims["uid"], body.email)


@app.delete("/v1/account/duo-invite")
def duo_remove(claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, Any]:
    return services().remove_duo(claims["uid"])


@app.post("/v1/billing/checkout")
async def checkout(body: CheckoutBody, request: Request, claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, str]:
    gateway = services()
    gateway.require_verified(claims)
    gateway.rate_limit("checkout", client_key(request, claims["uid"]), limit=5, window_seconds=900)
    checkout_url = await gateway.create_checkout(claims["uid"], body.plan)
    return {"checkoutUrl": checkout_url}


@app.post("/v1/webhooks/mercado-pago")
async def mercado_pago_webhook(
    request: Request,
    data_id: str = Query(alias="data.id", min_length=1, max_length=128),
    x_signature: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    config = settings()
    if not x_signature or not x_request_id or not verify_mp_webhook(
        header=x_signature,
        request_id=x_request_id,
        data_id=data_id,
        secret=config.mercado_pago_webhook_secret,
    ):
        raise HTTPException(status_code=401, detail="Webhook inválido.")
    gateway = services()
    payment = await gateway.payment(data_id)
    gateway.apply_payment(payment)
    return {"ok": True}


@app.post("/v1/codes/redeem")
def redeem_code(body: CodeBody, request: Request, claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, Any]:
    gateway = services()
    gateway.require_verified(claims)
    gateway.rate_limit("redeem-code", client_key(request, claims["uid"]), limit=5, window_seconds=900)
    return gateway.redeem_code(claims["uid"], body.code)


@app.post("/v1/license")
def license_document(body: LicenseBody, request: Request, claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, Any]:
    from google.cloud import firestore as google_firestore

    gateway = services()
    gateway.require_verified(claims)
    gateway.rate_limit("license", client_key(request, claims["uid"]), limit=10, window_seconds=3600)
    profile_data = gateway.profile(claims["uid"])
    installation_hash = opaque_hash(body.installationToken, settings().code_hash_pepper)
    profile_ref = gateway.db.collection("profiles").document(claims["uid"])
    transaction = gateway.db.transaction()

    @google_firestore.transactional
    def reserve_device(txn):
        raw = profile_ref.get(transaction=txn).to_dict() or {}
        devices = dict(raw.get("devices") or {})
        if installation_hash not in devices and len(devices) >= 2:
            raise HTTPException(status_code=409, detail="Limite de dispositivos atingido.")
        devices[installation_hash] = devices.get(installation_hash) or datetime.now(UTC).isoformat()
        txn.set(profile_ref, {"devices": devices, "updatedAt": datetime.now(UTC)}, merge=True)
        return sorted(set(raw.get("entitlements") or []))

    entitlements = reserve_device(transaction)
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=24)
    if profile_data["subscriptionStatus"] in {"active", "trial"} and profile_data.get("accessEndsAt"):
        expires_at = min(expires_at, datetime.fromisoformat(profile_data["accessEndsAt"]))
    payload = {
        "schema": 1,
        "subject": opaque_hash(claims["uid"], settings().code_hash_pepper),
        "installation": installation_hash,
        "status": profile_data["subscriptionStatus"],
        "plan": profile_data["plan"],
        "entitlements": entitlements,
        "issuedAt": now.isoformat(),
        "expiresAt": expires_at.isoformat(),
    }
    return sign_license(payload, settings().license_private_key)


@app.get("/v1/account/export")
def export_account(claims: dict[str, Any] = Depends(bearer_claims)) -> dict[str, Any]:
    return services().export_account(claims["uid"])


@app.post("/v1/account/delete-request", status_code=204)
def delete_account(claims: dict[str, Any] = Depends(bearer_claims)) -> None:
    services().delete_account(claims)
