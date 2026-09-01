from __future__ import annotations

import ipaddress
import os
import statistics
from typing import Callable

from .icmp import IP_SUCCESS, IP_TTL_EXPIRED_REASSEM, IP_TTL_EXPIRED_TRANSIT, icmp_echo_detail


def _hop_summary(ttl: int, probes: list[dict]) -> dict:
    addresses = [p.get("address") for p in probes if p.get("address")]
    address = next(iter(addresses), None)
    latencies = [float(p["latency_ms"]) for p in probes if p.get("latency_ms") is not None]
    received = len([p for p in probes if p.get("address")])
    loss = (1.0 - received / len(probes)) * 100.0 if probes else 100.0
    median = statistics.median(latencies) if latencies else None
    jitter = (
        statistics.fmean(abs(b - a) for a, b in zip(latencies, latencies[1:]))
        if len(latencies) >= 2
        else 0.0 if latencies else None
    )
    return {
        "hop": ttl,
        "address": address,
        "received": received,
        "sent": len(probes),
        "loss_percent": round(loss, 1),
        "median_ms": None if median is None else round(float(median), 2),
        "jitter_ms": None if jitter is None else round(float(jitter), 2),
        "statuses": [p.get("status") for p in probes],
    }


def analyze_route_hops(hops: list[dict]) -> dict:
    """Heuristic diagnostics only; never changes routing from traceroute data.

    Intermediate routers frequently deprioritize ICMP. We therefore prefer
    degradations that *persist* across later responsive hops and the destination
    instead of blaming the first router that drops a probe.
    """
    responsive = [h for h in hops if h.get("median_ms") is not None]
    observations: list[str] = []
    latency_candidate = None
    loss_candidate = None
    jitter_candidate = None

    if not responsive:
        return {
            "candidate_degradation_hop": None,
            "candidate_latency_hop": None,
            "candidate_loss_hop": None,
            "candidate_jitter_hop": None,
            "observations": ["Nenhum hop respondeu ao diagnóstico ICMP."],
            "caution": "Ausência de resposta ICMP não prova perda de tráfego real.",
        }

    destination = responsive[-1]
    destination_loss = float(destination.get("loss_percent") or 0.0)
    destination_jitter = float(destination.get("jitter_ms") or 0.0)

    # Find the first latency step that remains visible in subsequent hops.
    for index in range(1, len(responsive)):
        previous = float(responsive[index - 1].get("median_ms") or 0.0)
        current = float(responsive[index].get("median_ms") or 0.0)
        jump = current - previous
        later = [float(h.get("median_ms") or 0.0) for h in responsive[index:]]
        persistent = len(later) >= 2 and sum(1 for value in later if value >= previous + 10.0) >= min(2, len(later))
        if jump >= 15.0 and persistent:
            latency_candidate = responsive[index].get("hop")
            observations.append(
                f"Aumento persistente de latência de aproximadamente {jump:.0f} ms começa no hop "
                f"{responsive[index].get('hop')} ({responsive[index].get('address')})."
            )
            break

    # Only localize apparent loss when it also reaches the destination. An
    # isolated lossy intermediate router is intentionally ignored.
    if destination_loss >= 2.0:
        for index, hop in enumerate(responsive):
            if float(hop.get("loss_percent") or 0.0) < 2.0:
                continue
            later = responsive[index:]
            matching = [h for h in later if float(h.get("loss_percent") or 0.0) >= 2.0]
            if len(matching) >= 2 or hop is destination:
                loss_candidate = hop.get("hop")
                break
        observations.append(f"Perda ponta-a-ponta observada no destino: {destination_loss:.1f}%.")
        if loss_candidate is not None and loss_candidate != destination.get("hop"):
            observations.append(f"A perda aparente começa a persistir por volta do hop {loss_candidate}.")

    if destination_jitter >= 10.0:
        for index, hop in enumerate(responsive):
            if float(hop.get("jitter_ms") or 0.0) < 8.0:
                continue
            later = responsive[index:]
            if any(float(h.get("jitter_ms") or 0.0) >= 8.0 for h in later[1:]) or hop is destination:
                jitter_candidate = hop.get("hop")
                break
        observations.append(f"Jitter elevado permanece até o destino: {destination_jitter:.1f} ms.")
        if jitter_candidate is not None and jitter_candidate != destination.get("hop"):
            observations.append(f"O jitter elevado começa a persistir por volta do hop {jitter_candidate}.")

    if not observations:
        observations.append("Nenhuma degradação persistente óbvia foi identificada nesta amostra.")

    candidate = latency_candidate or loss_candidate or jitter_candidate
    return {
        "candidate_degradation_hop": candidate,
        "candidate_latency_hop": latency_candidate,
        "candidate_loss_hop": loss_candidate,
        "candidate_jitter_hop": jitter_candidate,
        "observations": observations,
        "caution": (
            "Perda em um hop intermediário isolado pode ser limitação/depriorização de ICMP. "
            "NexuFlow só destaca padrões que persistem e nunca altera rotas automaticamente com base apenas neste diagnóstico."
        ),
    }


def trace_route(
    target: str = "1.1.1.1",
    *,
    max_hops: int = 20,
    probes_per_hop: int = 3,
    timeout_ms: int = 650,
    echo: Callable[..., dict] = icmp_echo_detail,
) -> dict:
    try:
        ipaddress.IPv4Address(target)
    except ipaddress.AddressValueError as exc:
        raise ValueError("Route diagnostics currently accepts a literal IPv4 target") from exc

    if os.name != "nt" and echo is icmp_echo_detail:
        return {
            "target": target,
            "hops": [],
            "analysis": {
                "candidate_degradation_hop": None,
                "observations": ["Diagnóstico de rota detalhado disponível no Windows."],
                "caution": "Read-only diagnostic.",
            },
        }

    hops: list[dict] = []
    for ttl in range(1, max(1, min(64, int(max_hops))) + 1):
        probes = [echo(target, timeout_ms, 16, False, ttl) for _ in range(max(1, min(5, int(probes_per_hop))))]
        hop = _hop_summary(ttl, probes)
        hops.append(hop)
        reached = any(
            p.get("status") == IP_SUCCESS and p.get("address") == target
            for p in probes
        )
        if reached:
            break

    return {
        "target": target,
        "hops": hops,
        "analysis": analyze_route_hops(hops),
        "read_only": True,
        "anti_cheat_safe": True,
    }
