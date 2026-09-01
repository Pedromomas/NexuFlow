from __future__ import annotations

import json
import os
import time
from typing import Callable

import psutil

from .anti_cheat import is_protected_game, running_protected_games
from .catalog import GameCatalog
from .discovery import discover_games, first_running_game
from .models import BoostProfile
from .network.quality import NetworkQualityMonitor, QualityStore
from .orchestrator import NexusOrchestrator
from .state import StateStore, daemon_file, pending_manual_state, stop_file


def _write_daemon(data: dict) -> None:
    path = daemon_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def daemon_is_running() -> bool:
    path = daemon_file()
    if not path.exists():
        return False
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
        pid = int(meta.get("pid", 0))
        expected_started = float(meta.get("process_create_time", 0.0))
        if not pid or not psutil.pid_exists(pid):
            return False
        proc = psutil.Process(pid)
        if expected_started and abs(proc.create_time() - expected_started) > 1.0:
            return False
        name = proc.name().lower()
        return name.startswith("nexus-engine") or "python" in name
    except (OSError, ValueError, json.JSONDecodeError, psutil.Error):
        return False


def request_stop() -> None:
    path = stop_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(time.time()), encoding="utf-8")


def run_daemon(profile: BoostProfile, ready: Callable[[dict], None]) -> None:
    if daemon_is_running():
        ready({"ok": True, "action": "start", "message": "NexuFlow já está ativo.", "data": {"already_running": True}})
        return

    pending = pending_manual_state()
    if pending:
        ready({
            "ok": False,
            "action": "start",
            "message": "Restaure as alterações manuais antes de iniciar o BOOST.",
            "data": {"pending_manual_state": pending},
        })
        return

    sf = stop_file()
    try:
        sf.unlink(missing_ok=True)
    except OSError:
        pass

    catalog = GameCatalog.load()
    engine = NexusOrchestrator()
    quality_store = QualityStore()
    quality_monitor = NetworkQualityMonitor(store=quality_store, interval=1.0)
    quality_monitor_started = False

    # In Tauri/FastAPI modes an unprivileged observer may already be writing
    # quality samples. Avoid a second writer while that source is healthy. If
    # the UI/API disappears, the privileged daemon takes over automatically.
    if not quality_store.is_fresh(3.0):
        quality_monitor.start()
        quality_monitor_started = True

    # Strong crash recovery: if an active snapshot exists but its previous
    # daemon is gone, the new elevated daemon restores that state before it
    # touches the next game.
    interrupted_restore = None
    try:
        stale = engine.state_store.load()
        if stale.get("active"):
            interrupted_restore = engine.restore_all()
    except Exception as exc:
        interrupted_restore = {"restored": False, "errors": [str(exc)]}

    boosted: dict | None = None
    post_capture_due: float | None = None
    last_adaptive_check = 0.0
    last_adaptive_event = 0.0
    degraded_checks = 0

    status = {
        "pid": os.getpid(),
        "process_create_time": psutil.Process(os.getpid()).create_time(),
        "profile": profile.value,
        "started_at": time.time(),
        "boosted_game": None,
        "effective_profile": None,
        "last_error": None,
        "last_adaptive_event": None,
        "interrupted_restore": interrupted_restore,
    }
    _write_daemon(status)

    running = first_running_game(catalog)
    initial_report = None
    if running:
        try:
            initial_report = engine.optimize_game(running, profile)
            boosted = {
                "id": running["id"],
                "pid": running["pid"],
                "protected": bool((initial_report.get("anti_cheat") or {}).get("active")),
            }
            status["boosted_game"] = running["display_name"]
            status["effective_profile"] = initial_report.get("profile")
            post_capture_due = time.time() + 25.0
            _write_daemon(status)
        except Exception as exc:
            status["last_error"] = str(exc)
            _write_daemon(status)

    ready({
        "ok": True,
        "action": "start",
        "message": (
            f"{running['display_name']} otimizado. NexuFlow monitorando qualidade em tempo real."
            if boosted
            else "NexuFlow armado. O próximo jogo suportado será otimizado automaticamente."
        ),
        "data": {
            "pid": os.getpid(),
            "boosted_game": status["boosted_game"],
            "effective_profile": status["effective_profile"],
            "interrupted_restore": interrupted_restore,
            "report": initial_report,
        },
        "warnings": (
            (initial_report or {}).get("warnings", [])
            if initial_report
            else ([status["last_error"]] if status["last_error"] else [])
        ),
    })

    try:
        while not sf.exists():
            # Seamless telemetry ownership: if the observer/API writer stops,
            # continue quality sampling inside the daemon.
            if not quality_monitor_started and not quality_store.is_fresh(3.5):
                quality_monitor.start()
                quality_monitor_started = True

            games = discover_games(catalog)
            now = time.time()
            protected_current = next(
                (g for g in games if g.get("running") and is_protected_game(g.get("id"))),
                None,
            )
            protected_runtime_active = bool(running_protected_games())

            # If a protected title starts while a non-protected BOOST session is
            # already active, restore that session immediately before doing
            # anything else. The next branch then starts the protected title in
            # Riot/Valve Safe mode. This prevents old aggressive settings from
            # silently carrying into a newly launched protected game.
            if boosted and (protected_current or protected_runtime_active) and not boosted.get("protected", False):
                try:
                    engine.restore_all()
                    status["last_error"] = None
                except Exception as exc:
                    status["last_error"] = f"protected-transition rollback: {exc}"
                boosted = None
                post_capture_due = None
                degraded_checks = 0
                status["boosted_game"] = None
                status["effective_profile"] = None
                status["protected_takeover"] = protected_current.get("display_name") if protected_current else "EAC / BattlEye runtime"
                _write_daemon(status)

            if boosted:
                current = next(
                    (
                        g
                        for g in games
                        if g["id"] == boosted["id"]
                        and g["running"]
                        and int(g.get("pid") or 0) == int(boosted["pid"])
                    ),
                    None,
                )
                if current is None:
                    try:
                        engine.restore_all()
                    except Exception as exc:
                        status["last_error"] = f"rollback: {exc}"
                    boosted = None
                    post_capture_due = None
                    degraded_checks = 0
                    status["boosted_game"] = None
                    status["effective_profile"] = None
                    _write_daemon(status)

            if boosted is None:
                # A generic EAC/BattlEye service/process signal is enough to
                # enter lockdown, but it is not enough to guess which ordinary
                # catalog process is the protected game. Keep observing without
                # applying a Roblox/legacy profile to the wrong process.
                if protected_runtime_active and protected_current is None:
                    status["boosted_game"] = None
                    status["effective_profile"] = BoostProfile.PROTECTED_SAFE.value
                    status["protected_takeover"] = "EAC / BattlEye runtime"
                    status["last_error"] = None
                    _write_daemon(status)
                    time.sleep(1.25)
                    continue

                current = protected_current or next((g for g in games if g["running"]), None)
                if current:
                    try:
                        report = engine.optimize_game(current, profile)
                        boosted = {
                            "id": current["id"],
                            "pid": current["pid"],
                            "protected": bool((report.get("anti_cheat") or {}).get("active")),
                        }
                        status["boosted_game"] = current["display_name"]
                        status["effective_profile"] = report.get("profile")
                        status["last_error"] = None
                        post_capture_due = now + 25.0
                        degraded_checks = 0
                    except Exception as exc:
                        status["last_error"] = str(exc)
                    _write_daemon(status)

            if boosted and post_capture_due and now >= post_capture_due:
                try:
                    engine.capture_quality_after()
                except Exception as exc:
                    status["last_error"] = f"after-baseline: {exc}"
                post_capture_due = None
                _write_daemon(status)

            # Adaptive Booster: detect sustained degradation, then recalculate
            # DNS/endpoint/route diagnostics without touching the live game.
            if boosted and now - last_adaptive_check >= 5.0:
                last_adaptive_check = now
                try:
                    state = engine.state_store.load()
                    before = state.get("quality_after") or state.get("quality_before") or {}
                    current_quality = quality_store.snapshot(20.0)
                    base_score = int(before.get("nexus_score") or 0)
                    current_score = int(current_quality.get("nexus_score") or 0)
                    loss = float(current_quality.get("packet_loss_percent") or 0.0)
                    jitter = float(current_quality.get("jitter_ms") or 0.0)
                    degraded = (
                        (base_score >= 60 and current_score <= base_score - 18)
                        or loss >= 2.0
                        or jitter >= 12.0
                    )
                    degraded_checks = degraded_checks + 1 if degraded else 0
                    if degraded_checks >= 2 and now - last_adaptive_event >= 90.0:
                        event = engine.adaptive_reassess()
                        last_adaptive_event = now
                        degraded_checks = 0
                        status["last_adaptive_event"] = event.get("timestamp") if event else now
                        _write_daemon(status)
                except Exception as exc:
                    status["last_error"] = f"adaptive: {exc}"
                    _write_daemon(status)

            time.sleep(1.25)
    finally:
        try:
            engine.restore_all()
        except Exception:
            pass
        quality_monitor.stop()
        try:
            daemon_file().unlink(missing_ok=True)
        except OSError:
            pass
        try:
            sf.unlink(missing_ok=True)
        except OSError:
            pass


def stop_daemon_unprivileged(wait_seconds: float = 14.0) -> dict:
    """Ask the already-elevated daemon to restore and exit.

    This path never applies a privileged mutation itself, so it is safe to
    invoke from the medium-integrity Tauri host without another UAC prompt.
    The elevated daemon owns the rollback in its finally block.
    """
    if not daemon_is_running():
        state = StateStore().load()
        return {
            "stopped": True,
            "restore_pending": bool(state.get("active")),
            "message": "NexuFlow já estava inativo." if not state.get("active") else "Snapshot pendente requer rollback elevado.",
        }

    request_stop()
    deadline = time.time() + wait_seconds
    while daemon_is_running() and time.time() < deadline:
        time.sleep(0.2)

    state = StateStore().load()
    pending = bool(state.get("active"))
    return {
        "stopped": not daemon_is_running(),
        "restore_pending": pending,
        "message": (
            "NexuFlow desligado e alterações restauradas."
            if not daemon_is_running() and not pending
            else "Rollback não terminou; use Restaurar tudo."
        ),
    }


def stop_daemon(wait_seconds: float = 12.0) -> dict:
    request_stop()
    deadline = time.time() + wait_seconds
    while daemon_is_running() and time.time() < deadline:
        time.sleep(0.2)
    restore = NexusOrchestrator().restore_all()
    return {"stopped": not daemon_is_running(), "restore": restore}
