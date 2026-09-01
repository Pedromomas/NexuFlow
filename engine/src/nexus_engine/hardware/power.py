from __future__ import annotations

import ctypes
import os
import re
from ctypes import wintypes

from ..winexec import run_command
from ..policy_runtime import assert_feature_enabled

GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("ACLineStatus", wintypes.BYTE), ("BatteryFlag", wintypes.BYTE), ("BatteryLifePercent", wintypes.BYTE), ("SystemStatusFlag", wintypes.BYTE), ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD)]


def on_ac_power() -> bool:
    if os.name != "nt":
        return False
    s = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
        return False
    return s.ACLineStatus == 1


class PowerPlanManager:
    @staticmethod
    def active_guid() -> str:
        out = run_command(["powercfg", "/getactivescheme"]).stdout
        match = GUID_RE.search(out)
        if not match:
            raise RuntimeError("Could not parse active power scheme GUID")
        return match.group(0)

    def apply(self, aggressive: bool = False, original: str | None = None) -> dict:
        assert_feature_enabled("power_plan")
        if os.name != "nt":
            return {"changed": False, "reason": "Windows only"}
        original = original or self.active_guid()
        if not on_ac_power():
            return {"changed": False, "original": original, "reason": "Laptop is not on AC power"}
        out = run_command(["powercfg", "/duplicatescheme", original]).stdout
        match = GUID_RE.search(out)
        if not match:
            raise RuntimeError("Could not create temporary NexuFlow power scheme")
        temporary = match.group(0)
        try:
            run_command(["powercfg", "/changename", temporary, "NexuFlow Temporary"])
            run_command(["powercfg", "/setacvalueindex", temporary, "SUB_PCIEXPRESS", "ASPM", "0"])
            # Always permit the processor to reach 100%. Aggressive additionally
            # pins the AC minimum to 100%, trading power/heat for consistency.
            run_command(["powercfg", "/setacvalueindex", temporary, "SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"])
            if aggressive:
                run_command(["powercfg", "/setacvalueindex", temporary, "SUB_PROCESSOR", "PROCTHROTTLEMIN", "100"])
            run_command(["powercfg", "/setactive", temporary])
            return {"changed": True, "original": original, "temporary": temporary}
        except Exception:
            run_command(["powercfg", "/setactive", original], check=False)
            run_command(["powercfg", "/delete", temporary], check=False)
            raise

    @staticmethod
    def restore(snapshot: dict) -> None:
        if os.name != "nt":
            return
        original, temporary = snapshot.get("original"), snapshot.get("temporary")
        if original:
            run_command(["powercfg", "/setactive", original], check=False)
        if temporary:
            run_command(["powercfg", "/delete", temporary], check=False)

        # Crash recovery: remove stale temporary NexuFlow plans whose GUID was not
        # checkpointed yet. Never delete the user's original active scheme.
        try:
            listing = run_command(["powercfg", "/list"], check=False).stdout
            for line in listing.splitlines():
                if "NexuFlow Temporary" not in line and "Nexus Booster Temporary" not in line:
                    continue
                match = GUID_RE.search(line)
                if match and match.group(0).lower() != str(original or "").lower():
                    run_command(["powercfg", "/delete", match.group(0)], check=False)
        except Exception:
            pass
