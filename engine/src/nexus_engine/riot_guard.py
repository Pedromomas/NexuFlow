"""Backward-compatible Riot guard imports.

New code should import :mod:`nexus_engine.anti_cheat`, which also contains the
Valve VAC/Trusted Mode policy.
"""
from .anti_cheat import (
    RIOT_GAME_IDS,
    VANGUARD_PROCESS_NAMES,
    anti_cheat_policy_report,
    effective_profile,
    is_riot_game,
    vanguard_processes,
)


def riot_policy_report(game_id, requested, effective):
    return anti_cheat_policy_report(game_id, requested, effective)


__all__ = [
    "RIOT_GAME_IDS",
    "VANGUARD_PROCESS_NAMES",
    "effective_profile",
    "is_riot_game",
    "riot_policy_report",
    "vanguard_processes",
]
