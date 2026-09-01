from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path


class ElevationError(RuntimeError):
    pass


def is_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_elevated() -> None:
    if os.name != "nt":
        raise ElevationError("NexuFlow privileged engine requires Windows")
    if getattr(sys, "frozen", False):
        executable, args = sys.executable, sys.argv[1:]
    else:
        executable, args = sys.executable, [str(Path(sys.argv[0]).resolve()), *sys.argv[1:]]
    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.restype = ctypes.c_void_p
    rc = shell_execute(None, "runas", executable, subprocess.list2cmdline(args), None, 0)
    rc_value = int(rc or 0)
    if rc_value <= 32:
        raise ElevationError(f"UAC elevation failed or was cancelled (ShellExecute={rc_value})")
    raise SystemExit(0)


def require_admin(auto_elevate: bool = False) -> None:
    if is_admin():
        return
    if auto_elevate:
        relaunch_elevated()
    raise PermissionError("Administrator privileges are required")
