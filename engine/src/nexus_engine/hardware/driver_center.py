from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from ..anti_cheat import running_protected_games
from ..winexec import ProtectedPowerShellError, powershell_json


WINDOWS_OPTIONAL_UPDATES_URI = "ms-settings:windowsupdate-optionalupdates"
MAX_DRIVER_UPDATES = 50


def _is_windows() -> bool:
    return os.name == "nt"


def _clean_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    return text[:limit] or None


def _query_windows_update() -> dict:
    """Search Windows Update for offered drivers without downloading them."""
    result = powershell_json(
        r"""
$session = New-Object -ComObject Microsoft.Update.Session
$session.ClientApplicationID = 'NexuFlow Driver Center 1.5.5'
$searcher = $session.CreateUpdateSearcher()
$result = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Driver'")
$items = @()
foreach ($update in @($result.Updates)) {
  $manufacturer = $null
  $model = $null
  $driverClass = $null
  $provider = $null
  $driverDate = $null
  try { $manufacturer = [string]$update.DriverManufacturer } catch {}
  try { $model = [string]$update.DriverModel } catch {}
  try { $driverClass = [string]$update.DriverClass } catch {}
  try { $provider = [string]$update.DriverProvider } catch {}
  try { $driverDate = ([datetime]$update.DriverVerDate).ToUniversalTime().ToString('o') } catch {}
  $items += [ordered]@{
    title = [string]$update.Title
    manufacturer = $manufacturer
    model = $model
    driver_class = $driverClass
    provider = $provider
    driver_date = $driverDate
    downloaded = [bool]$update.IsDownloaded
    mandatory = [bool]$update.IsMandatory
  }
}
[ordered]@{
  result_code = [int]$result.ResultCode
  count = [int]$items.Count
  updates = @($items)
} | ConvertTo-Json -Depth 6 -Compress
""",
        timeout=120.0,
    )
    return result if isinstance(result, dict) else {"result_code": 0, "count": 0, "updates": []}


def _unavailable(reason: str, *, deferred: bool = False, protected_games: list[str] | None = None) -> dict:
    return {
        "schema": 1,
        "available": False,
        "deferred": deferred,
        "read_only": True,
        "scan_source": "windows_update_agent",
        "status": "deferred" if deferred else "unavailable",
        "updates_offered": 0,
        "updates": [],
        "download_performed": False,
        "installation_performed": False,
        "protected_games": protected_games or [],
        "reason": reason,
    }


def scan_driver_updates() -> dict:
    """Run an explicit, read-only Windows Update driver search.

    A zero result means only that Windows Update offered no driver update at
    scan time. It is not presented as proof that every vendor driver is the
    newest release. Hardware IDs, device instance IDs and local paths are never
    returned to the UI.
    """
    protected = running_protected_games()
    if protected:
        return _unavailable(
            "O scan de drivers foi adiado até o jogo protegido ser fechado.",
            deferred=True,
            protected_games=protected,
        )
    if not _is_windows():
        return _unavailable("O Driver Center está disponível somente no Windows.")

    try:
        raw = _query_windows_update()
    except ProtectedPowerShellError:
        return _unavailable(
            "O scan de drivers foi bloqueado porque uma sessão protegida começou.",
            deferred=True,
        )
    except Exception as exc:
        return _unavailable(f"O Windows Update não concluiu o scan: {_clean_text(exc, 240)}")

    updates: list[dict] = []
    raw_updates = raw.get("updates")
    if isinstance(raw_updates, dict):
        raw_updates = [raw_updates]
    if not isinstance(raw_updates, list):
        raw_updates = []
    for item in raw_updates[:MAX_DRIVER_UPDATES]:
        if not isinstance(item, dict):
            continue
        updates.append(
            {
                "title": _clean_text(item.get("title"), 200) or "Atualização de driver",
                "manufacturer": _clean_text(item.get("manufacturer"), 120),
                "model": _clean_text(item.get("model"), 160),
                "driver_class": _clean_text(item.get("driver_class"), 80),
                "provider": _clean_text(item.get("provider"), 120),
                "driver_date": _clean_text(item.get("driver_date"), 48),
                "downloaded": item.get("downloaded") is True,
                "mandatory": item.get("mandatory") is True,
            }
        )

    offered = len(updates)
    return {
        "schema": 1,
        "available": True,
        "deferred": False,
        "read_only": True,
        "scan_source": "windows_update_agent",
        "status": "updates_available" if offered else "no_updates_offered",
        "updates_offered": offered,
        "updates": updates,
        "download_performed": False,
        "installation_performed": False,
        "protected_games": [],
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "result_code": int(raw.get("result_code") or 0),
        "reason": None,
        "privacy": "Scan local; sem hardware ID, device ID, caminho pessoal ou upload para o NexuFlow.",
        "caution": (
            "Nenhuma atualização oferecida não prova que todo driver do fabricante é o mais novo. "
            "O Windows Update é a fonte segura padrão; drivers opcionais continuam sob escolha do usuário."
        ),
    }


def open_windows_driver_updates() -> dict:
    """Open the fixed official Windows Settings page; never install silently."""
    if not _is_windows():
        raise OSError("Windows Update settings are available only on Windows")
    os.startfile(WINDOWS_OPTIONAL_UPDATES_URI)  # type: ignore[attr-defined]
    return {
        "ok": True,
        "opened": True,
        "uri": WINDOWS_OPTIONAL_UPDATES_URI,
        "installation_performed": False,
        "message": "Atualizações opcionais do Windows foram abertas para sua confirmação.",
    }
