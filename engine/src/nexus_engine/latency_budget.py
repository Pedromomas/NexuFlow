from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = 1
RULES_VERSION = "2026.09.01"

_CONFIDENCE_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
_SEVERITY_ORDER = {"unknown": 0, "ok": 1, "warning": 2, "critical": 3}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any, *, minimum: float | None = 0.0) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or (minimum is not None and parsed < minimum):
        return None
    return parsed


def _first_number(source: Mapping[str, Any], *names: str) -> float | None:
    for name in names:
        parsed = _number(source.get(name))
        if parsed is not None:
            return parsed
    return None


def _max_confidence(left: str, right: str) -> str:
    return left if _CONFIDENCE_ORDER[left] >= _CONFIDENCE_ORDER[right] else right


def _min_confidence(left: str, right: str) -> str:
    return left if _CONFIDENCE_ORDER[left] <= _CONFIDENCE_ORDER[right] else right


def _max_severity(left: str, right: str) -> str:
    return left if _SEVERITY_ORDER[left] >= _SEVERITY_ORDER[right] else right


def _domain(
    *,
    status: str,
    severity: str,
    confidence: str,
    evidence: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "severity": severity,
        "confidence": confidence,
        "evidence": evidence or [],
        "limitations": limitations or [],
    }


def _quality_confidence(quality: Mapping[str, Any]) -> str:
    sample_count = _number(quality.get("sample_count")) or 0.0
    span_seconds = _number(quality.get("span_seconds")) or 0.0
    has_measurement = any(
        _number(quality.get(key)) is not None
        for key in ("latency_ms", "jitter_ms", "packet_loss_percent")
    )
    if bool(quality.get("complete_window")) or (sample_count >= 15 and span_seconds >= 18):
        return "high"
    if sample_count >= 5:
        return "medium"
    if sample_count >= 1 or has_measurement:
        return "low"
    return "none"


def _route_candidate(route: Mapping[str, Any]) -> int | None:
    analysis = _mapping(route.get("analysis"))
    for name in (
        "candidate_degradation_hop",
        "candidate_latency_hop",
        "candidate_loss_hop",
        "candidate_jitter_hop",
    ):
        value = _number(analysis.get(name), minimum=1.0)
        if value is not None:
            return int(value)
    return None


def _connection_domain(
    quality: Mapping[str, Any],
    route: Mapping[str, Any],
) -> tuple[dict[str, Any], int]:
    confidence = _quality_confidence(quality)
    latency = _number(quality.get("latency_ms"))
    jitter = _number(quality.get("jitter_ms"))
    loss = _number(quality.get("packet_loss_percent"))
    target = str(quality.get("target") or "alvo neutro")
    evidence: list[str] = []
    limitations = [
        "A medição usa um alvo de referência e não representa necessariamente a rota do servidor do jogo.",
        "Latência, jitter e perda ponta a ponta não separam sozinhos Wi-Fi/LAN, roteador e provedor.",
    ]
    severity = "ok"
    signal_score = 0

    if loss is not None:
        if loss >= 5.0:
            severity = "critical"
            signal_score = max(signal_score, 30)
            evidence.append(f"Perda de {loss:.2f}% foi observada até {target}.")
        elif loss >= 1.0:
            severity = _max_severity(severity, "warning")
            signal_score = max(signal_score, 20)
            evidence.append(f"Perda de {loss:.2f}% foi observada até {target}.")
        elif loss > 0.0:
            evidence.append(f"Perda residual de {loss:.2f}% apareceu na janela medida.")

    if jitter is not None:
        if jitter >= 30.0:
            severity = "critical"
            signal_score = max(signal_score, 30)
            evidence.append(f"Jitter elevado de {jitter:.2f} ms foi medido.")
        elif jitter >= 10.0:
            severity = _max_severity(severity, "warning")
            signal_score = max(signal_score, 20)
            evidence.append(f"Jitter elevado de {jitter:.2f} ms foi medido.")

    # High RTT to a neutral target is worth showing, but geography and target
    # selection prevent it from proving a local or ISP fault.
    if latency is not None and latency >= 150.0:
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 15)
        evidence.append(f"RTT de {latency:.2f} ms foi medido até {target}.")
        limitations.append("RTT alto isolado pode refletir distância geográfica do alvo.")

    candidate = _route_candidate(route)
    if candidate == 1:
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 22)
        evidence.append("O diagnóstico de rota encontrou degradação persistente já no primeiro hop responsivo.")
        limitations.append("O primeiro hop não identifica sozinho se a origem é Wi-Fi, cabo, roteador ou acesso do provedor.")

    if signal_score:
        if confidence == "none":
            confidence = "low"
        return _domain(
            status="degradation_observed",
            severity=severity,
            confidence=confidence,
            evidence=evidence,
            limitations=limitations,
        ), signal_score

    if confidence in {"none", "low"}:
        return _domain(
            status="insufficient_data",
            severity="unknown",
            confidence=confidence,
            evidence=evidence,
            limitations=limitations + ["A janela é curta demais para declarar a conexão estável."],
        ), 0

    evidence.append("A janela medida não mostrou perda, jitter elevado ou RTT extremamente alto.")
    return _domain(
        status="no_issue_observed",
        severity="ok",
        confidence=confidence,
        evidence=evidence,
        limitations=limitations,
    ), 0


def _route_domain(route: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    analysis = _mapping(route.get("analysis"))
    hops = [item for item in (route.get("hops") or []) if isinstance(item, Mapping)]
    responsive = [hop for hop in hops if _number(hop.get("median_ms")) is not None]
    candidate = _route_candidate(route)
    limitations = [
        "Roteadores intermediários podem limitar ou depriorizar ICMP.",
        "O hop observado não comprova qual empresa, enlace ou equipamento causou a degradação.",
    ]

    if not analysis and not responsive:
        return _domain(
            status="insufficient_data",
            severity="unknown",
            confidence="none",
            limitations=limitations,
        ), 0

    target = str(route.get("target") or "")
    destination = responsive[-1] if responsive else {}
    reached_destination = bool(target and str(destination.get("address") or "") == target)
    destination_loss = _number(destination.get("loss_percent"))
    destination_jitter = _number(destination.get("jitter_ms"))

    if candidate is not None and candidate > 1:
        severity = "warning"
        if (destination_loss is not None and destination_loss >= 5.0) or (
            destination_jitter is not None and destination_jitter >= 30.0
        ):
            severity = "critical"
        confidence = "medium" if reached_destination and len(responsive) >= 3 else "low"
        evidence = [f"Uma degradação que persiste em hops posteriores começa por volta do hop {candidate}."]
        if reached_destination:
            evidence.append("O padrão também alcançou o destino do diagnóstico.")
        else:
            limitations.append("O destino não respondeu de forma suficiente para corroborar o padrão ponta a ponta.")
        return _domain(
            status="degradation_observed",
            severity=severity,
            confidence=confidence,
            evidence=evidence,
            limitations=limitations,
        ), 32 if severity == "critical" else 22

    if candidate == 1:
        return _domain(
            status="indeterminate",
            severity="unknown",
            confidence="low",
            evidence=["A degradação começa no primeiro hop responsivo, sem localização segura entre rede local e acesso."],
            limitations=limitations,
        ), 0

    if reached_destination and len(responsive) >= 2:
        return _domain(
            status="no_issue_observed",
            severity="ok",
            confidence="medium",
            evidence=["Nenhuma degradação persistente foi localizada até o destino nesta amostra."],
            limitations=limitations,
        ), 0

    return _domain(
        status="insufficient_data",
        severity="unknown",
        confidence="low" if responsive else "none",
        limitations=limitations + ["A rota não respondeu o bastante para localizar uma degradação."],
    ), 0


def _pc_domain(
    gaming_health: Mapping[str, Any],
    stutter: Mapping[str, Any],
) -> tuple[dict[str, Any], int]:
    cpu = _mapping(gaming_health.get("cpu"))
    memory = _mapping(gaming_health.get("memory"))
    gpu = _mapping(gaming_health.get("gpu"))
    evidence: list[str] = []
    limitations = [
        "Uso de CPU/GPU e pressão de memória são correlações; sem frametime não provam a causa da travada.",
        "DPC/ISR elevado indica pressão no kernel, mas não identifica um driver específico sem uma análise ETW válida.",
    ]
    severity = "ok"
    signal_score = 0
    signals = 0
    measurements = 0

    cpu_percent = _first_number(cpu, "utilization_percent", "percent")
    if cpu_percent is not None:
        measurements += 1
        if cpu_percent >= 98.0:
            severity = "critical"
            signal_score = max(signal_score, 30)
            signals += 1
            evidence.append(f"CPU permaneceu próxima da saturação ({cpu_percent:.1f}%).")
        elif cpu_percent >= 90.0:
            severity = _max_severity(severity, "warning")
            signal_score = max(signal_score, 20)
            signals += 1
            evidence.append(f"Uso elevado de CPU foi observado ({cpu_percent:.1f}%).")

    if bool(cpu.get("possible_clock_constraint")):
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 22)
        signals += 1
        evidence.append("CPU sob carga apresentou clock agregado abaixo do esperado.")

    memory_percent = _first_number(memory, "percent", "utilization_percent")
    available_gb = _number(memory.get("available_gb"))
    if memory_percent is not None or available_gb is not None:
        measurements += 1
    if (memory_percent is not None and memory_percent >= 95.0) or (
        available_gb is not None and available_gb < 1.0
    ):
        severity = "critical"
        signal_score = max(signal_score, 30)
        signals += 1
        evidence.append("A memória disponível ficou em nível crítico na amostra.")
    elif (memory_percent is not None and memory_percent >= 88.0) or (
        available_gb is not None and available_gb < 2.0
    ):
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 20)
        signals += 1
        evidence.append("A amostra mostrou pressão de memória.")

    gpu_utilization = _first_number(gpu, "utilization", "utilization_percent")
    gpu_temperature = _first_number(gpu, "temperature_c", "temperature")
    if gpu_utilization is not None or gpu_temperature is not None:
        measurements += 1
    if gpu_temperature is not None and gpu_temperature >= 90.0:
        severity = "critical"
        signal_score = max(signal_score, 30)
        signals += 1
        evidence.append(f"Temperatura de GPU muito alta foi observada ({gpu_temperature:.0f} °C).")
    elif gpu_temperature is not None and gpu_temperature >= 85.0:
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 20)
        signals += 1
        evidence.append(f"Temperatura elevada de GPU foi observada ({gpu_temperature:.0f} °C).")
    if gpu_utilization is not None and gpu_utilization >= 99.0:
        evidence.append(f"A GPU ficou totalmente ocupada na amostra ({gpu_utilization:.0f}%).")
        limitations.append("GPU em 99–100% pode ser comportamento normal de um jogo sem limite de FPS.")
        signal_score = max(signal_score, 14)

    dpc = _mapping(stutter.get("dpc"))
    interrupt = _mapping(stutter.get("interrupt"))
    dpc_percent = _first_number(stutter, "dpc_percent", "processor_dpc_percent")
    if dpc_percent is None:
        dpc_percent = _first_number(dpc, "percent", "utilization_percent")
    interrupt_percent = _first_number(stutter, "interrupt_percent", "processor_interrupt_percent")
    if interrupt_percent is None:
        interrupt_percent = _first_number(interrupt, "percent", "utilization_percent")
    max_dpc_us = _first_number(stutter, "max_dpc_us", "dpc_max_us")
    if max_dpc_us is None:
        max_dpc_us = _first_number(dpc, "max_us", "maximum_us")
    max_isr_us = _first_number(stutter, "max_isr_us", "isr_max_us")
    if max_isr_us is None:
        max_isr_us = _first_number(interrupt, "max_us", "maximum_us")
    events_lost = _first_number(stutter, "events_lost") or 0.0

    if any(value is not None for value in (dpc_percent, interrupt_percent, max_dpc_us, max_isr_us)):
        measurements += 1
    if dpc_percent is not None and dpc_percent >= 15.0:
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 24)
        signals += 1
        evidence.append(f"Tempo de DPC elevado foi medido ({dpc_percent:.1f}%).")
    if interrupt_percent is not None and interrupt_percent >= 30.0:
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 24)
        signals += 1
        evidence.append(f"Tempo de interrupção elevado foi medido ({interrupt_percent:.1f}%).")
    if max_dpc_us is not None and max_dpc_us >= 100.0:
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 22)
        signals += 1
        evidence.append(f"Foi observado pico de DPC de {max_dpc_us:.0f} µs.")
    if max_isr_us is not None and max_isr_us >= 25.0:
        severity = _max_severity(severity, "warning")
        signal_score = max(signal_score, 22)
        signals += 1
        evidence.append(f"Foi observado pico de ISR de {max_isr_us:.0f} µs.")

    if signal_score:
        confidence = "medium" if signals >= 2 or severity == "critical" else "low"
        if events_lost > 0:
            confidence = "low"
            limitations.append("A captura perdeu eventos; a confiança do diagnóstico foi reduzida.")
        return _domain(
            status="pressure_observed",
            severity=severity,
            confidence=confidence,
            evidence=evidence,
            limitations=limitations,
        ), signal_score

    if measurements < 2:
        return _domain(
            status="insufficient_data",
            severity="unknown",
            confidence="none" if measurements == 0 else "low",
            evidence=evidence,
            limitations=limitations,
        ), 0

    evidence.append("As métricas fornecidas não mostraram pressão evidente de CPU, memória, temperatura ou DPC/ISR.")
    return _domain(
        status="no_issue_observed",
        severity="ok",
        confidence="medium",
        evidence=evidence,
        limitations=limitations,
    ), 0


def _server_domain(*, symptom_reported: bool, other_signal: bool) -> dict[str, Any]:
    evidence: list[str] = []
    if symptom_reported and not other_signal:
        evidence.append(
            "O sintoma informado não foi explicado pelas métricas locais e de referência fornecidas; "
            "servidor ou rota específica do jogo continuam apenas como hipóteses."
        )
    return _domain(
        status="indeterminate",
        severity="unknown",
        confidence="none",
        evidence=evidence,
        limitations=[
            "NexuFlow não mede o tempo de processamento do servidor do jogo.",
            "Um alvo neutro não representa necessariamente a região, a fila ou a rota do servidor do jogo.",
            "Esta área nunca é marcada como causa por exclusão.",
        ],
    )


def _verdict(
    domains: Mapping[str, Mapping[str, Any]],
    scores: Mapping[str, int],
    *,
    symptom_reported: bool,
) -> dict[str, Any]:
    positive = {key: value for key, value in scores.items() if value > 0}
    if not positive:
        if symptom_reported:
            return {
                "primary_area": "inconclusive",
                "supporting_areas": [],
                "confidence": "none",
                "summary": "As métricas fornecidas não explicam o sintoma com evidência suficiente.",
                "causality": "not_established",
            }
        return {
            "primary_area": "no_issue_observed",
            "supporting_areas": [],
            "confidence": "none",
            "summary": "Nenhum sinal forte foi encontrado, mas isso não garante ausência de problema.",
            "causality": "not_established",
        }

    ordered = sorted(positive, key=lambda key: positive[key], reverse=True)
    strongest_score = positive[ordered[0]]
    strongest = [key for key in ordered if positive[key] == strongest_score]

    # Connection degradation corroborated and localized after the first hop is
    # one evidence chain, not two independent causes. Prefer the more specific
    # route label and retain connection as supporting evidence.
    if "route_or_isp" in strongest and "connection_or_local_network" in strongest:
        strongest.remove("connection_or_local_network")

    if len(strongest) > 1:
        confidence = "low"
        return {
            "primary_area": "multiple_signals",
            "supporting_areas": ordered,
            "confidence": confidence,
            "summary": "Há sinais relevantes em mais de uma área; os dados não isolam uma única origem.",
            "causality": "not_established",
        }

    primary = strongest[0]
    confidence = str(domains[primary].get("confidence") or "none")
    supporting = [key for key in ordered if key != primary]
    labels = {
        "connection_or_local_network": "conexão/caminho de rede",
        "route_or_isp": "rota além do primeiro hop",
        "pc_or_driver_pressure": "pressão do PC/kernel",
    }
    return {
        "primary_area": primary,
        "supporting_areas": supporting,
        "confidence": confidence,
        "summary": (
            f"Os sinais mais fortes aparecem em {labels[primary]}. "
            "Isto é uma classificação por evidências, não uma prova de causalidade."
        ),
        "causality": "not_established",
    }


def classify_latency_budget(
    *,
    quality: Mapping[str, Any] | None = None,
    route: Mapping[str, Any] | None = None,
    gaming_health: Mapping[str, Any] | None = None,
    stutter: Mapping[str, Any] | None = None,
    symptom_reported: bool = False,
) -> dict[str, Any]:
    """Classify supplied latency evidence without manufacturing a total delay.

    The function is deliberately pure: it performs no probing, process access,
    tracing or system mutation. Confidence describes how well the supplied
    evidence supports an *observed signal*, never certainty that the signal
    caused a player's symptom.
    """

    quality_map = _mapping(quality)
    route_map = _mapping(route)
    health_map = _mapping(gaming_health)
    stutter_map = _mapping(stutter)

    connection, connection_score = _connection_domain(quality_map, route_map)
    route_result, route_score = _route_domain(route_map)
    pc, pc_score = _pc_domain(health_map, stutter_map)
    scores = {
        "connection_or_local_network": connection_score,
        "route_or_isp": route_score,
        "pc_or_driver_pressure": pc_score,
    }
    other_signal = any(value > 0 for value in scores.values())
    domains = {
        "connection_or_local_network": connection,
        "route_or_isp": route_result,
        "pc_or_driver_pressure": pc,
        "server_or_game_specific": _server_domain(
            symptom_reported=bool(symptom_reported),
            other_signal=other_signal,
        ),
    }

    return {
        "schema": SCHEMA_VERSION,
        "rules_version": RULES_VERSION,
        "methodology": "evidence_based_non_additive",
        "verdict": _verdict(domains, scores, symptom_reported=bool(symptom_reported)),
        "domains": domains,
        "limitations": [
            "Não existe soma ou orçamento total em milissegundos porque rede, frametime, input e servidor não foram medidos na mesma base.",
            "Nenhuma área é declarada causa; o resultado aponta somente sinais observados e próximos testes seguros.",
            "O módulo não lê memória, sockets ou arquivos do jogo e não interage com o anticheat.",
        ],
        "next_checks": {
            "connection_or_local_network": [
                "Repetir a medição com janela completa e, se possível, comparar Ethernet e Wi-Fi.",
                "Comparar primeiro hop e alvo neutro para separar acesso local de caminho externo.",
            ],
            "route_or_isp": [
                "Repetir em outro horário ou conexão; um único traceroute não confirma responsabilidade do provedor.",
            ],
            "pc_or_driver_pressure": [
                "Correlacionar a janela com frametime e usar ETW somente fora de sessão protegida para localizar driver.",
            ],
            "server_or_game_specific": [
                "Comparar região e status oficial do jogo; servidor continua indeterminado sem telemetria própria.",
            ],
        },
    }


__all__ = ["classify_latency_budget"]
