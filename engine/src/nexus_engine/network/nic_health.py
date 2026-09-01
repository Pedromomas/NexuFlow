from __future__ import annotations

import os
from typing import Any

from ..anti_cheat import running_protected_games
from ..winexec import powershell_json


_EEE_KEYWORDS = frozenset({"*eee", "eee", "advancedeee", "enablegreenethernet", "greenethernet"})
_RSS_KEYWORDS = frozenset({"*rss", "rss"})
_INTERRUPT_MODERATION_KEYWORDS = frozenset({"*interruptmoderation", "interruptmoderation"})


def _is_windows() -> bool:
    return os.name == "nt"


def _deferred(reason: str, protected_games: list[str] | None = None) -> dict:
    return {
        "schema": 1,
        "read_only": True,
        "mutation_performed": False,
        "available": False,
        "deferred": True,
        "reason": reason,
        "protected_games": sorted(set(protected_games or [])),
        "adapter": None,
        "features": {
            "energy_efficient_ethernet": {"status": "deferred", "enabled": None, "supported": None},
            "receive_side_scaling": {"status": "deferred", "enabled": None, "supported": None},
            "interrupt_moderation": {"status": "deferred", "enabled": None, "supported": None},
        },
        "recommendations": [],
    }


def _query_windows_nic() -> dict:
    """Read the active physical adapter state with read-only NetAdapter cmdlets."""
    data = powershell_json(
        r"""
$adapter = Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
  Where-Object { $_.Status -eq 'Up' } |
  Sort-Object -Property ifIndex |
  Select-Object -First 1
if (-not $adapter) {
  [ordered]@{ available=$false; reason='No active physical adapter found' } | ConvertTo-Json -Compress
  return
}
$properties = @(Get-NetAdapterAdvancedProperty -Name $adapter.Name -AllProperties -ErrorAction SilentlyContinue)
$rss = Get-NetAdapterRss -Name $adapter.Name -ErrorAction SilentlyContinue
[ordered]@{
  available=$true
  adapter=[ordered]@{
    name=[string]$adapter.Name
    description=[string]$adapter.InterfaceDescription
    interface_index=[int]$adapter.ifIndex
    link_speed=[string]$adapter.LinkSpeed
  }
  rss=if($rss){[ordered]@{supported=$true; enabled=[bool]$rss.Enabled}}else{[ordered]@{supported=$false; enabled=$null}}
  advanced_properties=@($properties | ForEach-Object {
    [ordered]@{
      registry_keyword=[string]$_.RegistryKeyword
      display_name=[string]$_.DisplayName
      display_value=[string]$_.DisplayValue
      registry_value=$_.RegistryValue
    }
  })
} | ConvertTo-Json -Depth 6 -Compress
"""
    )
    return data if isinstance(data, dict) else {"available": False, "reason": "NIC query returned no data"}


def _coerce_enabled(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, list) and len(value) == 1:
        return _coerce_enabled(value[0])
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "enabled", "enable", "on", "yes"}:
            return True
        if normalized in {"0", "false", "disabled", "disable", "off", "no"}:
            return False
    return None


def _advanced_feature(properties: list[dict], keywords: frozenset[str]) -> dict:
    for item in properties:
        keyword = str(item.get("registry_keyword") or "").strip().casefold()
        if keyword not in keywords:
            continue
        enabled = _coerce_enabled(item.get("registry_value"))
        if enabled is None:
            enabled = _coerce_enabled(item.get("display_value"))
        return {
            "supported": True,
            "enabled": enabled,
            "status": "enabled" if enabled is True else "disabled" if enabled is False else "unknown",
            "driver_label": str(item.get("display_name") or "")[:120] or None,
            "driver_value": str(item.get("display_value") or "")[:120] or None,
        }
    return {"supported": False, "enabled": None, "status": "not_exposed_by_driver"}


def _rss_feature(data: Any, properties: list[dict]) -> dict:
    if isinstance(data, dict) and data.get("supported") is True:
        enabled = _coerce_enabled(data.get("enabled"))
        return {
            "supported": True,
            "enabled": enabled,
            "status": "enabled" if enabled is True else "disabled" if enabled is False else "unknown",
        }
    return _advanced_feature(properties, _RSS_KEYWORDS)


def nic_health_report(*, protected: bool | None = None) -> dict:
    """Describe EEE, RSS and Interrupt Moderation without changing the adapter.

    PowerShell is used only for the read-only query and only after protected
    gameplay has been ruled out. No ``Set-*`` cmdlet is present in this module.
    """
    detected_games: list[str] = []
    if protected is None:
        try:
            detected_games = running_protected_games()
            protected = bool(detected_games)
        except Exception:
            return _deferred("Protected-session status unavailable; NIC query deferred fail-closed")
    if protected:
        return _deferred(
            "NIC driver-property diagnostics are deferred while anti-cheat protected gameplay is active",
            detected_games,
        )
    if not _is_windows():
        report = _deferred("NIC driver-property diagnostics are available only on Windows")
        report["deferred"] = False
        return report

    try:
        raw = _query_windows_nic()
    except Exception as exc:
        report = _deferred(f"NIC diagnostics unavailable: {exc}")
        report["deferred"] = False
        return report
    if raw.get("available") is not True:
        report = _deferred(str(raw.get("reason") or "NIC diagnostics unavailable"))
        report["deferred"] = False
        return report

    properties = raw.get("advanced_properties")
    if not isinstance(properties, list):
        properties = []
    properties = [item for item in properties if isinstance(item, dict)]
    eee = _advanced_feature(properties, _EEE_KEYWORDS)
    rss = _rss_feature(raw.get("rss"), properties)
    moderation = _advanced_feature(properties, _INTERRUPT_MODERATION_KEYWORDS)

    recommendations: list[dict] = []
    if eee.get("enabled") is True:
        recommendations.append({
            "feature": "energy_efficient_ethernet",
            "severity": "info",
            "message": "EEE está ativo. Em alguns adaptadores ele pode contribuir para variação de latência; qualquer teste deve ser manual, reversível e fora do jogo.",
        })
    if rss.get("enabled") is False:
        recommendations.append({
            "feature": "receive_side_scaling",
            "severity": "info",
            "message": "RSS está desativado. Verifique a recomendação do fabricante antes de habilitá-lo manualmente fora de uma sessão protegida.",
        })
    if moderation.get("supported") is True:
        recommendations.append({
            "feature": "interrupt_moderation",
            "severity": "info",
            "message": "Interrupt Moderation troca latência por carga de CPU. O NexuFlow apenas mostra o estado e não recomenda uma configuração universal.",
        })

    return {
        "schema": 1,
        "read_only": True,
        "mutation_performed": False,
        "available": True,
        "deferred": False,
        "reason": None,
        "protected_games": [],
        "adapter": raw.get("adapter") if isinstance(raw.get("adapter"), dict) else None,
        "features": {
            "energy_efficient_ethernet": eee,
            "receive_side_scaling": rss,
            "interrupt_moderation": moderation,
        },
        "recommendations": recommendations,
    }
