from nexus_engine.network.route_diagnostics import analyze_route_hops, trace_route


def test_route_analysis_marks_persistent_latency_jump():
    hops = [
        {"hop": 1, "address": "192.168.1.1", "median_ms": 1.0, "jitter_ms": 0.2, "loss_percent": 0.0},
        {"hop": 2, "address": "10.0.0.1", "median_ms": 5.0, "jitter_ms": 0.3, "loss_percent": 0.0},
        {"hop": 3, "address": "203.0.113.1", "median_ms": 31.0, "jitter_ms": 2.0, "loss_percent": 0.0},
        {"hop": 4, "address": "1.1.1.1", "median_ms": 34.0, "jitter_ms": 2.0, "loss_percent": 0.0},
    ]
    result = analyze_route_hops(hops)
    assert result["candidate_degradation_hop"] == 3


def test_trace_route_is_read_only_with_mock_echo():
    def echo(target, timeout, payload, df, ttl):
        if ttl == 1:
            return {"address": "192.168.0.1", "latency_ms": 1.0, "status": 11013, "ttl": ttl}
        return {"address": target, "latency_ms": 20.0, "status": 0, "ttl": ttl}

    result = trace_route("1.1.1.1", max_hops=5, probes_per_hop=2, echo=echo)
    assert result["read_only"] is True
    assert result["anti_cheat_safe"] is True
    assert len(result["hops"]) == 2


def test_route_analysis_ignores_non_persistent_latency_spike():
    hops = [
        {"hop": 1, "address": "10.0.0.1", "median_ms": 1.0, "jitter_ms": 0.2, "loss_percent": 0.0},
        {"hop": 2, "address": "10.0.0.2", "median_ms": 45.0, "jitter_ms": 0.2, "loss_percent": 0.0},
        {"hop": 3, "address": "10.0.0.3", "median_ms": 5.0, "jitter_ms": 0.3, "loss_percent": 0.0},
        {"hop": 4, "address": "1.1.1.1", "median_ms": 6.0, "jitter_ms": 0.3, "loss_percent": 0.0},
    ]
    result = analyze_route_hops(hops)
    assert result["candidate_latency_hop"] is None


def test_route_analysis_can_localize_persistent_loss_and_jitter():
    hops = [
        {"hop": 1, "address": "10.0.0.1", "median_ms": 1.0, "jitter_ms": 0.2, "loss_percent": 0.0},
        {"hop": 2, "address": "10.0.0.2", "median_ms": 5.0, "jitter_ms": 9.0, "loss_percent": 5.0},
        {"hop": 3, "address": "10.0.0.3", "median_ms": 7.0, "jitter_ms": 10.0, "loss_percent": 5.0},
        {"hop": 4, "address": "1.1.1.1", "median_ms": 8.0, "jitter_ms": 12.0, "loss_percent": 5.0},
    ]
    result = analyze_route_hops(hops)
    assert result["candidate_loss_hop"] == 2
    assert result["candidate_jitter_hop"] == 2
