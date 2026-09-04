from __future__ import annotations

from dataclasses import dataclass

import psutil

from .models import BoostProfile

RIOT_GAME_IDS = frozenset({"valorant", "lol"})
VALVE_GAME_IDS = frozenset({"cs2"})
EAC_GAME_IDS = frozenset({"fortnite", "fallguys"})
BATTLEYE_GAME_IDS = frozenset({"fortnite", "pubg", "rainbow6", "dayz", "arma3"})
PROTECTED_GAME_IDS = RIOT_GAME_IDS | VALVE_GAME_IDS | EAC_GAME_IDS | BATTLEYE_GAME_IDS
KNOWN_MUTABLE_GAME_IDS = frozenset({"roblox"})

# Policy metadata is intentionally shipped in the engine so every transport
# (Tauri, FastAPI and CLI) reports the same compatibility posture.
POLICY_VERSION = "2026.09.04"
POLICY_REVIEWED_AT = "2026-09-04"
OFFICIAL_POLICY_SOURCES = (
    "https://www.riotgames.com/en/DevRel/vanguard-faq",
    "https://support-developer.riotgames.com/hc/en-us/articles/28021427366163-Vanguard",
    "https://www.riotgames.com/en/terms-of-service",
    "https://help.steampowered.com/en/faqs/view/09A0-4879-4353-EF95",
    "https://help.steampowered.com/en/faqs/view/571A-97DA-70E9-FF74",
    "https://help.steampowered.com/en/faqs/view/22C0-03D0-AE4B-04E8",
    "https://en.help.roblox.com/hc/en-us/articles/24275616578708-Anti-cheat-Messages",
    "https://www.easy.ac/support/articles",
    "https://www.battleye.com/support/faq/",
)

# Vanguard's user-mode components. The kernel driver is deliberately not
# queried, opened, stopped, inspected or otherwise interacted with by NexuFlow.
VANGUARD_PROCESS_NAMES = frozenset({"vgtray.exe", "vgc.exe"})

# Process names are used only for read-only classification. Protected-game
# discovery never asks for module lists, threads, loaded DLLs, game memory or
# per-process sockets.
PROTECTED_PROCESS_TO_GAME = {
    "valorant-win64-shipping.exe": "valorant",
    "league of legends.exe": "lol",
    "cs2.exe": "cs2",
    "fortniteclient-win64-shipping.exe": "fortnite",
    "fortniteclient-win64-shipping_eac_eos.exe": "fortnite",
    "fortniteclient-win64-shipping_be.exe": "fortnite",
    "fallguys_client_game.exe": "fallguys",
    "tslgame.exe": "pubg",
    "rainbowsix.exe": "rainbow6",
    "rainbowsix_vulkan.exe": "rainbow6",
    "rainbowsix_dx11.exe": "rainbow6",
    "dayz_x64.exe": "dayz",
    "dayz.exe": "dayz",
    "arma3_x64.exe": "arma3",
    "arma3.exe": "arma3",
}

# Names only: no handles, modules, memory or sockets are inspected. Generic
# runtimes deliberately force the most restrictive protected policy.
PROTECTED_RUNTIME_NAMES = frozenset({
    "easyanticheat.exe", "easyanticheat_eos.exe", "easyanticheat_launcher.exe",
    "beservice.exe", "beservices.exe", "battleye.exe",
})

# Windows service metadata is queried read-only. EAC and BattlEye service names
# vary slightly between games, so classification accepts their documented base
# names plus per-title suffixes. Vanguard is intentionally separate: vgk/vgc can
# remain installed or running when no Riot game is active, so their presence is
# environmental evidence only and must never trigger a global mutation lock.
EAC_SERVICE_PREFIXES = frozenset({"easyanticheat", "easyanticheateos"})
BATTLEYE_SERVICE_PREFIXES = frozenset({"beservice", "battleye"})
VANGUARD_SERVICE_NAMES = frozenset({"vgk", "vgc"})

# These operations are forbidden by NexuFlow's own compatibility policy while
# any protected title is running. This is deliberately stricter than merely
# avoiding known cheat APIs: it reduces accidental interaction surface.
BLOCKED_MUTATIONS_DURING_PROTECTED_RUNTIME = frozenset(
    {
        "process_optimization",
        "process_priority",
        "cpu_sets",
        "endpoint_firewall_steering",
        "dns_mutation",
        "mtu_mutation",
        "tcp_registry_tweaks",
        "standby_list_purge",
        "service_pausing",
        "network_reset",
        "game_file_mutation",
        "packet_interception_or_modification",
        "input_automation",
        "anti_cheat_manipulation",
    }
)


class ProtectedGameMutationError(RuntimeError):
    """Raised when a protected-game lockdown blocks a system mutation."""


@dataclass(frozen=True, slots=True)
class CompatibilityCapabilities:
    read_only_process_detection: bool = True
    system_telemetry: bool = True
    network_quality_sampling: bool = True
    route_diagnostics: bool = True
    dns_benchmark: bool = True
    pmtu_measurement: bool = True
    power_plan: bool = True
    crash_safe_rollback: bool = True

    process_optimization: bool = False
    endpoint_firewall_steering: bool = False
    dns_mutation_during_game: bool = False
    mtu_mutation_during_game: bool = False
    tcp_registry_tweaks: bool = False
    standby_list_purge: bool = False
    service_pausing: bool = False
    network_reset: bool = False
    game_socket_inspection: bool = False
    process_memory_access: bool = False
    dll_or_code_injection: bool = False
    graphics_hooks: bool = False
    input_automation: bool = False
    game_file_modification: bool = False
    anti_cheat_service_or_driver_access: bool = False
    powershell_execution_during_protected_session: bool = False
    arbitrary_game_endpoint_probing_during_game: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            field: bool(getattr(self, field))
            for field in self.__dataclass_fields__
        }


PROTECTED_CAPABILITIES = CompatibilityCapabilities()


def normalize_game_id(game_id: str | None) -> str:
    return (game_id or "").strip().lower()


def is_riot_game(game_id: str | None) -> bool:
    return normalize_game_id(game_id) in RIOT_GAME_IDS


def is_valve_game(game_id: str | None) -> bool:
    return normalize_game_id(game_id) in VALVE_GAME_IDS


def is_protected_game(game_id: str | None) -> bool:
    return normalize_game_id(game_id) in PROTECTED_GAME_IDS


def boost_objective(requested: BoostProfile) -> str:
    """Keep the user's goal independent from the anti-cheat safety overlay."""
    if requested is BoostProfile.PING:
        return "ping"
    if requested is BoostProfile.PC:
        return "pc"
    if requested is BoostProfile.HARDCORE_SAFE:
        return "hardcore_safe"
    # Auto, Complete and legacy per-game profiles all request the complete
    # safe feature set. The effective anti-cheat profile still decides what is
    # actually allowed.
    return "complete"


def _iter_process_names() -> list[tuple[int, str]]:
    """Return ordinary PID/name metadata only.

    This helper intentionally does not request executable paths, modules,
    handles, threads, memory maps or networking tables for protected games.
    """
    result: list[tuple[int, str]] = []
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = int(proc.info.get("pid") or 0)
                name = str(proc.info.get("name") or "").lower()
                if pid and name:
                    result.append((pid, name))
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
                continue
    except psutil.Error:
        return []
    return result


def _canonical_service_key(value: str | None) -> str:
    """Normalize a service or display name without executing any service API."""
    return "".join(character for character in str(value or "").casefold() if character.isalnum())


def _service_family(name: str, display_name: str) -> str | None:
    """Classify only well-known anti-cheat service names.

    The real service name is authoritative. The display name is a read-only
    fallback for game-specific EAC/BattlEye registrations. Vanguard deliberately
    requires the exact vgk/vgc service name to avoid broad "Riot" false positives.
    """
    service_key = _canonical_service_key(name)
    display_key = _canonical_service_key(display_name)

    if service_key in VANGUARD_SERVICE_NAMES:
        return "vanguard_environment"
    if any(service_key.startswith(prefix) for prefix in EAC_SERVICE_PREFIXES):
        return "eac"
    if any(service_key.startswith(prefix) for prefix in BATTLEYE_SERVICE_PREFIXES):
        return "battleye"
    if any(display_key.startswith(prefix) for prefix in EAC_SERVICE_PREFIXES):
        return "eac"
    if any(display_key.startswith(prefix) for prefix in BATTLEYE_SERVICE_PREFIXES):
        return "battleye"
    return None


def _read_only_windows_services() -> tuple[bool, list[dict[str, str]]]:
    """Return service name/display/status metadata without controlling services.

    psutil's Windows service iterator only queries SCM metadata here. NexuFlow
    never calls start(), stop(), restart(), changes configuration, or opens a
    service/driver device. If enumeration is unavailable or denied, ``available``
    is false and callers retain the existing process/catalog/Unknown-Safe policy.
    Query failure is never treated as proof that an anti-cheat is absent, but it
    also does not globally lock a machine merely because SCM access was denied.
    """
    iterator = getattr(psutil, "win_service_iter", None)
    if not callable(iterator):
        return False, []

    observations: list[dict[str, str]] = []
    try:
        services = iterator()
        for service in services:
            try:
                name = str(service.name() or "")
            except (psutil.Error, OSError, RuntimeError, TypeError, ValueError):
                continue

            try:
                display_name = str(service.display_name() or "")
            except (psutil.Error, OSError, RuntimeError, TypeError, ValueError):
                display_name = ""

            try:
                status = str(service.status() or "unknown").casefold()
            except (psutil.Error, OSError, RuntimeError, TypeError, ValueError):
                status = "unknown"

            if name:
                observations.append(
                    {
                        "name": name,
                        "display_name": display_name,
                        "status": status,
                    }
                )
    except (psutil.Error, OSError, RuntimeError, TypeError, ValueError):
        return False, []

    return True, observations


def protected_service_signals() -> dict:
    """Observe anti-cheat service signals without opening a service or driver.

    Only a RUNNING EAC/BattlEye service is an active generic protected runtime.
    vgk/vgc observations are returned separately as environmental evidence and
    never make the global protected-runtime flag active by themselves.
    """
    available, observations = _read_only_windows_services()
    protected_runtime_services: list[dict[str, str]] = []
    vanguard_environment_services: list[dict[str, str]] = []

    for observation in observations:
        family = _service_family(observation["name"], observation["display_name"])
        if family == "vanguard_environment":
            vanguard_environment_services.append(observation)
        elif family in {"eac", "battleye"} and observation["status"] == "running":
            protected_runtime_services.append({**observation, "family": family})

    protected_runtime_services.sort(key=lambda item: item["name"].casefold())
    vanguard_environment_services.sort(key=lambda item: item["name"].casefold())
    return {
        "available": available,
        "protected_runtime_services": protected_runtime_services,
        "vanguard_environment_services": vanguard_environment_services,
    }


def running_protected_services() -> list[str]:
    """Return RUNNING EAC/BattlEye service names; Vanguard is excluded."""
    signals = protected_service_signals()
    return [item["name"] for item in signals["protected_runtime_services"]]


def vanguard_processes() -> list[str]:
    """Read-only user-mode process-name observation; never manipulates Vanguard."""
    return sorted({name for _pid, name in _iter_process_names() if name in VANGUARD_PROCESS_NAMES})


def running_protected_games() -> list[str]:
    """Return protected ids from read-only process and service metadata."""
    games = {
        game_id
        for _pid, name in _iter_process_names()
        if (
            game_id := (
                PROTECTED_PROCESS_TO_GAME.get(name)
                or ("protected_runtime" if name in PROTECTED_RUNTIME_NAMES else None)
            )
        )
    }
    if running_protected_services():
        games.add("protected_runtime")
    return sorted(games)


def protected_pid_game(pid: int) -> str | None:
    """Classify a PID without opening the protected process for optimization.

    Only process-list PID/name metadata is consulted. NexuFlow never requests
    VM_READ/VM_WRITE, modules, threads or injection-oriented handles here.
    """
    try:
        wanted = int(pid)
    except (TypeError, ValueError):
        return None
    for proc_pid, name in _iter_process_names():
        if proc_pid == wanted:
            return PROTECTED_PROCESS_TO_GAME.get(name)
    return None


def protected_runtime_context() -> dict:
    games = running_protected_games()
    service_signals = protected_service_signals()
    return {
        "active": bool(games),
        "games": games,
        "vanguard_user_processes": vanguard_processes(),
        "service_scan_available": service_signals["available"],
        "protected_runtime_services": service_signals["protected_runtime_services"],
        "vanguard_environment_services": service_signals["vanguard_environment_services"],
        "policy_version": POLICY_VERSION,
        "reviewed_at": POLICY_REVIEWED_AT,
    }


def assert_mutation_allowed(
    action: str,
    *,
    game_id: str | None = None,
    pid: int | None = None,
) -> None:
    """Defense-in-depth guard used by low-level mutation modules.

    A UI/Orchestrator policy bug must not be enough to make a protected-game
    mutation happen. The low-level manager itself rejects it.
    """
    normalized_action = str(action).strip().lower()
    if normalized_action not in BLOCKED_MUTATIONS_DURING_PROTECTED_RUNTIME:
        return

    explicit_game = normalize_game_id(game_id)
    if explicit_game in PROTECTED_GAME_IDS:
        raise ProtectedGameMutationError(
            f"{normalized_action} is disabled for anti-cheat protected game: {explicit_game}"
        )

    if pid is not None:
        protected = protected_pid_game(pid)
        if protected:
            raise ProtectedGameMutationError(
                f"{normalized_action} is disabled for protected process: {protected}"
            )

    active = running_protected_games()
    if active:
        raise ProtectedGameMutationError(
            f"{normalized_action} is disabled while protected gameplay is active: {', '.join(active)}"
        )


def effective_profile(requested: BoostProfile, game_id: str | None) -> BoostProfile:
    """Resolve profile with one-way anti-cheat downgrades."""
    gid = normalize_game_id(game_id)
    if gid in RIOT_GAME_IDS:
        return BoostProfile.RIOT_SAFE
    if gid in VALVE_GAME_IDS:
        return BoostProfile.VALVE_SAFE
    if gid == "protected_runtime" or gid in EAC_GAME_IDS | BATTLEYE_GAME_IDS:
        return BoostProfile.PROTECTED_SAFE

    # Unknown titles are never allowed to inherit a mutating profile. This is
    # the Safe Core fail-closed boundary.
    if gid and gid not in KNOWN_MUTABLE_GAME_IDS:
        return BoostProfile.UNKNOWN_SAFE

    if requested is BoostProfile.AUTO:
        if gid == "roblox":
            return BoostProfile.ROBLOX
        return BoostProfile.SAFE

    if requested is BoostProfile.HARDCORE_SAFE:
        return BoostProfile.HARDCORE_SAFE

    # A protected profile selected for an unrelated game does not unlock any
    # special behavior; it becomes the ordinary conservative profile.
    if requested in {BoostProfile.RIOT_SAFE, BoostProfile.VALVE_SAFE, BoostProfile.PROTECTED_SAFE, BoostProfile.UNKNOWN_SAFE}:
        return BoostProfile.SAFE

    if requested is BoostProfile.ROBLOX and gid != "roblox":
        return BoostProfile.SAFE

    return requested


def anti_cheat_policy_report(
    game_id: str | None,
    requested: BoostProfile,
    effective: BoostProfile,
) -> dict:
    gid = normalize_game_id(game_id)
    riot = gid in RIOT_GAME_IDS
    valve = gid in VALVE_GAME_IDS
    generic_protected = gid == "protected_runtime" or gid in EAC_GAME_IDS | BATTLEYE_GAME_IDS
    unknown = bool(gid) and gid not in (PROTECTED_GAME_IDS | KNOWN_MUTABLE_GAME_IDS | {"protected_runtime"})
    protected = riot or valve or generic_protected or unknown
    objective = boost_objective(requested)

    provider = "Riot Vanguard" if riot else "Valve VAC / Trusted Mode" if valve else "EAC / BattlEye" if generic_protected else "Unknown Game Safe" if unknown else None
    mode = "riot_safe" if riot else "valve_safe" if valve else "protected_safe" if generic_protected else "unknown_safe" if unknown else None

    blocked = [
        "process_memory_access",
        "process_code_injection",
        "dll_injection",
        "graphics_hooks",
        "input_automation",
        "game_socket_inspection",
        "packet_interception_or_modification",
        "game_file_modification",
        "anti_cheat_service_or_driver_manipulation",
        "endpoint_firewall_steering",
        "process_priority_changes",
        "cpu_affinity_or_cpu_sets",
        "dns_mutation_during_game",
        "mtu_mutation_during_game",
        "tcp_registry_tweaks",
        "standby_list_purge",
        "service_pausing",
        "network_reset",
        "powershell_execution_during_protected_session",
        "arbitrary_game_endpoint_probing_during_game",
    ] if protected else []

    allowed = [
        "read_only_process_name_detection",
        "read_only_system_telemetry",
        "crash_safe_rollback",
        "local_session_history",
    ] if protected else []
    if protected and objective in {"ping", "complete"}:
        allowed.extend([
            "network_quality_sampling_to_neutral_reference_targets",
            "read_only_route_diagnostics_to_neutral_reference_targets",
            "dns_benchmark_without_live_resolver_change",
            "read_only_pmtu_recommendation",
        ])
    if protected and objective in {"pc", "complete"}:
        allowed.append("temporary_system_power_plan")

    return {
        "active": protected,
        "provider": provider,
        "mode": mode,
        "game_id": gid or None,
        "requested_profile": requested.value,
        "objective_mode": objective,
        "effective_profile": effective.value,
        "policy_version": POLICY_VERSION,
        "policy_reviewed_at": POLICY_REVIEWED_AT,
        "official_policy_sources": list(OFFICIAL_POLICY_SOURCES) if protected else [],
        "lockdown": "maximum_compatibility" if protected else "standard",
        "capabilities": PROTECTED_CAPABILITIES.to_dict() if protected else None,
        "vanguard_processes_detected": vanguard_processes() if riot else [],
        "trusted_mode_note": (
            "NexuFlow keeps CS2 Trusted Mode intact, does not inject into CS2, and does not require -allow_third_party_software."
            if valve else None
        ),
        "riot_note": (
            "NexuFlow does not read Riot game memory, intercept/redirect Riot communications, automate gameplay, or manipulate Vanguard."
            if riot else None
        ),
        "guarantee": (
            "risk-minimized compatibility design; only Riot/Valve can determine enforcement, so no third-party app can guarantee zero ban risk"
            if protected else None
        ),
        "blocked_features": blocked,
        "allowed_features": allowed,
    }
