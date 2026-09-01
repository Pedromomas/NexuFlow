from __future__ import annotations

import os

from .winexec import ProtectedPowerShellError, powershell_json


def _powershell_json(script: str) -> dict:
    if os.name != "nt":
        return {"available": False, "reason": "Windows only"}
    try:
        value = powershell_json(script)
        return value if isinstance(value, dict) else {"available": False, "reason": "invalid query response"}
    except ProtectedPowerShellError:
        return {
            "available": False,
            "deferred": True,
            "reason": "PowerShell pre-flight deferred until the protected session closes",
        }
    except (OSError, ValueError, RuntimeError):
        return {"available": False, "reason": "query unavailable"}


def preflight_report() -> dict:
    """Read-only Windows security posture. Never changes boot/security state."""
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$dg=Get-CimInstance Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard
$tpm=Get-Tpm
$sb=Confirm-SecureBootUEFI
$bcd=(bcdedit /enum '{current}') -join "`n"
$mit=Get-ProcessMitigation -System
[ordered]@{
 secure_boot=[bool]$sb; tpm_present=[bool]$tpm.TpmPresent; tpm_ready=[bool]$tpm.TpmReady
 vbs_status=if($dg){[int]$dg.VirtualizationBasedSecurityStatus}else{$null}
 hvci_running=if($dg){$dg.SecurityServicesRunning -contains 2}else{$null}
 testsigning=($bcd -match 'testsigning\s+Yes'); kernel_debug=($bcd -match 'debug\s+Yes')
 integrity_checks_disabled=($bcd -match 'nointegritychecks\s+Yes')
 dep_policy=[string]$mit.DEP.Enable; driver_verifier=([bool](verifier /query 2>$null))
 vulnerable_driver_blocklist_note='Managed by Windows Security; NexuFlow does not modify it.'
 iommu_kernel_dma_protection='reported_by_windows_security_ui'
}|ConvertTo-Json -Compress
"""
    values = _powershell_json(script)
    warnings: list[str] = []
    for key in ("testsigning", "kernel_debug", "integrity_checks_disabled"):
        if values.get(key) is True:
            warnings.append(f"{key} is enabled")
    if values.get("secure_boot") is False:
        warnings.append("Secure Boot is disabled or unavailable")
    if values.get("tpm_present") is False:
        warnings.append("TPM was not detected")
    return {"schema": 2, "read_only": True, "checks": values, "warnings": warnings, "passed": not warnings}
