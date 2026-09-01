from pathlib import Path

from nexus_engine.history import SessionHistory


def test_session_history_deduplicates_session_id(tmp_path: Path):
    history = SessionHistory(tmp_path / "history.json")
    state = {
        "session_id": "abc",
        "game": {"id": "roblox", "display_name": "Roblox"},
        "started_at": 10.0,
        "profile": "roblox",
        "requested_profile": "auto",
        "quality_before": {"latency_ms": 40.0, "jitter_ms": 5.0, "packet_loss_percent": 1.0, "nexus_score": 80},
        "quality_after": {"latency_ms": 30.0, "jitter_ms": 2.0, "packet_loss_percent": 0.0, "nexus_score": 95},
    }
    history.record_state(state, ended_at=20.0)
    history.record_state(state, ended_at=21.0)
    items = history.list()
    assert len(items) == 1
    assert items[0]["quality_delta"]["latency_ms"] == -10.0
    assert items[0]["fps_average"] is None
