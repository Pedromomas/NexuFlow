"""Bounded, neutral-reference diagnostics. Never changes network configuration."""
from __future__ import annotations

import math
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from .dns import PUBLIC_PROVIDERS, _benchmark
from .icmp import icmp_echo_ipv4
from .quality import QUALITY_TARGETS, QualityStore, _local_data_dir, summarize_samples

REFERENCE_NAMES = dict(zip(QUALITY_TARGETS, ("Cloudflare", "Google", "Quad9")))


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def describe_samples(samples: list[dict], target: str) -> dict:
    """No samples is unknown; timeouts are loss, never a zero-ms reply."""
    result = summarize_samples(samples, target=target)
    values = sorted(s["latency_ms"] for s in samples if s["latency_ms"] is not None)
    result.update({"name": REFERENCE_NAMES.get(target, target), "minimum_ms": min(values) if values else None,
                   "maximum_ms": max(values) if values else None,
                   "p95_ms": values[math.ceil(len(values) * .95) - 1] if values else None,
                   "spikes": sum(v > max(50, statistics.median(values) * 2) for v in values) if values else 0})
    if not samples:
        result.update(packet_loss_percent=None, nexus_score=None, grade="Sem amostras")
    result["status"] = "no_data" if not samples else "no_reply" if not values else "attention" if result["packet_loss_percent"] > 0 or (result["jitter_ms"] or 0) > 15 else "stable"
    return result


def connection_history(store: QualityStore | None = None, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    raw = (store or QualityStore()).load().get("samples", [])
    clean = []
    for s in (raw[-240:] if isinstance(raw, list) else []):
        if not isinstance(s, dict) or s.get("target") not in QUALITY_TARGETS or not _number(s.get("timestamp")):
            continue
        if not now - 120 <= s["timestamp"] <= now:
            continue
        latency = s.get("latency_ms")
        clean.append({"target": s["target"], "timestamp": s["timestamp"], "latency_ms": latency if _number(latency) else None})
    clean.sort(key=lambda s: s["timestamp"])
    target = clean[-1]["target"] if clean else None
    # Display one contiguous target segment, not a mixture after failover.
    segment = []
    for s in reversed(clean):
        if s["target"] != target:
            break
        segment.append(s)
    segment.reverse()
    age = now - segment[-1]["timestamp"] if segment else None
    stale = age is None or age > 5
    return {"schema": 1, "read_only": True, "target": target, "stale": stale,
            "age_seconds": round(age, 1) if age is not None else None,
            "summary": describe_samples(segment, target or ""), "samples": segment,
            "note": "Referência de internet, não o servidor da partida. Janela de até 120 segundos; trocas de alvo reiniciam o gráfico."}


@contextmanager
def _scan_lock(directory: Path | None = None):
    """OS advisory lock, released on exit/crash; shared by CLI, API and desktop."""
    directory = directory or _local_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "center.lock").open("a+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"0"); handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Um diagnóstico já está em andamento. Aguarde sua conclusão.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _probe_reference(target: str) -> dict:
    if target not in QUALITY_TARGETS:
        raise ValueError("Referência fora da allowlist")
    samples = []
    for index in range(12):
        latency, _ = icmp_echo_ipv4(target, timeout_ms=600)
        samples.append({"timestamp": time.time(), "latency_ms": latency if _number(latency) else None})
        if index < 11:
            time.sleep(.25)
    return describe_samples(samples, target)


def scan_connection() -> dict:
    with _scan_lock():
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(_probe_reference, QUALITY_TARGETS))
    responsive = [r for r in results if r["latency_ms"] is not None]
    affected = [r for r in responsive if r["status"] == "attention"]
    if not responsive:
        conclusion = "Nenhuma referência respondeu. Verifique a conexão; firewall ou bloqueio de ICMP também podem explicar isso."
    elif len(affected) >= 2:
        conclusion = "Oscilação em mais de uma referência. Repita sem downloads e compare cabo/Wi-Fi antes de atribuir o problema ao provedor."
    elif affected or len(responsive) < 3:
        conclusion = "As referências divergem. Um destino pode limitar ICMP; esse resultado isolado não comprova falha da sua internet."
    else:
        conclusion = "Referências estáveis nesta amostra curta. Isso não exclui problemas no servidor do jogo ou em outro horário."
    return {"schema": 1, "kind": "connection_scan", "measured_at": time.time(), "read_only": True,
            "results": results, "conclusion": conclusion, "max_packets": 36,
            "method": "12 consultas ICMP por referência no Windows, timeout de 600 ms. Fora do Windows: conexão TCP/443, não ICMP.",
            "privacy": "Sem IP pessoal, caminho de arquivo, MAC ou dados de jogos no relatório."}


def rank_dns() -> dict:
    with _scan_lock():
        with ThreadPoolExecutor(max_workers=3) as pool:
            scores = list(pool.map(_benchmark, PUBLIC_PROVIDERS))
    scores.sort(key=lambda s: (s.success_rate < .75, s.score, s.provider.name))
    rows = [{**s.to_dict(), "samples": len(s.samples_ms), "successful": len(s.successful),
             "eligible": s.success_rate >= .75 and s.median_ms is not None} for s in scores]
    return {"schema": 1, "kind": "dns_ranking", "measured_at": time.time(), "read_only": True, "results": rows,
            "recommendation": next((r["provider"] for r in rows if r["eligible"]), None),
            "method": "6 consultas UDP/53 por provedor: dois servidores, três domínios públicos fixos. Ranking penaliza falhas (150 ms × proporção de falhas).",
            "note": "Mede resolução DNS, não ping da partida. Não mede seu DNS atual, não considera todos os recursos de privacidade e não aplica alterações."}
