from __future__ import annotations

import os

import psutil

from ..anti_cheat import assert_mutation_allowed
from ..policy_runtime import assert_feature_enabled
from ..winexec import powershell_json, run_command


class ServiceManager:
    # Narrow allow-list only. Security/Defender/Firewall services are never touched.
    TARGETS = ("DiagTrack", "wuauserv")
    UPDATE_WORKERS = {"tiworker.exe", "trustedinstaller.exe", "mousocoreworker.exe"}

    @classmethod
    def _windows_update_busy(cls) -> bool:
        for proc in psutil.process_iter(["name"]):
            try:
                if (proc.info.get("name") or "").lower() in cls.UPDATE_WORKERS:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def snapshot(self) -> list[dict]:
        if os.name != "nt":
            return []
        quoted = ",".join(f"'{x}'" for x in self.TARGETS)
        update_busy = self._windows_update_busy()
        data = powershell_json(rf"""
$result = @()
foreach($name in @({quoted})) {{
  $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
  if($svc) {{ $result += [PSCustomObject]@{{Name=$name; WasRunning=($svc.Status -eq 'Running')}} }}
}}
$result | ConvertTo-Json -Compress
""")
        if data is None:
            return []
        result = data if isinstance(data, list) else [data]
        for item in result:
            item["SafeToPause"] = not (item.get("Name") == "wuauserv" and update_busy)
            if item.get("Name") == "wuauserv" and update_busy:
                item["SkipReason"] = "Windows Update worker is active"
        return result

    @staticmethod
    def pause(snapshot: list[dict]) -> None:
        assert_mutation_allowed("service_pausing")
        assert_feature_enabled("service_pause")
        if os.name != "nt":
            return
        for item in snapshot:
            if item.get("WasRunning") and item.get("SafeToPause", True):
                name = str(item.get("Name", "")).replace("'", "")
                if name:
                    try:
                        powershell_json(f"Stop-Service -Name '{name}' -Force -ErrorAction Stop; @{{ok=$true}} | ConvertTo-Json -Compress")
                        item["PausedByNexus"] = True
                    except Exception as exc:
                        item["PauseError"] = str(exc)

    @staticmethod
    def restore(snapshot: list[dict]) -> None:
        if os.name != "nt":
            return
        errors: list[str] = []
        for item in snapshot:
            # Only restart a service that NexuFlow itself successfully stopped.
            if item.get("WasRunning") and item.get("PausedByNexus"):
                name = str(item.get("Name", "")).replace("'", "")
                if name:
                    try:
                        # Direct SCM client; rollback must stay PowerShell-free if
                        # an anti-cheat protected game started in the meantime.
                        run_command(["sc.exe", "start", name])
                    except Exception as exc:
                        errors.append(f"{name}: {exc}")
        if errors:
            raise RuntimeError("Service rollback failed: " + "; ".join(errors))
