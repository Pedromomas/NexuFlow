"""Access-code policy. `now` must come from the server, never the client."""
from datetime import datetime, timedelta


def unused_code_revocation(data: dict, admin_uid: str, now: datetime) -> dict:
    if data.get('usedAt') or data.get('usedBy') or data.get('deletedAccountHash'):
        raise ValueError('Código já resgatado. Revogar o benefício exige revisão separada.')
    if data.get('revoked'):
        return {}
    return {'revoked': True, 'revokedBy': admin_uid, 'revokedAt': now}


def redemption_updates(data: dict, profile: dict, uid: str, now: datetime):
    if data.get('revoked') or data.get('usedAt') or data.get('usedBy') or data.get('deletedAccountHash'):
        raise ValueError('Código indisponível.')
    deadline = data.get('redeemBefore')
    if deadline is not None and (not isinstance(deadline, datetime) or deadline.tzinfo is None or deadline <= now):
        raise ValueError('Código expirado.')
    rewards = list(data.get('rewards') or [])
    if any(item not in {'theme:origin', 'theme:rio', 'theme:kiwi', 'premium:lifetime'} for item in rewards):
        raise ValueError('Recompensa inválida.')
    if sum(item.startswith('theme:') for item in rewards) > 1:
        raise ValueError('Cada código pode liberar apenas um tema.')
    days = data.get('durationDays')
    if days is not None and (type(days) is not int or not 1 <= days <= 365 or 'premium:lifetime' in rewards):
        raise ValueError('Duração inválida.')
    if not rewards and days is None:
        raise ValueError('Código sem benefício.')
    update = {'entitlements': sorted(set(profile.get('entitlements') or []).union(rewards)), 'updatedAt': now}
    if 'premium:lifetime' in rewards:
        update.update(plan='lifetime', subscriptionStatus='active', subscriptionEndsAt=None)
    elif days is not None:
        current = profile.get('codeAccessEndsAt')
        start = current if isinstance(current, datetime) and current > now else now
        update['codeAccessEndsAt'] = start + timedelta(days=days)
    return update, {'usedBy': uid, 'usedAt': now}, rewards
