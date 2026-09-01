from pathlib import Path

from nexus_engine.network.quality import QualityStore, nexus_score, quality_delta, summarize_samples


def test_loss_is_penalized_more_than_small_latency_difference():
    lossy = nexus_score(18.0, 1.0, 8.0)
    stable = nexus_score(28.0, 1.0, 0.0)
    assert stable > lossy


def test_quality_summary_calculates_latency_jitter_loss():
    samples = [
        {"timestamp": 0.0, "target": "1.1.1.1", "latency_ms": 20.0},
        {"timestamp": 1.0, "target": "1.1.1.1", "latency_ms": 22.0},
        {"timestamp": 2.0, "target": "1.1.1.1", "latency_ms": None},
        {"timestamp": 3.0, "target": "1.1.1.1", "latency_ms": 21.0},
    ]
    result = summarize_samples(samples)
    assert result["latency_ms"] == 21.0
    assert result["packet_loss_percent"] == 25.0
    assert result["jitter_ms"] == 1.5


def test_quality_store_window_and_delta(tmp_path: Path):
    store = QualityStore(tmp_path / "quality.json")
    for i in range(25):
        store.append({"timestamp": float(i), "target": "1.1.1.1", "latency_ms": 30.0})
    before = store.snapshot(25, end_ts=24.0)
    after = dict(before)
    after["latency_ms"] = 25.0
    after["nexus_score"] = max(0, int(before["nexus_score"]) - 5)
    delta = quality_delta(before, after)
    assert before["complete_window"] is True
    assert delta["latency_ms"] == -5.0
    assert delta["nexus_score"] == -5.0


def test_quality_snapshot_never_mixes_probe_targets(tmp_path: Path):
    store = QualityStore(tmp_path / "quality.json")
    store.append({"timestamp": 10.0, "target": "1.1.1.1", "latency_ms": 10.0})
    store.append({"timestamp": 11.0, "target": "1.1.1.1", "latency_ms": 11.0})
    store.append({"timestamp": 12.0, "target": "8.8.8.8", "latency_ms": 50.0})
    store.append({"timestamp": 13.0, "target": "8.8.8.8", "latency_ms": 52.0})
    result = store.snapshot(10.0, end_ts=13.0)
    assert result["target"] == "8.8.8.8"
    assert result["sample_count"] == 2
    assert result["latency_ms"] == 51.0


def test_monitor_reuses_fresh_shared_target(tmp_path: Path, monkeypatch):
    from nexus_engine.network.quality import NetworkQualityMonitor

    store = QualityStore(tmp_path / "quality.json")
    store.append({"timestamp": __import__("time").time(), "target": "9.9.9.9", "latency_ms": 20.0})
    monitor = NetworkQualityMonitor(store=store)
    # If reuse works, candidate probing should not be needed.
    monkeypatch.setattr("nexus_engine.network.quality.icmp_echo_ipv4", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected probe")))
    assert monitor.select_target(reuse_fresh=True) == "9.9.9.9"
