from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, TextIO

import psutil

from .catalog import GameCatalog
from .daemon import daemon_is_running
from .discovery import discover_games, preferred_running_game
from .hardware.nvidia import nvidia_telemetry
from .latency_budget import classify_latency_budget
from .network.quality import NetworkQualityMonitor, QualityStore, quality_delta
from .network.connection_center import connection_history
from .state import StateStore


def _snapshot(games: list[dict], gpu: dict, quality: dict) -> dict:
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    game = preferred_running_game(games)
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
        "active_game": game.get("display_name") if game else None,
        "active_game_id": game.get("id") if game else None,
        "gpu_name": gpu.get("name"),
        "gpu_utilization": gpu.get("utilization"),
        "gpu_temperature_c": gpu.get("temperature_c"),
        "daemon_active": daemon,
        "effective_profile": state.get("profile") if state.get("active") else None,
        "anti_cheat": state.get("anti_cheat") if state.get("active") else None,
        "session_quality": session_quality,
        "latency_budget": classify_latency_budget(quality=quality, gaming_health=budget_health),
        "recovery_required": bool(state.get("active")) and not daemon,
    }


def _run_observer(parent_pid: int | None, sink: Callable[[dict], None]) -> None:
    """Long-lived unprivileged telemetry observer used by the Tauri host."""
    catalog = GameCatalog.load()
    games: list[dict] = []
    gpu: dict = {"available": False, "name": None, "utilization": None}
    next_games = 0.0
    next_gpu = 0.0
    store = QualityStore()
    quality_monitor = NetworkQualityMonitor(store=store, interval=1.0)

    psutil.cpu_percent(interval=None)

    while True:
        if parent_pid and (parent_pid <= 0 or not psutil.pid_exists(parent_pid)):
            return

        now = time.monotonic()
        if now >= next_games:
            games = discover_games(catalog)
            next_games = now + 3.0
        if now >= next_gpu:
            gpu = nvidia_telemetry()
            next_gpu = now + 8.0

        try:
            quality_monitor.tick()
        except Exception:
            pass
        quality = store.snapshot(30.0)

        sink({
            "kind": "snapshot",
            "telemetry": _snapshot(games, gpu, quality),
            "games": games,
        })
        time.sleep(1.0)


def run_observer(parent_pid: int | None, stream: TextIO) -> None:
    def sink(event: dict) -> None:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()

    _run_observer(parent_pid, sink)


def run_observer_file(parent_pid: int | None, path: Path) -> None:
    """Observer transport for the packaged windowless sidecar.

    PyInstaller --windowed intentionally has no stdout/stderr console streams.
    Tauri therefore reads a small atomic JSON snapshot file instead of keeping
    a console pipe open. This removes the black CMD window without changing
    telemetry behavior.
    """
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    def sink(event: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(event, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(path)

    try:
        _run_observer(parent_pid, sink)
    finally:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
