from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import psutil

from .catalog import GameCatalog
from .anti_cheat import is_protected_game


def _expand_hint(hint: str) -> list[Path]:
    expanded = os.path.expandvars(hint)
    matches = [Path(x) for x in glob.glob(expanded)]
    return sorted((p for p in matches if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)


def _steam_library_paths() -> list[Path]:
    paths: list[Path] = []
    candidates = [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]
    if os.name == "nt":
        try:
            import winreg
            pairs = (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            )
            for hive, sub, name in pairs:
                try:
                    with winreg.OpenKey(hive, sub) as key:
                        value, _ = winreg.QueryValueEx(key, name)
                        candidates.append(Path(value))
                except OSError:
                    pass
        except ImportError:
            pass
    for steam in candidates:
        if steam.exists() and steam not in paths:
            paths.append(steam)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            try:
                text = vdf.read_text(encoding="utf-8", errors="ignore")
                for raw in re.findall(r'"path"\s+"([^"]+)"', text):
                    p = Path(raw.replace("\\\\", "\\"))
                    if p.exists() and p not in paths:
                        paths.append(p)
            except OSError:
                pass
    return paths


def _cs2_steam_candidates() -> list[Path]:
    rel = Path("steamapps/common/Counter-Strike Global Offensive/game/bin/win64/cs2.exe")
    return [lib / rel for lib in _steam_library_paths() if (lib / rel).is_file()]


def _running_processes() -> dict[str, list[dict]]:
    # Name/PID enumeration is sufficient to detect protected titles and avoids
    # querying their executable path/handle unless a non-protected profile
    # actually needs it.
    by_name: dict[str, list[dict]] = {}
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name:
                by_name.setdefault(name, []).append({"pid": proc.info["pid"]})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return by_name


def discover_games(catalog: GameCatalog | None = None) -> list[dict]:
    catalog = catalog or GameCatalog.load()
    running = _running_processes()
    result: list[dict] = []
    for game in catalog.games.values():
        hit = None
        for process_name in game.process_names:
            entries = running.get(process_name.lower()) or []
            if entries:
                hit = entries[0]
                break
        installed_paths: list[Path] = []
        if hit and not is_protected_game(game.id):
            try:
                exe = psutil.Process(int(hit["pid"])).exe()
                if exe:
                    installed_paths.append(Path(exe))
            except (psutil.Error, OSError, ValueError):
                pass
        for hint in game.install_hints:
            installed_paths.extend(_expand_hint(hint))
        if game.id == "cs2":
            installed_paths.extend(_cs2_steam_candidates())
        unique: list[Path] = []
        for p in installed_paths:
            try:
                rp = p.resolve()
            except OSError:
                rp = p
            try:
                if rp.is_file() and rp not in unique:
                    unique.append(rp)
            except (OSError, PermissionError):
                # Discovery is best-effort and must not fail API startup when
                # Windows denies metadata access to another installed title.
                continue
        executable = str(unique[0]) if unique else None
        result.append({
            "id": game.id,
            "display_name": game.display_name,
            "installed": bool(executable) or hit is not None,
            "running": hit is not None,
            "executable": executable,
            "pid": hit.get("pid") if hit else None,
        })
    return result


def preferred_running_game(games: list[dict]) -> dict | None:
    """Prefer an anti-cheat protected title when multiple games are running.

    This prevents a previously started Roblox/non-protected session from being
    treated as authoritative while VALORANT/LoL/CS2 is also active.
    """
    protected = next(
        (g for g in games if g.get("running") and is_protected_game(g.get("id"))),
        None,
    )
    if protected:
        return protected
    return next((g for g in games if g.get("running")), None)


def first_running_game(catalog: GameCatalog | None = None) -> dict | None:
    return preferred_running_game(discover_games(catalog))
