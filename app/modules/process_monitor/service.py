from __future__ import annotations

import json
import threading
from collections.abc import Callable

from app import _bootstrap  # noqa: F401
from nexus_engine.catalog import GameCatalog
from nexus_engine.anti_cheat import protected_pid_game
from nexus_engine.discovery import discover_games
from nexus_engine.hardware.process import ProcessOptimizer
from nexus_engine.state import program_data_dir


class ProcessMonitorService:
    """Low-frequency process observer for the REST control plane.

    The privileged BOOST daemon owns automatic optimization. This service keeps
    game discovery warm for the Ionic/FastAPI UI and owns explicit manual
    process-priority snapshots so those changes can be rolled back exactly.
    """

    def __init__(self, interval: float = 2.0) -> None:
        self.interval = max(0.5, float(interval))
        self.catalog = GameCatalog.load()
        self.state_path = program_data_dir() / "state" / "manual-process.json"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._last_scan: list[dict] = []

    def _scan_now(self) -> list[dict]:
        games = discover_games(self.catalog)
        with self._lock:
            self._last_scan = [dict(game) for game in games]
        return games

    def scan(self) -> list[dict]:
        return self._scan_now()

    def cached_games(self) -> list[dict]:
        with self._lock:
            cached = [dict(game) for game in self._last_scan]
        return cached or self._scan_now()

    def set_priority(self, pid: int, aggressive: bool = False) -> dict:
        protected = protected_pid_game(pid)
        if protected:
            raise RuntimeError(f"Manual process optimization is disabled for anti-cheat protected game: {protected}")
        snapshots = self._load()
        if any(int(item.get("pid", 0)) == int(pid) for item in snapshots):
            raise RuntimeError("This PID is already tracked by the manual process optimizer")

        snapshot = ProcessOptimizer.snapshot(pid)
        snapshots.append(snapshot)
        self._save(snapshots)  # checkpoint before mutation
        try:
            applied = ProcessOptimizer.apply(snapshot, aggressive=aggressive)
            snapshots[-1] = applied
            self._save(snapshots)
            return applied
        except Exception:
            # If the mutation failed after a partial OS change, keep the
            # checkpoint instead of discarding the only rollback information.
            self._save(snapshots)
            raise

    def restore_pid(self, pid: int) -> dict:
        snapshots = self._load()
        keep: list[dict] = []
        restored = 0
        for snapshot in snapshots:
            if int(snapshot.get("pid", 0)) == int(pid):
                ProcessOptimizer.restore(snapshot)
                restored += 1
            else:
                keep.append(snapshot)
        self._save(keep)
        return {"restored": bool(restored), "count": restored}

    def restore_all(self) -> dict:
        snapshots = self._load()
        errors: list[str] = []
        keep: list[dict] = []
        restored = 0
        for snapshot in snapshots:
            try:
                ProcessOptimizer.restore(snapshot)
                restored += 1
            except Exception as exc:  # preserve failed snapshots for retry
                errors.append(str(exc))
                keep.append(snapshot)
        self._save(keep)
        return {"restored": not errors, "count": restored, "errors": errors}

    def start(self, on_game: Callable[[dict], None] | None = None) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._scan_now()

        def loop() -> None:
            while not self._stop.wait(self.interval):
                games = self._scan_now()
                if on_game:
                    for game in games:
                        if game.get("running"):
                            on_game(dict(game))

        self._thread = threading.Thread(target=loop, name="NexuFlowProcessMonitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None

    def _load(self) -> list[dict]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, data: list[dict]) -> None:
        if not data:
            self.state_path.unlink(missing_ok=True)
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)
