from types import SimpleNamespace

import pytest
import json

from nexus_engine import orchestrator
from nexus_engine import daemon
from nexus_engine import __main__ as cli
from nexus_engine.models import BoostProfile


class _StateStore:
    def __init__(self):
        self.saved = []

    def load(self):
        return {}

    def save(self, value):
        self.saved.append(value)


def test_stop_timeout_never_starts_a_second_rollback(monkeypatch):
    monkeypatch.setattr(daemon, 'request_stop', lambda: None)
    monkeypatch.setattr(daemon, 'daemon_is_running', lambda: True)
    monkeypatch.setattr(daemon, 'NexusOrchestrator', lambda: pytest.fail('Concurrent rollback is forbidden'))
    result = daemon.stop_daemon(wait_seconds=0)
    assert result['stopped'] is False
    assert result['restore_pending'] is True


@pytest.mark.parametrize('active', [False, True])
def test_stopped_daemon_reports_actual_pending_snapshot(monkeypatch, active):
    monkeypatch.setattr(daemon, 'request_stop', lambda: None)
    monkeypatch.setattr(daemon, 'daemon_is_running', lambda: False)
    monkeypatch.setattr(daemon, 'NexusOrchestrator', lambda: SimpleNamespace(restore_all=lambda: {'restored': False}))
    monkeypatch.setattr(daemon, 'StateStore', lambda: SimpleNamespace(load=lambda: {'active': active}))
    assert daemon.stop_daemon()['restore_pending'] is active


@pytest.mark.parametrize('stopped,pending,ok', [(True, False, True), (True, True, False), (False, True, False)])
def test_privileged_restore_does_not_claim_false_success(monkeypatch, tmp_path, stopped, pending, ok):
    request = tmp_path / 'request.json'
    result = tmp_path / 'result.json'
    request.write_text(json.dumps({'schema': 1, 'requested_by': 'tauri', 'action': 'restore'}), encoding='utf-8')
    monkeypatch.setattr(cli, '_validate_job_paths', lambda *_: None)
    monkeypatch.setattr(cli.os, 'name', 'nt')
    monkeypatch.setattr(cli, 'is_admin', lambda: True)
    monkeypatch.setattr(cli, 'stop_daemon', lambda: {'stopped': stopped, 'restore_pending': pending})
    cli._handle_job(request, result)
    assert json.loads(result.read_text(encoding='utf-8'))['ok'] is ok


@pytest.mark.parametrize('reported_success', [False, True])
def test_unrestored_snapshot_blocks_new_boost_without_overwriting(monkeypatch, reported_success):
    engine = orchestrator.NexusOrchestrator.__new__(orchestrator.NexusOrchestrator)
    store = _StateStore()
    store.load = lambda: {'active': True, 'session_id': 'original'}
    engine.state_store = store
    engine.restore_all = lambda: {'restored': reported_success}
    monkeypatch.setattr(orchestrator.os, 'name', 'nt')
    monkeypatch.setattr(orchestrator, 'effective_profile', lambda *_: BoostProfile.SAFE)
    monkeypatch.setattr(orchestrator, 'boost_objective', lambda *_: 'pc')
    with pytest.raises(RuntimeError, match='Rollback incompleto'):
        engine.optimize_game({'id': 'test', 'running': True, 'pid': 123, 'executable': 'game.exe'}, BoostProfile.PC)
    assert store.saved == []


@pytest.mark.parametrize('reported_success', [False, True])
def test_daemon_does_not_report_ready_when_recovery_leaves_active_state(monkeypatch, tmp_path, reported_success):
    responses = []
    stopped = []
    monkeypatch.setattr(daemon, 'daemon_is_running', lambda: False)
    monkeypatch.setattr(daemon, 'pending_manual_state', lambda: [])
    monkeypatch.setattr(daemon, 'stop_file', lambda: tmp_path / 'stop')
    monkeypatch.setattr(daemon.GameCatalog, 'load', lambda: object())
    monkeypatch.setattr(daemon, 'NexusOrchestrator', lambda: SimpleNamespace(
        state_store=SimpleNamespace(load=lambda: {'active': True}),
        restore_all=lambda: {'restored': reported_success}))
    monkeypatch.setattr(daemon, 'QualityStore', lambda: SimpleNamespace(is_fresh=lambda _: True))
    monkeypatch.setattr(daemon, 'NetworkQualityMonitor', lambda **_: SimpleNamespace(stop=lambda: stopped.append(True)))
    monkeypatch.setattr(daemon, '_write_daemon', lambda _: pytest.fail('Must not publish a ready daemon'))
    daemon.run_daemon(BoostProfile.PC, responses.append)
    assert len(responses) == 1
    assert responses[0]['ok'] is False
    assert 'Rollback pendente' in responses[0]['message']
    assert stopped == [True]


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
