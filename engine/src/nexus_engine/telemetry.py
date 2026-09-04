from __future__ import annotations

import os
import time

import psutil

from .admin import is_admin
from .anti_cheat import anti_cheat_policy_report, effective_profile, running_protected_games
from .catalog import GameCatalog
from .daemon import daemon_is_running
from .diagnostics.stutter_health import stutter_health_snapshot
from .discovery import discover_games, first_running_game
from .hardware.health import gaming_health
from .hardware.nvidia import nvidia_telemetry
from .hardware.session_guard import session_guard_report
from .hardware.windows_gaming import windows_gaming_report
from .history import SessionHistory
from .investigator import record_event
from .latency_budget import classify_latency_budget
from .models import BoostProfile
from .network.dns import DNSManager
from .network.interfaces import InterfaceManager
from .network.nic_health import nic_health_report
from .network.quality import QUALITY_TARGETS, current_quality, quality_delta
from .network.connection_center import connection_history
from .network.route_diagnostics import trace_route
from .state import StateStore
from .policy_runtime import policy_status


def recovery_status() -> dict:
    state = StateStore().load()
    active = bool(state.get("active"))
    daemon = daemon_is_running()
    return {
        "required": active and not daemon,
        "snapshot_active": active,
        "daemon_active": daemon,
        "session_id": state.get("session_id"),
        "game": state.get("game"),
        "started_at": state.get("started_at"),
        "restore_errors": state.get("restore_errors", []),
    }


def telemetry() -> dict:
    cpu = psutil.cpu_percent(interval=0.05)
    mem = psutil.virtual_memory()
    quality = current_quality(window_seconds=30.0)
    game = first_running_game()
    gpu = nvidia_telemetry()
    daemon = daemon_is_running()
    state = StateStore().load()
    session_quality = None
    if state.get("active"):
        before = state.get("quality_before")
        after = state.get("quality_after")
        session_quality = {
            "before": before,
            "after": after,
            "delta": quality_delta(before, after),
            "adaptive_events": len(state.get("adaptive_events") or []),
        }

    budget_health = {
        "cpu": {"utilization_percent": round(cpu, 1)},
        "memory": {
            "percent": round(mem.percent, 1),
            "available_gb": round(mem.available / (1024 ** 3), 2),
        },
        "gpu": gpu,
    }
    latency_budget = classify_latency_budget(quality=quality, gaming_health=budget_health)

    return {
        "timestamp": int(time.time() * 1000),
        "engine_online": True,
        "cpu_percent": round(cpu, 1),
        "memory_percent": round(mem.percent, 1),
        "memory_used_gb": round((mem.total - mem.available) / (1024 ** 3), 2),
        "memory_total_gb": round(mem.total / (1024 ** 3), 2),
        "ping_ms": quality.get("latency_ms"),
        "jitter_ms": quality.get("jitter_ms"),
        "packet_loss_percent": quality.get("packet_loss_percent"),
        "nexus_score": quality.get("nexus_score"),
        "quality_grade": quality.get("grade"),
        "quality_target": quality.get("target"),
        "connection_history": connection_history(),
        "quality_window_seconds": quality.get("span_seconds"),
        "network_status": "Online" if quality.get("latency_ms") is not None else "Degraded",
        "active_game": game["display_name"] if game else None,
        "active_game_id": game["id"] if game else None,
        "gpu_name": gpu.get("name"),
        "gpu_utilization": gpu.get("utilization"),
        "gpu_temperature_c": gpu.get("temperature_c"),
        "daemon_active": daemon,
        "effective_profile": state.get("profile") if state.get("active") else None,
        "objective_mode": state.get("objective_mode") if state.get("active") else None,
        "anti_cheat": state.get("anti_cheat") if state.get("active") else None,
        "session_quality": session_quality,
        "latency_budget": latency_budget,
        "recovery_required": bool(state.get("active")) and not daemon,
    }


def diagnostics() -> dict:
    games = discover_games(GameCatalog.load())
    result = {
        "platform": os.name,
        "admin": is_admin(),
        "games": games,
        "daemon_active": daemon_is_running(),
        "gpu": nvidia_telemetry(),
        "quality": current_quality(),
        "recovery": recovery_status(),
    }
    protected = running_protected_games()
    if protected:
        result["interface"] = {
            "deferred": True,
            "reason": "Protected-game compatibility mode blocks every PowerShell/pwsh launch while gameplay is active",
            "protected_games": protected,
        }
        result["dns"] = {"deferred": True, "current_resolver_queried": False}
    else:
        try:
            iface = InterfaceManager.primary_ipv4()
            result["interface"] = {
                "index": iface.index,
                "alias": iface.alias,
                "description": iface.description,
                "gateway": iface.next_hop,
                "link_speed": iface.link_speed,
                "mtu": iface.mtu,
                "category": iface.network_category,
                "virtual": iface.probably_virtual,
            }
            if os.name == "nt":
                result["dns"] = DNSManager.snapshot(iface.index, iface.guid)
        except Exception as exc:
            result["interface_error"] = str(exc)
    return result


def anti_cheat_status(game_id: str | None = None) -> dict:
    if game_id is None:
        running = first_running_game()
        game_id = running.get("id") if running else None
    requested = BoostProfile.AUTO
    effective = effective_profile(requested, game_id)
    return anti_cheat_policy_report(game_id, requested, effective)


def session_history(limit: int = 30) -> list[dict]:
    return SessionHistory().list(limit)


def gaming_health_report() -> dict:
    protected = bool(running_protected_games())
    health = gaming_health(protected_runtime=protected)
    stutter = stutter_health_snapshot()
    health["nic_health"] = nic_health_report(protected=protected)
    health["windows_gaming"] = windows_gaming_report()
    health["stutter_health"] = stutter
    health["session_guard"] = session_guard_report()
    health["policy"] = policy_status()
    health["latency_budget"] = classify_latency_budget(
        quality=current_quality(window_seconds=30.0),
        gaming_health=health,
    )
    return health


def route_diagnostics(target: str = "1.1.1.1") -> dict:
    protected = running_protected_games()
    if protected and target not in QUALITY_TARGETS:
        raise ValueError(
            "Protected-game compatibility mode permits route diagnostics only to neutral NexuFlow reference targets"
        )
    result = trace_route(target)
    record_event(
        "rede",
        "diagnóstico de rota",
        target,
        details="Sondas somente leitura; nenhuma rota foi alterada.",
    )
    return result
