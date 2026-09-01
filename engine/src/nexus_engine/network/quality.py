from __future__ import annotations

import json
import math
import os
import statistics
import tempfile
import threading
import time
from pathlib import Path

from .icmp import icmp_echo_ipv4

QUALITY_TARGETS = ("1.1.1.1", "8.8.8.8", "9.9.9.9")
_STORE_LOCK = threading.RLock()


def _local_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()))
    else:
        base = Path(tempfile.gettempdir())
    return base / "NexuFlow" / "quality"


def nexus_score(latency_ms: float | None, jitter_ms: float | None, loss_percent: float | None) -> int:
    """Return a transparent 0-100 connection-quality score.

    Packet loss is deliberately the strongest penalty, followed by jitter and
    then latency. This makes a low-ping but lossy route score worse than a
    slightly slower stable route.
    """
    if latency_ms is None:
        return 0
    jitter = max(0.0, float(jitter_ms or 0.0))
    loss = max(0.0, float(loss_percent or 0.0))
    latency = max(0.0, float(latency_ms))

    loss_penalty = min(60.0, loss * 7.0)
    jitter_penalty = min(25.0, jitter * 1.25)
    latency_penalty = 0.0 if latency <= 30.0 else min(25.0, (latency - 30.0) * 0.22)
    return int(round(max(0.0, min(100.0, 100.0 - loss_penalty - jitter_penalty - latency_penalty))))


def quality_grade(score: int) -> str:
    if score >= 92:
        return "Excelente"
    if score >= 80:
        return "Boa"
    if score >= 65:
        return "Instável"
    if score >= 45:
        return "Ruim"
    return "Crítica"


def summarize_samples(samples: list[dict], *, target: str | None = None) -> dict:
    if not samples:
        return {
            "target": target,
            "sample_count": 0,
            "span_seconds": 0.0,
            "latency_ms": None,
            "jitter_ms": None,
            "packet_loss_percent": 100.0,
            "nexus_score": 0,
            "grade": "Crítica",
            "complete_window": False,
        }

    times = [float(s.get("timestamp", 0.0)) for s in samples]
    successful = [float(s["latency_ms"]) for s in samples if s.get("latency_ms") is not None]
    loss = (1.0 - (len(successful) / len(samples))) * 100.0
    latency = float(statistics.median(successful)) if successful else None
    if len(successful) >= 2:
        # Mean absolute inter-sample variation is easier to explain to users
        # than raw standard deviation and tracks the "spiky" feeling well.
        jitter = statistics.fmean(abs(b - a) for a, b in zip(successful, successful[1:]))
    else:
        jitter = 0.0 if successful else None
    score = nexus_score(latency, jitter, loss)
    span = max(times) - min(times) if len(times) >= 2 else 0.0
    return {
        "target": target or samples[-1].get("target"),
        "sample_count": len(samples),
        "span_seconds": round(max(0.0, span), 1),
        "latency_ms": None if latency is None else round(latency, 2),
        "jitter_ms": None if jitter is None else round(float(jitter), 2),
        "packet_loss_percent": round(loss, 2),
        "nexus_score": score,
        "grade": quality_grade(score),
        "complete_window": span >= 18.0 and len(samples) >= 15,
    }


def quality_delta(before: dict | None, after: dict | None) -> dict | None:
    if not before or not after:
        return None

    def diff(key: str):
        a, b = before.get(key), after.get(key)
        if a is None or b is None:
            return None
        return round(float(b) - float(a), 2)

    return {
        "latency_ms": diff("latency_ms"),
        "jitter_ms": diff("jitter_ms"),
        "packet_loss_percent": diff("packet_loss_percent"),
        "nexus_score": diff("nexus_score"),
    }


class QualityStore:
    def __init__(self, path: Path | None = None, max_samples: int = 240) -> None:
        self.path = path or (_local_data_dir() / "rolling.json")
        self.max_samples = max(60, int(max_samples))

    def _load_unlocked(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"samples": []}
        except (OSError, json.JSONDecodeError):
            return {"samples": []}

    def load(self) -> dict:
        with _STORE_LOCK:
            return self._load_unlocked()

    def append(self, sample: dict) -> None:
        with _STORE_LOCK:
            data = self._load_unlocked()
            samples = list(data.get("samples") or [])
            samples.append(sample)
            samples = samples[-self.max_samples :]
            payload = {
                "schema": 1,
                "updated_at": time.time(),
                "writer_pid": os.getpid(),
                "target": sample.get("target"),
                "samples": samples,
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            tmp.replace(self.path)

    def snapshot(self, window_seconds: float = 30.0, *, end_ts: float | None = None) -> dict:
        data = self.load()
        samples = list(data.get("samples") or [])
        end = float(end_ts if end_ts is not None else time.time())
        start = end - max(1.0, float(window_seconds))
        window = [s for s in samples if start <= float(s.get("timestamp", 0.0)) <= end]

        # Never mix two probe targets in one baseline. A target switch can have
        # a different natural RTT and would otherwise create a fake before/after
        # improvement or regression. Use the newest target present in-window.
        active_target = None
        for sample in reversed(window):
            candidate = sample.get("target")
            if candidate:
                active_target = str(candidate)
                break
        if active_target:
            window = [s for s in window if str(s.get("target") or "") == active_target]
        return summarize_samples(window, target=active_target or data.get("target"))

    def is_fresh(self, max_age_seconds: float = 5.0) -> bool:
        data = self.load()
        return (time.time() - float(data.get("updated_at", 0.0))) <= max_age_seconds

    def writer_pid(self) -> int | None:
        try:
            value = int(self.load().get("writer_pid", 0))
            return value or None
        except (TypeError, ValueError):
            return None

    def fresh_target(self, max_age_seconds: float = 10.0) -> str | None:
        data = self.load()
        if (time.time() - float(data.get("updated_at", 0.0))) > max_age_seconds:
            return None
        target = str(data.get("target") or "")
        return target if target in QUALITY_TARGETS else None


class NetworkQualityMonitor:
    store: QualityStore
    interval: float = 1.0
    target_refresh_seconds: float = 1800.0

    def __init__(self, store: QualityStore | None = None, interval: float = 1.0) -> None:
        self.store = store or QualityStore()
        self.interval = max(0.5, float(interval))
        # Stable reference target is more important than chasing the lowest RTT
        # during a session. Re-selection occurs only after a long interval or
        # repeated failures.
        self.target_refresh_seconds = 1800.0
        self._target: str | None = None
        self._target_selected_at = 0.0
        self._consecutive_failures = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _candidate_score(samples: list[float | None]) -> float:
        successful = [x for x in samples if x is not None]
        if not successful:
            return math.inf
        loss = 1.0 - len(successful) / len(samples)
        return statistics.median(successful) + loss * 500.0

    def select_target(self, *, reuse_fresh: bool = True) -> str:
        # Observer, FastAPI and privileged daemon can coexist. Reuse a fresh
        # writer's target so all transports measure the same reference path.
        if reuse_fresh:
            shared = self.store.fresh_target(12.0)
            if shared:
                self._target = shared
                self._target_selected_at = time.monotonic()
                return shared

        best_target = QUALITY_TARGETS[0]
        best_score = math.inf
        for target in QUALITY_TARGETS:
            samples = [icmp_echo_ipv4(target, 550, 16, False)[0] for _ in range(3)]
            score = self._candidate_score(samples)
            if score < best_score:
                best_target, best_score = target, score
        self._target = best_target
        self._target_selected_at = time.monotonic()
        self._consecutive_failures = 0
        return best_target

    def tick(self) -> dict:
        if self._target is None:
            self.select_target(reuse_fresh=True)
        elif (
            time.monotonic() - self._target_selected_at >= self.target_refresh_seconds
            and self._consecutive_failures >= 2
        ):
            # Do not switch a healthy measurement target merely because time
            # passed. Baseline comparability wins; refresh only when it is also
            # showing repeated failures.
            self.select_target(reuse_fresh=False)

        target = self._target or QUALITY_TARGETS[0]
        latency, status = icmp_echo_ipv4(target, 700, 16, False)
        if latency is None:
            self._consecutive_failures += 1
        else:
            self._consecutive_failures = 0

        # Five consecutive failures justify finding a new public reference.
        if self._consecutive_failures >= 5:
            self.select_target(reuse_fresh=False)
            target = self._target or target
            latency, status = icmp_echo_ipv4(target, 700, 16, False)
            self._consecutive_failures = 0 if latency is not None else 1

        sample = {
            "timestamp": time.time(),
            "target": target,
            "latency_ms": None if latency is None else round(float(latency), 2),
            "status": status,
        }
        self.store.append(sample)
        return sample

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def loop() -> None:
            while not self._stop.is_set():
                started = time.monotonic()
                try:
                    self.tick()
                except Exception:
                    # Telemetry must never take the app down.
                    pass
                remaining = self.interval - (time.monotonic() - started)
                self._stop.wait(max(0.05, remaining))

        self._thread = threading.Thread(target=loop, name="NexuFlowNetworkQuality", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.5)
        self._thread = None


def current_quality(*, window_seconds: float = 30.0) -> dict:
    store = QualityStore()
    snapshot = store.snapshot(window_seconds)
    if snapshot.get("sample_count", 0) > 0 and store.is_fresh(8.0):
        return snapshot

    # Cold-start fallback: one immediate sample, clearly marked incomplete.
    monitor = NetworkQualityMonitor(store=store)
    try:
        monitor.tick()
    except Exception:
        pass
    return store.snapshot(window_seconds)
