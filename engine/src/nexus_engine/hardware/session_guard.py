from __future__ import annotations

import os

import psutil

from ..anti_cheat import running_protected_games


# A session guard that guesses which process is "unimportant" is not safe.
# These names are therefore advisory signals only; they are never terminated,
# suspended, reprioritized or opened for mutation by this module.
ADVISORY_BACKGROUND_NAMES = frozenset(
    {
        "discord.exe",
        "onedrive.exe",
        "googledrivesync.exe",
        "dropbox.exe",
        "steamwebhelper.exe",
    }
)


def session_guard_report() -> dict:
    """Return a privacy-minimized, read-only background-pressure preview.

    Version 1.5 intentionally ships the advisor before priority mutation. A
    future opt-in implementation must use an exact user allow-list, persist the
    original priority and restore it by PID *and* creation time. It must also
    remain completely disabled whenever a protected runtime is active.
    """
    protected = running_protected_games()
    if protected:
        return {
            "schema": 1,
            "available": True,
            "read_only": True,
            "deferred": True,
            "mutation_enabled": False,
            "protected_games": protected,
            "candidate_count": 0,
            "candidates": [],
            "reason": "A análise por processo é adiada durante a sessão protegida.",
        }

    candidates: set[str] = set()
    inspected = 0
    try:
        for process in psutil.process_iter(["name"]):
            try:
                name = str(process.info.get("name") or "").casefold()
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
                continue
            if not name:
                continue
            inspected += 1
            if name in ADVISORY_BACKGROUND_NAMES:
                candidates.add(name)
    except psutil.Error:
        return {
            "schema": 1,
            "available": False,
            "read_only": True,
            "deferred": False,
            "mutation_enabled": False,
            "candidate_count": 0,
            "candidates": [],
            "reason": "A lista de processos não pôde ser consultada.",
        }

    return {
        "schema": 1,
        "available": True,
        "read_only": True,
        "deferred": False,
        "mutation_enabled": False,
        "platform_supported": os.name == "nt",
        "processes_observed": inspected,
        "candidate_count": len(candidates),
        "candidates": sorted(candidates),
        "privacy": "Somente nomes conhecidos; sem PID, caminho, janela, módulos ou conteúdo.",
        "reason": (
            "A 1.5 apenas sugere possíveis fontes de carga. Ela não reduz prioridade nem fecha aplicativos automaticamente."
        ),
        "future_mutation_contract": {
            "opt_in_required": True,
            "exact_user_allowlist_required": True,
            "restore_original_priority_required": True,
            "disabled_during_protected_runtime": True,
        },
    }
