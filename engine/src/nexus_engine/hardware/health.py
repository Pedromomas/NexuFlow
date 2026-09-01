from __future__ import annotations

import os
import re

import psutil

from .nvidia import nvidia_telemetry
from .power import PowerPlanManager, on_ac_power
from ..anti_cheat import running_protected_games
from ..network.interfaces import InterfaceManager
from ..winexec import run_command


def _parse_link_speed_mbps(value: str | None) -> float | None:
    text = (value or "").strip().lower().replace(",", ".")
    match = re.search(r"([0-9.]+)\s*(gbps|mbps)", text)
    if not match:
        return None
    number = float(match.group(1))
    return round(number * 1000.0 if match.group(2) == "gbps" else number, 1)


def _power_scheme() -> dict:
    if os.name != "nt":
        return {"guid": None, "name": None, "on_ac_power": False}
    try:
        out = run_command(["powercfg", "/getactivescheme"], check=False).stdout.strip()
        guid_match = re.search(r"[0-9a-fA-F-]{36}", out)
        name_match = re.search(r"\(([^)]+)\)\s*$", out)
        return {
            "guid": guid_match.group(0) if guid_match else None,
            "name": name_match.group(1) if name_match else None,
            "on_ac_power": on_ac_power(),
        }
    except Exception as exc:
        return {"guid": None, "name": None, "on_ac_power": None, "error": str(exc)}


def gaming_health(*, protected_runtime: bool | None = None) -> dict:
    if protected_runtime is None:
        protected_runtime = bool(running_protected_games())

    cpu_percent = psutil.cpu_percent(interval=0.08)
    memory = psutil.virtual_memory()
    freq = psutil.cpu_freq()
    gpu = nvidia_telemetry()
    warnings: list[dict] = []

    interface: dict = {}
    if protected_runtime:
        # Valve documents PowerShell among software that can contribute to a
        # VAC-secure connection error. InterfaceManager currently uses Windows
        # PowerShell cmdlets, so protected-game telemetry deliberately avoids
        # spawning it while the game is running. Quality/jitter/loss sampling
        # remains native ICMP and does not require adapter introspection.
        interface = {
            "deferred": True,
            "reason": "Protected-game compatibility mode: adapter introspection deferred until the game closes",
        }
    else:
        try:
            iface = InterfaceManager.primary_ipv4()
            speed_mbps = _parse_link_speed_mbps(iface.link_speed)
            text = f"{iface.alias} {iface.description}".lower()
            is_wifi = any(marker in text for marker in ("wi-fi", "wifi", "wireless", "802.11"))
            interface = {
                "alias": iface.alias,
                "description": iface.description,
                "link_speed": iface.link_speed,
                "link_speed_mbps": speed_mbps,
                "connection_type": "Wi-Fi" if is_wifi else "Ethernet/Other",
                "mtu": iface.mtu,
                "gateway": iface.next_hop,
                "virtual": iface.probably_virtual,
            }
            if is_wifi:
                warnings.append({"severity": "info", "code": "wifi", "message": "Wi-Fi detectado; Ethernet tende a oferecer menor jitter para jogos competitivos."})
            if speed_mbps is not None and speed_mbps <= 100:
                warnings.append({"severity": "warning", "code": "slow_link", "message": f"Link negociado em {speed_mbps:g} Mbps; verifique cabo, porta e duplex."})
        except Exception as exc:
            interface = {"error": str(exc)}

    available_gb = memory.available / (1024 ** 3)
    if available_gb < 2.0:
        warnings.append({"severity": "warning", "code": "low_memory", "message": f"Apenas {available_gb:.1f} GB de RAM disponível."})

    gpu_temp = gpu.get("temperature_c")
    if isinstance(gpu_temp, (int, float)) and gpu_temp >= 85:
        warnings.append({"severity": "warning", "code": "gpu_hot", "message": f"GPU em {gpu_temp:.0f} °C; possível limitação térmica sob carga."})

    current_mhz = float(freq.current) if freq else None
    max_mhz = float(freq.max) if freq and freq.max else None
    possible_clock_constraint = bool(
        cpu_percent >= 80 and current_mhz and max_mhz and max_mhz > 0 and current_mhz < max_mhz * 0.60
    )
    if possible_clock_constraint:
        warnings.append({
            "severity": "info",
            "code": "cpu_clock_constraint",
            "message": "CPU sob carga com clock agregado baixo. Isso pode ser energia/temperatura, mas não é prova de thermal throttling.",
        })

    return {
        "cpu": {
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "utilization_percent": round(cpu_percent, 1),
            "current_mhz": None if current_mhz is None else round(current_mhz, 0),
            "max_mhz": None if max_mhz is None else round(max_mhz, 0),
            "possible_clock_constraint": possible_clock_constraint,
            "thermal_throttling": "not_directly_observable_without_vendor_specific_telemetry",
        },
        "memory": {
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(available_gb, 2),
            "percent": round(memory.percent, 1),
        },
        "gpu": gpu,
        "network": interface,
        "power": _power_scheme(),
        "warnings": warnings,
    }
