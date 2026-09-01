from __future__ import annotations

import shutil
import threading
import time

from ..winexec import run_command

_CACHE_LOCK = threading.Lock()
_CACHE_VALUE: dict | None = None
_CACHE_AT = 0.0
_CACHE_SECONDS = 5.0


def _number(value: str) -> float | None:
    cleaned = value.strip()
    if cleaned in {"N/A", "[N/A]", ""}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _read_nvidia() -> dict:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {
            "available": False,
            "name": None,
            "utilization": None,
            "driver_version": None,
            "temperature_c": None,
        }
    try:
        fields = (
            "name,driver_version,utilization.gpu,temperature.gpu,pstate,"
            "power.draw,clocks.current.graphics"
        )
        out = run_command(
            [exe, f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
            timeout=5,
        ).stdout.strip().splitlines()
        if not out:
            return {"available": False, "name": None, "utilization": None}
        parts = [p.strip() for p in out[0].split(",")]
        return {
            "available": True,
            "name": parts[0] if parts else "NVIDIA GPU",
            "driver_version": parts[1] if len(parts) > 1 else None,
            "utilization": _number(parts[2]) if len(parts) > 2 else None,
            "temperature_c": _number(parts[3]) if len(parts) > 3 else None,
            "pstate": parts[4] if len(parts) > 4 else None,
            "power_w": _number(parts[5]) if len(parts) > 5 else None,
            "graphics_clock_mhz": _number(parts[6]) if len(parts) > 6 else None,
            "driver_profile_note": (
                "NexuFlow does not force NVIDIA game profiles through undocumented registry keys. "
                "PCIe power behavior is handled by the reversible temporary Windows power plan."
            ),
        }
    except Exception as exc:
        return {
            "available": False,
            "name": None,
            "utilization": None,
            "driver_version": None,
            "temperature_c": None,
            "error": str(exc),
        }


def nvidia_telemetry(*, force: bool = False) -> dict:
    """Return GPU telemetry without spawning nvidia-smi on every UI refresh."""
    global _CACHE_AT, _CACHE_VALUE
    now = time.monotonic()
    with _CACHE_LOCK:
        if not force and _CACHE_VALUE is not None and now - _CACHE_AT < _CACHE_SECONDS:
            return dict(_CACHE_VALUE)
        value = _read_nvidia()
        _CACHE_VALUE = dict(value)
        _CACHE_AT = now
        return value
