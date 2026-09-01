from __future__ import annotations

import os
import re
from typing import Any

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows interpreter
    winreg = None  # type: ignore[assignment]


GAME_BAR_KEY = r"Software\Microsoft\GameBar"
GPU_PREFERENCES_KEY = r"Software\Microsoft\DirectX\UserGpuPreferences"
_GPU_PREFERENCE_RE = re.compile(r"(?:^|;)\s*GpuPreference\s*=\s*([012])\s*(?:;|$)", re.IGNORECASE)


def _is_windows() -> bool:
    return os.name == "nt" and winreg is not None


def _read_game_mode() -> dict:
    if winreg is None:
        return {"available": False, "status": "unknown", "reason": "Windows registry unavailable"}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, GAME_BAR_KEY, 0, winreg.KEY_READ) as key:
            for value_name in ("AutoGameModeEnabled", "AllowAutoGameMode"):
                try:
                    value, _kind = winreg.QueryValueEx(key, value_name)
                except OSError:
                    continue
                enabled = bool(value) if isinstance(value, int) and value in (0, 1) else None
                return {
                    "available": True,
                    "status": "enabled" if enabled is True else "disabled" if enabled is False else "unknown",
                    "enabled": enabled,
                    "source_value": value_name,
                }
    except OSError:
        pass
    return {
        "available": False,
        "status": "unknown",
        "enabled": None,
        "reason": "Game Mode preference is not explicitly stored for this user",
    }


def _read_gpu_preferences() -> dict:
    counts = {"system_default": 0, "power_saving": 0, "high_performance": 0, "unrecognized": 0}
    if winreg is None:
        return {"available": False, "stored_entries": 0, **counts}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, GPU_PREFERENCES_KEY, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    _application_path, raw_value, _kind = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                match = _GPU_PREFERENCE_RE.search(str(raw_value or ""))
                preference = match.group(1) if match else None
                bucket = {
                    "0": "system_default",
                    "1": "power_saving",
                    "2": "high_performance",
                }.get(preference, "unrecognized")
                counts[bucket] += 1
    except OSError:
        return {"available": False, "stored_entries": 0, **counts}
    return {
        "available": True,
        "stored_entries": sum(counts.values()),
        **counts,
    }


def windows_gaming_report() -> dict[str, Any]:
    """Read Windows gaming preferences without inspecting a game process.

    Executable paths stored under ``UserGpuPreferences`` are counted but never
    returned, keeping the report useful without exporting personal paths.
    """
    if not _is_windows():
        return {
            "schema": 1,
            "read_only": True,
            "mutation_performed": False,
            "process_inspection": False,
            "protected_process_access": False,
            "available": False,
            "reason": "Windows gaming preferences are available only on Windows",
            "game_mode": {"available": False, "status": "unknown", "enabled": None},
            "graphics_preferences": {"available": False, "stored_entries": 0},
        }

    return {
        "schema": 1,
        "read_only": True,
        "mutation_performed": False,
        "process_inspection": False,
        "protected_process_access": False,
        "available": True,
        "reason": None,
        "game_mode": _read_game_mode(),
        "graphics_preferences": {
            **_read_gpu_preferences(),
            "application_paths_exported": False,
            "note": "Preferências por aplicativo são resumidas; caminhos de executáveis não são exportados.",
        },
    }
