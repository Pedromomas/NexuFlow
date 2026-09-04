from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from nexus_engine.admin import ElevationError, is_admin, relaunch_elevated
from nexus_engine import __version__
from nexus_engine.hardware.driver_center import open_windows_driver_updates, scan_driver_updates
from nexus_engine.hardware.pc_center import PC_SETTINGS, open_pc_settings
from nexus_engine.network.connection_center import scan_connection, rank_dns
from nexus_engine.network.speed_test import run_speed_test
from nexus_engine.catalog import GameCatalog
from nexus_engine.daemon import run_daemon, stop_daemon, stop_daemon_unprivileged
from nexus_engine.discovery import discover_games
from nexus_engine.models import BoostProfile
from nexus_engine.observer import run_observer, run_observer_file
from nexus_engine.telemetry import (
    anti_cheat_status,
    diagnostics,
    gaming_health_report,
    recovery_status,
    route_diagnostics,
    session_history,
    telemetry,
)
from nexus_engine.preflight import preflight_report
from nexus_engine.investigator import investigator_snapshot
from nexus_engine.report_signing import sign_report, verify_report


PUBLIC_PROFILE_VALUES = ("ping", "pc", "complete", "hardcore_safe")


def _atomic_json(path: Path, value) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)


def emit(value, output_file: Path | None = None) -> None:
    """Emit JSON to stdout in development or to a file in packaged mode.

    The production PyInstaller helper is built with --windowed so Windows does
    not create a console window. Tauri therefore supplies --output-file for
    request/response commands. Keeping stdout support preserves CLI/dev usage.
    """
    if output_file is not None:
        _atomic_json(output_file, value)
        return
    stream = getattr(sys, "stdout", None)
    if stream is not None:
        print(json.dumps(value, ensure_ascii=False, separators=(",", ":")), flush=True)


def _job_root() -> Path:
    return (Path(tempfile.gettempdir()) / "NexuFlow" / "jobs").resolve()


def _validate_job_paths(request_path: Path, result_path: Path) -> None:
    expected = _job_root()
    req_parent = request_path.resolve().parent
    res_parent = result_path.resolve().parent
    if req_parent != expected or res_parent != expected:
        raise ValueError("Privileged job files must be inside the NexuFlow temporary job directory")
    if not request_path.name.endswith(".request.json") or not result_path.name.endswith(".result.json"):
        raise ValueError("Invalid privileged job filename")
    req_token = request_path.name.removesuffix(".request.json")
    res_token = result_path.name.removesuffix(".result.json")
    if req_token != res_token or len(req_token) < 20:
        raise ValueError("Privileged request/result token mismatch")


def _write_result(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _handle_job(request_path: Path, result_path: Path) -> None:
    _validate_job_paths(request_path, result_path)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if request.get("schema") != 1 or request.get("requested_by") != "tauri":
        raise ValueError("Rejected malformed privileged request")
    action = str(request.get("action", ""))
    profile_raw = str(request.get("profile", "complete"))
    if action not in {"start", "restore"}:
        raise ValueError("Rejected unsupported privileged action")
    if action == "start" and profile_raw not in PUBLIC_PROFILE_VALUES:
        raise ValueError("Rejected unsupported boost profile")

    if os.name != "nt":
        _write_result(result_path, {"ok": False, "action": action, "message": "NexuFlow system optimization requires Windows 10/11."})
        return

    if not is_admin():
        try:
            relaunch_elevated()
        except ElevationError as exc:
            _write_result(result_path, {"ok": False, "action": action, "message": str(exc)})
            return

    if action == "start":
        run_daemon(BoostProfile(profile_raw), lambda value: _write_result(result_path, value))
        return
    if action == "restore":
        data = stop_daemon()
        _write_result(result_path, {"ok": True, "action": "restore", "message": "Rollback completo executado.", "data": data})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexus-engine")
    parser.add_argument("--telemetry-json", action="store_true")
    parser.add_argument("--discover-json", action="store_true")
    parser.add_argument("--diagnostics-json", action="store_true")
    parser.add_argument("--gaming-health-json", action="store_true")
    parser.add_argument("--driver-scan-json", action="store_true")
    parser.add_argument("--connection-scan-json", action="store_true")
    parser.add_argument("--dns-ranking-json", action="store_true")
    parser.add_argument("--speed-test-json", action="store_true")
    parser.add_argument("--open-pc-settings", choices=tuple(PC_SETTINGS))
    parser.add_argument("--open-driver-updates-json", action="store_true")
    parser.add_argument("--history-json", action="store_true")
    parser.add_argument("--investigator-json", action="store_true")
    parser.add_argument("--sign-report-file", type=Path)
    parser.add_argument("--verify-report-file", type=Path)
    parser.add_argument("--preflight-json", action="store_true")
    parser.add_argument("--recovery-json", action="store_true")
    parser.add_argument("--anti-cheat-json", nargs="?", const="", metavar="GAME_ID")
    parser.add_argument("--route-diagnostics-json", nargs="?", const="1.1.1.1", metavar="IPV4")
    parser.add_argument("--stop-signal-json", action="store_true")
    parser.add_argument("--observer", action="store_true")
    parser.add_argument("--observer-file", type=Path)
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--daemon-profile", choices=PUBLIC_PROFILE_VALUES)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.telemetry_json:
            emit(telemetry(), args.output_file); return
        if args.discover_json:
            emit(discover_games(GameCatalog.load()), args.output_file); return
        if args.diagnostics_json:
            emit(diagnostics(), args.output_file); return
        if args.gaming_health_json:
            emit(gaming_health_report(), args.output_file); return
        if args.driver_scan_json:
            emit(scan_driver_updates(), args.output_file); return
        if args.connection_scan_json:
            emit(scan_connection(), args.output_file); return
        if args.dns_ranking_json:
            emit(rank_dns(), args.output_file); return
        if args.speed_test_json:
            emit(run_speed_test(), args.output_file); return
        if args.open_pc_settings:
            emit(open_pc_settings(args.open_pc_settings), args.output_file); return
        if args.open_driver_updates_json:
            emit(open_windows_driver_updates(), args.output_file); return
        if args.history_json:
            emit(session_history(50), args.output_file); return
        if args.investigator_json:
            emit(investigator_snapshot(100), args.output_file); return
        if args.sign_report_file:
            if args.sign_report_file.stat().st_size > 256 * 1024:
                raise ValueError("Session report exceeds the signing size limit")
            payload = json.loads(args.sign_report_file.read_text(encoding="utf-8"))
            emit(sign_report(payload), args.output_file); return
        if args.verify_report_file:
            if args.verify_report_file.stat().st_size > 512 * 1024:
                raise ValueError("Signed report exceeds the verification size limit")
            envelope = json.loads(args.verify_report_file.read_text(encoding="utf-8"))
            emit({"valid": verify_report(envelope), "algorithm": "Ed25519"}, args.output_file); return
        if args.preflight_json:
            emit(preflight_report(), args.output_file); return
        if args.recovery_json:
            emit(recovery_status(), args.output_file); return
        if args.anti_cheat_json is not None:
            emit(anti_cheat_status(args.anti_cheat_json or None), args.output_file); return
        if args.route_diagnostics_json is not None:
            emit(route_diagnostics(args.route_diagnostics_json), args.output_file); return
        if args.stop_signal_json:
            data = stop_daemon_unprivileged()
            emit({
                "ok": bool(data.get("stopped")) and not bool(data.get("restore_pending")),
                "action": "stop",
                "message": str(data.get("message") or "NexuFlow stop solicitado."),
                "data": data,
            }, args.output_file)
            return
        if args.observer:
            if args.observer_file is not None:
                run_observer_file(args.parent_pid, args.observer_file)
            else:
                stream = getattr(sys, "stdout", None)
                if stream is None:
                    raise RuntimeError("Packaged observer requires --observer-file")
                run_observer(args.parent_pid, stream)
            return
        if args.daemon_profile:
            if os.name != "nt":
                emit({"ok": False, "error": "NexuFlow daemon requires Windows."}, args.output_file); return
            if not is_admin():
                relaunch_elevated()
            run_daemon(BoostProfile(args.daemon_profile), lambda value: emit(value, args.output_file)); return
        if args.request and args.result:
            _handle_job(args.request, args.result); return
        emit({"ok": True, "name": "NexuFlow Engine", "version": __version__, "admin": is_admin()}, args.output_file)
    except Exception as exc:
        if args.result:
            try:
                _write_result(args.result, {"ok": False, "action": "error", "message": str(exc)})
                return
            except Exception:
                pass
        emit({"ok": False, "error": str(exc)}, args.output_file)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
