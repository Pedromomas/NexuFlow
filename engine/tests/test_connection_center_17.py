from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from nexus_engine.network import connection_center as center
from nexus_engine.network.dns import DNSScore
from nexus_engine import anti_cheat, discovery
from nexus_engine.catalog import GameCatalog
from nexus_engine.models import BoostProfile
from nexus_engine.hardware import pc_center


def test_empty_is_unknown_not_zero_ping_or_100_loss():
    result = center.connection_history(SimpleNamespace(load=lambda: {}), now=1000)
    assert result['stale']
    assert result['summary']['latency_ms'] is None
    assert result['summary']['packet_loss_percent'] is None
    assert result['summary']['nexus_score'] is None


def test_history_filters_corruption_and_separates_failovers():
    raw = [None, {}, {'timestamp': float('nan')},
           {'timestamp': 997, 'target': '1.1.1.1', 'latency_ms': 100},
           {'timestamp': 998, 'target': '8.8.8.8', 'latency_ms': 20},
           {'timestamp': 999, 'target': '1.1.1.1', 'latency_ms': 0},
           {'timestamp': 1000, 'target': '1.1.1.1', 'latency_ms': float('nan')},
           {'timestamp': 1001, 'target': '1.1.1.1', 'latency_ms': 12}]
    store = SimpleNamespace(load=lambda: {'samples': raw})
    r = center.connection_history(store, now=1000)
    assert len(r['samples']) == 2
    assert r['summary']['latency_ms'] == 0
    assert r['summary']['packet_loss_percent'] == 50
    assert not r['stale']
    assert center.connection_history(store, now=1008)['stale']


def test_percentiles_spikes_and_timeouts():
    r = center.describe_samples([{'timestamp': i, 'latency_ms': v} for i, v in enumerate([10, 20, 100, None])], '1.1.1.1')
    assert r['latency_ms'] == 20
    assert r['p95_ms'] == 100
    assert r['spikes'] == 1
    assert r['packet_loss_percent'] == 25


def test_scan_is_bounded_and_allowlisted(monkeypatch):
    calls = []
    def fake(ip, timeout_ms):
        calls.append((ip, timeout_ms)); return 10, 0
    monkeypatch.setattr(center, '_scan_lock', nullcontext)
    monkeypatch.setattr(center, 'icmp_echo_ipv4', fake)
    monkeypatch.setattr(center.time, 'sleep', lambda _: None)
    r = center.scan_connection()
    assert len(calls) == 36
    assert {ip for ip, _ in calls} == set(center.QUALITY_TARGETS)
    assert all(timeout == 600 for _, timeout in calls)
    assert 'estáveis' in r['conclusion']
    assert r['read_only']


def test_no_replies_does_not_claim_isp_is_down(monkeypatch):
    monkeypatch.setattr(center, '_scan_lock', nullcontext)
    monkeypatch.setattr(center, '_probe_reference', lambda ip: center.describe_samples([{'timestamp': 1, 'latency_ms': None}], ip))
    assert 'bloqueio de ICMP' in center.scan_connection()['conclusion']


def test_dns_does_not_recommend_failed_provider(monkeypatch):
    monkeypatch.setattr(center, '_scan_lock', nullcontext)
    monkeypatch.setattr(center, '_benchmark', lambda provider: DNSScore(provider, [None] * 6))
    r = center.rank_dns()
    assert r['recommendation'] is None
    assert len(r['results']) == 3
    assert all(row['median_ms'] is None for row in r['results'])


def test_dns_ranking_penalizes_failures(monkeypatch):
    monkeypatch.setattr(center, '_scan_lock', nullcontext)
    values = {'Cloudflare': [1, None, None, None, None, None], 'Google': [30] * 6, 'Quad9': [40] * 6}
    monkeypatch.setattr(center, '_benchmark', lambda provider: DNSScore(provider, values[provider.name]))
    assert center.rank_dns()['recommendation'] == 'Google'


def test_advisory_lock_rejects_overlap_and_releases(tmp_path):
    with center._scan_lock(tmp_path):
        with pytest.raises(RuntimeError):
            with center._scan_lock(tmp_path):
                pass
    with center._scan_lock(tmp_path):
        pass


def test_pc_shortcuts_reject_arbitrary_destinations():
    for target in ('powershell.exe', 'https://example.com', '../power', 'power --help'):
        with pytest.raises(ValueError): pc_center.open_pc_settings(target)


NEW_GAMES = ['fortnite', 'fallguys', 'pubg', 'rainbow6', 'dayz', 'arma3']


@pytest.mark.parametrize('game', NEW_GAMES)
@pytest.mark.parametrize('profile', list(BoostProfile))
def test_all_requested_profiles_downgrade_new_games(game, profile):
    assert anti_cheat.effective_profile(profile, game) is BoostProfile.PROTECTED_SAFE


@pytest.mark.parametrize('game', NEW_GAMES)
def test_catalog_aliases_detection_and_mutation_guards(game, monkeypatch):
    definition = GameCatalog.load().get(game)
    assert definition.catalog_source.startswith('https://')
    assert not definition.pools
    for alias in definition.process_names:
        assert anti_cheat.PROTECTED_PROCESS_TO_GAME[alias.lower()] == game
        monkeypatch.setattr(anti_cheat, '_iter_process_names', lambda: [(123, alias.lower())])
        monkeypatch.setattr(anti_cheat, 'running_protected_services', lambda: [])
        assert game in anti_cheat.running_protected_games()
    for action in anti_cheat.BLOCKED_MUTATIONS_DURING_PROTECTED_RUNTIME:
        with pytest.raises(anti_cheat.ProtectedGameMutationError):
            anti_cheat.assert_mutation_allowed(action, game_id=game)


@pytest.mark.parametrize('game', NEW_GAMES)
def test_discovery_never_opens_new_protected_process(game, monkeypatch):
    definition = GameCatalog.load().get(game)
    monkeypatch.setattr(discovery, '_running_processes', lambda: {definition.process_names[0].lower(): [{'pid': 123}]})
    monkeypatch.setattr(discovery, '_expand_hint', lambda _: [])
    monkeypatch.setattr(discovery, '_steam_library_paths', lambda: [])
    monkeypatch.setattr(discovery.psutil, 'Process', lambda _: pytest.fail('Opened protected PID'))
    r = discovery.discover_games(GameCatalog({game: definition}))[0]
    assert r['running'] and r['installed']
    assert r['executable'] is None
    assert r['live_match_validated'] is False


def test_steam_libraries_discover_new_game(tmp_path, monkeypatch):
    catalog = GameCatalog.load()
    game = catalog.get('dayz')
    exe = tmp_path / 'steamapps/common' / game.steam_paths[0]
    exe.parent.mkdir(parents=True); exe.touch()
    monkeypatch.setattr(discovery, '_steam_library_paths', lambda: [tmp_path])
    monkeypatch.setattr(discovery, '_running_processes', lambda: {})
    assert discovery.discover_games(GameCatalog({'dayz': game}))[0]['installed']


def test_protected_game_precedes_roblox():
    result = discovery.preferred_running_game([{'id': 'roblox', 'running': True}, {'id': 'fortnite', 'running': True}])
    assert result['id'] == 'fortnite'
