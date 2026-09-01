import math

from nexus_engine.latency_budget import classify_latency_budget


def _quality(**overrides):
    value = {
        "target": "1.1.1.1",
        "sample_count": 30,
        "span_seconds": 29.0,
        "complete_window": True,
        "latency_ms": 24.0,
        "jitter_ms": 1.2,
        "packet_loss_percent": 0.0,
    }
    value.update(overrides)
    return value


def _healthy_pc():
    return {
        "cpu": {"utilization_percent": 42.0, "possible_clock_constraint": False},
        "memory": {"percent": 55.0, "available_gb": 8.0},
        "gpu": {"utilization": 70.0, "temperature_c": 68.0},
    }


def _clean_route():
    return {
        "target": "1.1.1.1",
        "hops": [
            {"hop": 1, "address": "192.168.1.1", "median_ms": 1.0, "loss_percent": 0.0},
            {"hop": 2, "address": "1.1.1.1", "median_ms": 24.0, "loss_percent": 0.0},
        ],
        "analysis": {"candidate_degradation_hop": None},
    }


def test_stable_measurements_do_not_claim_a_cause_or_server_fault():
    result = classify_latency_budget(
        quality=_quality(),
        route=_clean_route(),
        gaming_health=_healthy_pc(),
    )

    assert result["verdict"]["primary_area"] == "no_issue_observed"
    assert result["verdict"]["causality"] == "not_established"
    assert result["domains"]["connection_or_local_network"]["status"] == "no_issue_observed"
    assert result["domains"]["server_or_game_specific"]["status"] == "indeterminate"
    assert result["domains"]["server_or_game_specific"]["confidence"] == "none"


def test_loss_and_jitter_classify_connection_evidence_with_complete_window():
    result = classify_latency_budget(
        quality=_quality(jitter_ms=18.0, packet_loss_percent=3.0),
        gaming_health=_healthy_pc(),
    )

    connection = result["domains"]["connection_or_local_network"]
    assert connection["status"] == "degradation_observed"
    assert connection["confidence"] == "high"
    assert result["verdict"]["primary_area"] == "connection_or_local_network"
    assert result["verdict"]["causality"] == "not_established"


def test_persistent_route_signal_after_gateway_is_not_called_a_proven_isp_fault():
    route = {
        "target": "1.1.1.1",
        "hops": [
            {"hop": 1, "address": "192.168.1.1", "median_ms": 1.0, "loss_percent": 0.0},
            {"hop": 2, "address": "10.0.0.1", "median_ms": 28.0, "loss_percent": 0.0},
            {"hop": 3, "address": "1.1.1.1", "median_ms": 31.0, "loss_percent": 0.0},
        ],
        "analysis": {"candidate_degradation_hop": 2},
    }
    result = classify_latency_budget(
        quality=_quality(latency_ms=31.0),
        route=route,
        gaming_health=_healthy_pc(),
    )

    route_result = result["domains"]["route_or_isp"]
    assert route_result["status"] == "degradation_observed"
    assert route_result["confidence"] == "medium"
    assert result["verdict"]["primary_area"] == "route_or_isp"
    assert any("não comprova" in item for item in route_result["limitations"])


def test_first_hop_signal_stays_ambiguous_between_lan_and_access():
    route = {
        "target": "1.1.1.1",
        "hops": [
            {"hop": 1, "address": "192.168.1.1", "median_ms": 30.0, "loss_percent": 5.0},
            {"hop": 2, "address": "1.1.1.1", "median_ms": 35.0, "loss_percent": 5.0},
        ],
        "analysis": {"candidate_degradation_hop": 1},
    }
    result = classify_latency_budget(quality=_quality(), route=route, gaming_health=_healthy_pc())

    assert result["domains"]["connection_or_local_network"]["status"] == "degradation_observed"
    assert result["domains"]["route_or_isp"]["status"] == "indeterminate"
    assert result["verdict"]["primary_area"] == "connection_or_local_network"


def test_pc_pressure_wins_when_network_is_stable():
    health = {
        "cpu": {"utilization_percent": 96.0, "possible_clock_constraint": True},
        "memory": {"percent": 94.0, "available_gb": 1.2},
        "gpu": {"utilization": 83.0, "temperature_c": 72.0},
    }
    result = classify_latency_budget(
        quality=_quality(),
        route=_clean_route(),
        gaming_health=health,
    )

    pc = result["domains"]["pc_or_driver_pressure"]
    assert pc["status"] == "pressure_observed"
    assert pc["confidence"] == "medium"
    assert result["verdict"]["primary_area"] == "pc_or_driver_pressure"
    assert result["verdict"]["causality"] == "not_established"


def test_server_remains_indeterminate_when_user_reports_lag_but_metrics_are_clean():
    result = classify_latency_budget(
        quality=_quality(),
        route=_clean_route(),
        gaming_health=_healthy_pc(),
        symptom_reported=True,
    )

    assert result["verdict"]["primary_area"] == "inconclusive"
    assert result["verdict"]["confidence"] == "none"
    server = result["domains"]["server_or_game_specific"]
    assert server["status"] == "indeterminate"
    assert server["confidence"] == "none"
    assert any("hipóteses" in item for item in server["evidence"])


def test_short_window_is_not_reported_as_a_healthy_connection():
    result = classify_latency_budget(
        quality=_quality(sample_count=2, span_seconds=1.0, complete_window=False),
        gaming_health={},
    )

    assert result["domains"]["connection_or_local_network"]["status"] == "insufficient_data"
    assert result["domains"]["connection_or_local_network"]["confidence"] == "low"
    assert result["domains"]["pc_or_driver_pressure"]["status"] == "insufficient_data"


def test_isolated_intermediate_loss_without_route_candidate_is_not_blamed():
    route = {
        "target": "1.1.1.1",
        "hops": [
            {"hop": 1, "address": "192.168.1.1", "median_ms": 1.0, "loss_percent": 0.0},
            {"hop": 2, "address": "10.0.0.1", "median_ms": 10.0, "loss_percent": 80.0},
            {"hop": 3, "address": "1.1.1.1", "median_ms": 22.0, "loss_percent": 0.0},
        ],
        "analysis": {"candidate_degradation_hop": None},
    }
    result = classify_latency_budget(quality=_quality(), route=route, gaming_health=_healthy_pc())

    assert result["domains"]["route_or_isp"]["status"] == "no_issue_observed"
    assert result["verdict"]["primary_area"] == "no_issue_observed"


def test_lost_stutter_events_reduce_confidence_and_never_name_a_driver_cause():
    result = classify_latency_budget(
        quality=_quality(),
        gaming_health=_healthy_pc(),
        stutter={"dpc_percent": 18.0, "max_dpc_us": 160.0, "events_lost": 12},
    )

    pc = result["domains"]["pc_or_driver_pressure"]
    assert pc["status"] == "pressure_observed"
    assert pc["confidence"] == "low"
    assert any("perdeu eventos" in item for item in pc["limitations"])
    assert result["verdict"]["causality"] == "not_established"


def test_invalid_numbers_are_ignored_and_no_additive_total_is_invented():
    result = classify_latency_budget(
        quality={
            "latency_ms": math.nan,
            "jitter_ms": math.inf,
            "packet_loss_percent": -2,
            "sample_count": 0,
        },
        gaming_health={"cpu": {"utilization_percent": "not-a-number"}},
    )

    assert result["domains"]["connection_or_local_network"]["status"] == "insufficient_data"
    assert result["methodology"] == "evidence_based_non_additive"
    assert "total_ms" not in result
    assert "latency_budget_ms" not in result
    assert any("Não existe soma" in item for item in result["limitations"])
