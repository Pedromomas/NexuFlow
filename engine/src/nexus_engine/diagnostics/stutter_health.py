from __future__ import annotations

import os
import statistics
import time
from typing import Any

import psutil


def _is_windows() -> bool:
    return os.name == "nt"


def _rate(after: Any, before: Any, attribute: str, elapsed: float) -> float | None:
    try:
        delta = float(getattr(after, attribute)) - float(getattr(before, attribute))
    except (AttributeError, TypeError, ValueError):
        return None
    if elapsed <= 0 or delta < 0:
        return None
    return delta / elapsed


def classify_stutter_snapshot(metrics: dict) -> dict:
    """Classify strong system-pressure signals without claiming root cause."""
    signals: list[dict] = []
    cpu = metrics.get("cpu") if isinstance(metrics.get("cpu"), dict) else {}
    memory = metrics.get("memory") if isinstance(metrics.get("memory"), dict) else {}
    rates = metrics.get("rates") if isinstance(metrics.get("rates"), dict) else {}

    total_cpu = cpu.get("total_percent")
    peak_core = cpu.get("peak_core_percent")
    if (isinstance(total_cpu, (int, float)) and total_cpu >= 92.0) or (
        isinstance(peak_core, (int, float)) and peak_core >= 98.0
    ):
        signals.append({
            "code": "cpu_pressure",
            "severity": "warning",
            "message": "A amostra encontrou pressão elevada de CPU. Isso pode acompanhar stutter, mas não identifica sozinho a causa.",
        })

    memory_percent = memory.get("percent")
    available_gb = memory.get("available_gb")
    if (isinstance(memory_percent, (int, float)) and memory_percent >= 92.0) or (
        isinstance(available_gb, (int, float)) and available_gb <= 1.0
    ):
        signals.append({
            "code": "memory_pressure",
            "severity": "warning",
            "message": "Há pouca memória disponível nesta amostra; paginação ou encerramento de aplicativos pode merecer investigação.",
        })

    context_switches = rates.get("context_switches_per_second")
    if isinstance(context_switches, (int, float)) and context_switches >= 150_000:
        signals.append({
            "code": "scheduler_activity",
            "severity": "info",
            "message": "A atividade do escalonador está alta. O contador não prova latência DPC/ISR nem aponta um driver específico.",
        })

    interrupts = rates.get("interrupts_per_second")
    if isinstance(interrupts, (int, float)) and interrupts >= 50_000:
        signals.append({
            "code": "interrupt_activity",
            "severity": "info",
            "message": "A taxa agregada de interrupções está elevada. Somente uma análise ETW separada poderia atribuir isso a um driver.",
        })

    disk_mbps = rates.get("disk_megabytes_per_second")
    if isinstance(disk_mbps, (int, float)) and disk_mbps >= 250.0:
        signals.append({
            "code": "storage_activity",
            "severity": "info",
            "message": "A amostra mostra atividade intensa de armazenamento, sem medir latência individual das operações.",
        })

    return {
        "classification": "possible_system_pressure" if signals else "no_obvious_system_pressure_in_sample",
        "stutter_cause_confirmed": False,
        "signals": signals,
        "confidence": "low" if signals else "insufficient_sample_for_root_cause",
    }


def _unavailable(reason: str) -> dict:
    return {
        "schema": 1,
        "read_only": True,
        "available": False,
        "reason": reason,
        "classification": {
            "classification": "unavailable",
            "stutter_cause_confirmed": False,
            "signals": [],
            "confidence": "none",
        },
        "etw": {
            "supported_by_platform": _is_windows(),
            "trace_started": False,
            "mode": "capability_only",
        },
    }


def stutter_health_snapshot(sample_interval: float = 0.15) -> dict:
    """Take a short psutil snapshot; never start ETW or inspect game processes."""
    try:
        interval = max(0.0, min(1.0, float(sample_interval)))
    except (TypeError, ValueError):
        return _unavailable("Invalid sample interval")

    try:
        cpu_before = psutil.cpu_stats()
        disk_before = psutil.disk_io_counters()
        net_before = psutil.net_io_counters()
        started = time.monotonic()
        per_cpu = [float(value) for value in psutil.cpu_percent(interval=interval, percpu=True)]
        elapsed = max(time.monotonic() - started, 0.000001)
        cpu_after = psutil.cpu_stats()
        disk_after = psutil.disk_io_counters()
        net_after = psutil.net_io_counters()
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        frequency = psutil.cpu_freq()
    except (OSError, ValueError, psutil.Error) as exc:
        return _unavailable(f"System counters unavailable: {exc}")

    disk_read = _rate(disk_after, disk_before, "read_bytes", elapsed) if disk_before and disk_after else None
    disk_write = _rate(disk_after, disk_before, "write_bytes", elapsed) if disk_before and disk_after else None
    net_sent = _rate(net_after, net_before, "bytes_sent", elapsed) if net_before and net_after else None
    net_received = _rate(net_after, net_before, "bytes_recv", elapsed) if net_before and net_after else None
    context_switches = _rate(cpu_after, cpu_before, "ctx_switches", elapsed)
    interrupts = _rate(cpu_after, cpu_before, "interrupts", elapsed)

    disk_total = None if disk_read is None or disk_write is None else (disk_read + disk_write) / (1024 * 1024)
    metrics = {
        "sample_interval_seconds": round(elapsed, 3),
        "cpu": {
            "total_percent": round(statistics.fmean(per_cpu), 1) if per_cpu else None,
            "peak_core_percent": round(max(per_cpu), 1) if per_cpu else None,
            "logical_cores": psutil.cpu_count(logical=True),
            "current_mhz": round(float(frequency.current), 0) if frequency else None,
        },
        "memory": {
            "percent": round(float(memory.percent), 1),
            "available_gb": round(float(memory.available) / (1024 ** 3), 2),
            "swap_percent": round(float(swap.percent), 1),
        },
        "rates": {
            "context_switches_per_second": None if context_switches is None else round(context_switches, 0),
            "interrupts_per_second": None if interrupts is None else round(interrupts, 0),
            "disk_megabytes_per_second": None if disk_total is None else round(disk_total, 2),
            "network_send_megabytes_per_second": None if net_sent is None else round(net_sent / (1024 * 1024), 2),
            "network_receive_megabytes_per_second": None if net_received is None else round(net_received / (1024 * 1024), 2),
        },
    }

    return {
        "schema": 1,
        "read_only": True,
        "available": True,
        "reason": None,
        "process_inspection": False,
        "driver_attribution": False,
        "metrics": metrics,
        "classification": classify_stutter_snapshot(metrics),
        "etw": {
            "supported_by_platform": _is_windows(),
            "trace_started": False,
            "mode": "capability_only",
            "note": "ETW pode permitir diagnóstico detalhado em uma função futura, mas nenhum trace é iniciado por este snapshot.",
        },
        "limitations": [
            "Não mede frame time do jogo.",
            "Não mede duração de DPC/ISR e não atribui atividade a drivers.",
            "Não consulta processos, memória, módulos, sockets ou anti-cheat.",
            "Uma amostra curta não confirma a causa de microtravamentos.",
        ],
    }
