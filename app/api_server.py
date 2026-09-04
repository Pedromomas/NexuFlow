from __future__ import annotations

import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager

from fastapi import Body, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import _bootstrap  # noqa: F401
from app import __version__
from app.modules.dns_benchmark import DNSBenchmarkService
from app.modules.network_flush import NetworkFlushService
from app.modules.process_monitor import ProcessMonitorService
from app.modules.route_selector import RouteSelectorService
from app.modules.tcp_tweaks import TcpTweaksService
from app.schemas import BoostRequest, FlushRequest, ProcessPriorityRequest, RouteApplyRequest, RouteBenchmarkRequest
from app.security import API_TOKEN, require_api_token
from nexus_engine.admin import is_admin
from nexus_engine.anti_cheat import is_protected_game, protected_pid_game, running_protected_games
from nexus_engine.daemon import daemon_is_running, stop_daemon
from nexus_engine.hardware.driver_center import open_windows_driver_updates, scan_driver_updates
from nexus_engine.hardware.pc_center import open_pc_settings
from nexus_engine.network.connection_center import scan_connection, rank_dns
from nexus_engine.network.quality import NetworkQualityMonitor, QUALITY_TARGETS
from nexus_engine.orchestrator import NexusOrchestrator
from nexus_engine.investigator import investigator_snapshot
from nexus_engine.report_signing import sign_report
from nexus_engine.state import pending_manual_state
from nexus_engine.telemetry import (
    anti_cheat_status,
    diagnostics,
    gaming_health_report,
    recovery_status,
    route_diagnostics,
    session_history,
    telemetry,
)


route_selector = RouteSelectorService()
dns_service = DNSBenchmarkService()
tcp_service = TcpTweaksService()
process_monitor = ProcessMonitorService(interval=2.0)
quality_monitor = NetworkQualityMonitor(interval=1.0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    process_monitor.start()
    if os.name == "nt":
        quality_monitor.start()
    try:
        yield
    finally:
        if os.name == "nt":
            quality_monitor.stop()
        process_monitor.stop()


app = FastAPI(
    title="NexuFlow Local API",
    version=__version__,
    description="Loopback-only control plane for the NexuFlow Windows optimizer.",
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8100",
        "http://127.0.0.1:8100",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-NexuFlow-Token"],
)


def _require_windows_admin() -> None:
    if os.name != "nt":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="System mutations require Windows.")
    if not is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The NexuFlow API must be started elevated for system mutations. Use scripts/run-api.ps1.",
        )


def _engine_python() -> list[str]:
    return [sys.executable, "-m", "nexus_engine"]


def _start_detached_daemon(profile: str) -> dict:
    if daemon_is_running():
        return {"ok": True, "action": "start", "message": "NexuFlow já está ativo.", "data": {"already_running": True}}

    pending = pending_manual_state()
    if pending:
        raise RuntimeError("Restore manual changes before BOOST: " + ", ".join(pending))

    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )

    subprocess.Popen([*_engine_python(), "--daemon-profile", profile], **kwargs)
    deadline = time.time() + 18.0
    while time.time() < deadline:
        if daemon_is_running():
            return {"ok": True, "action": "start", "message": "NexuFlow ativado e monitorando jogos.", "data": {"already_running": False}}
        time.sleep(0.2)
    raise RuntimeError("The privileged daemon did not become ready in time.")


def _ensure_manual_mutation_allowed() -> None:
    if daemon_is_running():
        raise HTTPException(status_code=409, detail="Stop the active BOOST session before using manual mutation endpoints.")


def _block_manual_mutation_during_protected_game(action: str) -> None:
    games = running_protected_games()
    if games:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{action} is disabled while an anti-cheat protected game is running ({', '.join(games)}). "
                "Use the automatic Riot/Valve Safe profile instead."
            ),
        )


@app.get("/api/v1/health")
def health() -> dict:
    return {
        "ok": True,
        "name": "NexuFlow",
        "api": __version__,
        "admin": is_admin(),
        "daemon_active": daemon_is_running(),
        "mutation_auth": "X-NexuFlow-Token",
    }


@app.get("/api/v1/telemetry")
def get_telemetry() -> dict:
    return telemetry()


@app.get("/api/v1/games")
def get_games() -> list[dict]:
    return process_monitor.cached_games()


@app.get("/api/v1/diagnostics")
def get_diagnostics() -> dict:
    return diagnostics()


@app.get("/api/v1/gaming-health")
def get_gaming_health() -> dict:
    return gaming_health_report()


@app.get("/api/v1/drivers/scan")
def get_driver_scan() -> dict:
    return scan_driver_updates()


@app.get("/api/v1/connection/scan")
def get_connection_scan() -> dict:
    try:
        return scan_connection()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/v1/connection/dns-ranking")
def get_dns_ranking() -> dict:
    try:
        return rank_dns()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/v1/pc/settings/{section}", dependencies=[Depends(require_api_token)])
def post_pc_settings(section: str) -> dict:
    try:
        return open_pc_settings(section)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/drivers/open-updates", dependencies=[Depends(require_api_token)])
def post_open_driver_updates() -> dict:
    try:
        return open_windows_driver_updates()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/history")
def get_history(limit: int = Query(default=30, ge=1, le=200)) -> list[dict]:
    return session_history(limit)


@app.get("/api/v1/investigator")
def get_investigator(limit: int = Query(default=100, ge=1, le=200)) -> dict:
    return investigator_snapshot(limit)


@app.post("/api/v1/reports/sign", dependencies=[Depends(require_api_token)])
def post_sign_report(payload: dict = Body(...)) -> dict:
    try:
        return sign_report(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/recovery")
def get_recovery() -> dict:
    return recovery_status()


@app.get("/api/v1/anti-cheat")
def get_anti_cheat(game_id: str | None = Query(default=None, max_length=64)) -> dict:
    return anti_cheat_status(game_id)


@app.get("/api/v1/route-diagnostics")
def get_route_diagnostics(target: str = Query(default="1.1.1.1", max_length=64)) -> dict:
    protected = running_protected_games()
    if protected and target not in QUALITY_TARGETS:
        raise HTTPException(
            status_code=409,
            detail="Protected-game compatibility mode only permits route diagnostics to neutral NexuFlow reference targets.",
        )
    try:
        return route_diagnostics(target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/dns/benchmark")
async def dns_benchmark() -> dict:
    return await dns_service.benchmark()


@app.post("/api/v1/dns/apply-best", dependencies=[Depends(require_api_token)])
def dns_apply_best() -> dict:
    _require_windows_admin()
    _ensure_manual_mutation_allowed()
    _block_manual_mutation_during_protected_game("Manual DNS mutation")
    try:
        return dns_service.apply_best()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/dns/restore", dependencies=[Depends(require_api_token)])
def dns_restore() -> dict:
    _require_windows_admin()
    return dns_service.restore()


@app.post("/api/v1/tcp/apply", dependencies=[Depends(require_api_token)])
def tcp_apply() -> dict:
    _require_windows_admin()
    _ensure_manual_mutation_allowed()
    _block_manual_mutation_during_protected_game("TCP registry tweaks")
    try:
        return tcp_service.apply()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/tcp/revert", dependencies=[Depends(require_api_token)])
def tcp_revert() -> dict:
    _require_windows_admin()
    return tcp_service.revert()


@app.post("/api/v1/boost/start", dependencies=[Depends(require_api_token)])
def boost_start(payload: BoostRequest) -> dict:
    _require_windows_admin()
    try:
        return _start_detached_daemon(payload.profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/boost/stop", dependencies=[Depends(require_api_token)])
def boost_stop() -> dict:
    _require_windows_admin()
    return {"ok": True, "action": "stop", "message": "NexuFlow desativado.", "data": stop_daemon()}


@app.post("/api/v1/restore", dependencies=[Depends(require_api_token)])
def restore_all() -> dict:
    _require_windows_admin()
    daemon_result = stop_daemon()
    route_result = route_selector.restore()
    dns_result = dns_service.restore()
    tcp_result = tcp_service.revert()
    process_result = process_monitor.restore_all()
    core_result = NexusOrchestrator().restore_all()
    return {
        "ok": True,
        "action": "restore",
        "message": "Rollback completo executado.",
        "data": {
            "daemon": daemon_result,
            "route_selector": route_result,
            "dns": dns_result,
            "tcp": tcp_result,
            "process": process_result,
            "core": core_result,
        },
    }


@app.post("/api/v1/routes/benchmark", dependencies=[Depends(require_api_token)])
def route_benchmark(payload: RouteBenchmarkRequest) -> dict:
    protected = running_protected_games()
    if protected:
        raise HTTPException(
            status_code=409,
            detail="Arbitrary endpoint benchmarks are disabled while Riot/Vanguard or CS2/VAC gameplay is active.",
        )
    return {"results": route_selector.benchmark(payload.ips, payload.attempts)}


@app.post("/api/v1/routes/apply", dependencies=[Depends(require_api_token)])
def route_apply(payload: RouteApplyRequest) -> dict:
    _require_windows_admin()
    _ensure_manual_mutation_allowed()
    if is_protected_game(payload.game_id):
        raise HTTPException(status_code=409, detail="Firewall endpoint steering is disabled for Riot/Vanguard and CS2/VAC profiles.")
    _block_manual_mutation_during_protected_game("Endpoint firewall steering")
    try:
        return route_selector.apply_best(**payload.model_dump())
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/routes/restore", dependencies=[Depends(require_api_token)])
def route_restore() -> dict:
    _require_windows_admin()
    return route_selector.restore()


@app.post("/api/v1/process/priority", dependencies=[Depends(require_api_token)])
def process_priority(payload: ProcessPriorityRequest) -> dict:
    _require_windows_admin()
    _ensure_manual_mutation_allowed()
    protected_game = protected_pid_game(payload.pid)
    if protected_game:
        raise HTTPException(status_code=409, detail=f"Manual process manipulation is disabled for protected game: {protected_game}.")
    _block_manual_mutation_during_protected_game("Manual process priority changes")
    try:
        snapshot = process_monitor.set_priority(payload.pid, payload.aggressive)
        return {"ok": True, "snapshot": snapshot}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/network/flush", dependencies=[Depends(require_api_token)])
def network_flush(payload: FlushRequest) -> dict:
    _require_windows_admin()
    _ensure_manual_mutation_allowed()
    _block_manual_mutation_during_protected_game("Network reset")
    try:
        return NetworkFlushService().execute(
            confirm_disconnect=payload.confirm_disconnect,
            include_ip_reset=payload.include_ip_reset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    print(f"NexuFlow API token: {API_TOKEN}")
    uvicorn.run("app.api_server:app", host="127.0.0.1", port=8000, reload=False)
