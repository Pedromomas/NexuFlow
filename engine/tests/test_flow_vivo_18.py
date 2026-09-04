from types import SimpleNamespace

import pytest

from nexus_engine import orchestrator
from nexus_engine.models import BoostProfile


class _StateStore:
    def __init__(self):
        self.saved = []

    def load(self):
        return {}

    def save(self, value):
        self.saved.append(value)


def test_stop_during_baseline_cancels_before_any_snapshot_or_mutation(monkeypatch):
    engine = orchestrator.NexusOrchestrator.__new__(orchestrator.NexusOrchestrator)
    engine.state_store = _StateStore()
    engine.quality_store = SimpleNamespace(snapshot=lambda _seconds: {"complete_window": False, "sample_count": 0})

    monkeypatch.setattr(orchestrator.os, "name", "nt")
    monkeypatch.setattr(orchestrator, "effective_profile", lambda _requested, _game_id: BoostProfile.SAFE)
    monkeypatch.setattr(orchestrator, "boost_objective", lambda _requested: "pc")
    monkeypatch.setattr(orchestrator, "pending_manual_state", lambda: [])
    monkeypatch.setattr(orchestrator, "anti_cheat_policy_report", lambda *_args: {})
    monkeypatch.setattr(orchestrator, "stop_file", lambda: SimpleNamespace(exists=lambda: True))

    game = {"id": "test", "display_name": "Teste", "running": True, "pid": 123, "executable": "game.exe"}
    with pytest.raises(RuntimeError, match="cancelada antes de qualquer alteração"):
        engine.optimize_game(game, BoostProfile.PC)

    assert engine.state_store.saved == []
