"""Admin policy independent of HTTP and persistence for local verification."""
import secrets
from datetime import datetime


def require_admin_claims(claims: dict, now: int) -> None:
    # These claims must be obtained from Firebase's verified token or user record.
    if claims.get('admin') is not True or claims.get('email_verified') is not True:
        raise PermissionError('Acesso exclusivo de administrador com e-mail confirmado.')
    authenticated_at = claims.get('auth_time')
    if type(authenticated_at) is not int or not 0 <= now - authenticated_at <= 600:
        raise PermissionError('Entre novamente para administrar códigos e usuários.')


def make_code_document(*, theme: str | None, days: int | None, lifetime: bool,
                       redeem_before: datetime | None, now: datetime, admin_uid: str):
    if theme is not None and theme not in {'origin', 'rio', 'kiwi'}:
        raise ValueError('Tema inválido.')
    if days is not None and (type(days) is not int or not 1 <= days <= 365 or lifetime):
        raise ValueError('Escolha de 1 a 365 dias ou acesso vitalício.')
    if not theme and days is None and not lifetime:
        raise ValueError('Selecione um benefício.')
    if redeem_before is not None and (redeem_before.tzinfo is None or redeem_before <= now):
        raise ValueError('O limite para resgate precisa ser uma data futura com fuso horário.')
    code = 'NEXU-' + secrets.token_hex(16).upper()
    return code, {
        'type': 'lifetime' if lifetime else 'timed' if days else 'theme',
        'rewards': ([f'theme:{theme}'] if theme else []) + (['premium:lifetime'] if lifetime else []),
        'durationDays': days, 'redeemBefore': redeem_before,
        'singleUse': True, 'revoked': False, 'usedBy': None,
        'createdAt': now, 'createdBy': admin_uid,
    }
