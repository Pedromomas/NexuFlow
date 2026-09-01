from nexus_engine.anti_cheat import anti_cheat_policy_report, effective_profile, is_protected_game
from nexus_engine.models import BoostProfile


def test_riot_titles_force_riot_safe_even_from_aggressive():
    assert effective_profile(BoostProfile.AGGRESSIVE, "valorant") is BoostProfile.RIOT_SAFE
    assert effective_profile(BoostProfile.AGGRESSIVE, "lol") is BoostProfile.RIOT_SAFE


def test_cs2_forces_valve_safe_even_from_aggressive():
    assert effective_profile(BoostProfile.AGGRESSIVE, "cs2") is BoostProfile.VALVE_SAFE
    assert effective_profile(BoostProfile.AUTO, "cs2") is BoostProfile.VALVE_SAFE


def test_auto_selects_roblox_profile():
    assert effective_profile(BoostProfile.AUTO, "roblox") is BoostProfile.ROBLOX


def test_explicit_protected_profiles_do_not_leak_to_other_games():
    assert effective_profile(BoostProfile.RIOT_SAFE, "roblox") is BoostProfile.SAFE
    assert effective_profile(BoostProfile.VALVE_SAFE, "roblox") is BoostProfile.SAFE


def test_protected_policy_blocks_game_process_and_injection(monkeypatch):
    monkeypatch.setattr("nexus_engine.anti_cheat.vanguard_processes", lambda: ["vgc.exe"])
    report = anti_cheat_policy_report("valorant", BoostProfile.AGGRESSIVE, BoostProfile.RIOT_SAFE)
    assert report["active"] is True
    assert report["provider"] == "Riot Vanguard"
    assert "process_memory_access" in report["blocked_features"]
    assert "endpoint_firewall_steering" in report["blocked_features"]
    assert report["vanguard_processes_detected"] == ["vgc.exe"]


def test_valve_policy_preserves_trusted_mode():
    report = anti_cheat_policy_report("cs2", BoostProfile.AGGRESSIVE, BoostProfile.VALVE_SAFE)
    assert is_protected_game("cs2")
    assert report["provider"] == "Valve VAC / Trusted Mode"
    assert "-allow_third_party_software" in report["trusted_mode_note"]
    assert "dll_injection" in report["blocked_features"]


def test_protected_pid_classification_uses_process_list_only(monkeypatch):
    class FakeProc:
        def __init__(self, pid, name):
            self.info = {"pid": pid, "name": name}

    monkeypatch.setattr(
        "nexus_engine.anti_cheat.psutil.process_iter",
        lambda _attrs: [FakeProc(123, "cs2.exe"), FakeProc(456, "notepad.exe")],
    )
    from nexus_engine.anti_cheat import protected_pid_game

    assert protected_pid_game(123) == "cs2"
    assert protected_pid_game(456) is None


def test_running_eac_service_forces_generic_protected_runtime(monkeypatch):
    from nexus_engine import anti_cheat

    class FakeService:
        def name(self):
            return "EasyAntiCheat_EOS_Game123"

        def display_name(self):
            return "Easy Anti-Cheat (Epic Online Services)"

        def status(self):
            return "running"

    monkeypatch.setattr(anti_cheat, "_iter_process_names", lambda: [])
    monkeypatch.setattr(anti_cheat.psutil, "win_service_iter", lambda: [FakeService()], raising=False)

    assert anti_cheat.running_protected_games() == ["protected_runtime"]
    assert anti_cheat.running_protected_services() == ["EasyAntiCheat_EOS_Game123"]


def test_running_battleye_service_forces_generic_protected_runtime(monkeypatch):
    from nexus_engine import anti_cheat

    class FakeService:
        def name(self):
            return "BEService_Fortnite"

        def display_name(self):
            return "BattlEye Service"

        def status(self):
            return "RUNNING"

    monkeypatch.setattr(anti_cheat, "_iter_process_names", lambda: [])
    monkeypatch.setattr(anti_cheat.psutil, "win_service_iter", lambda: [FakeService()], raising=False)

    assert anti_cheat.running_protected_games() == ["protected_runtime"]


def test_stopped_eac_service_is_not_an_active_runtime(monkeypatch):
    from nexus_engine import anti_cheat

    class FakeService:
        def name(self):
            return "EasyAntiCheat"

        def display_name(self):
            return "Easy Anti-Cheat"

        def status(self):
            return "stopped"

    monkeypatch.setattr(anti_cheat, "_iter_process_names", lambda: [])
    monkeypatch.setattr(anti_cheat.psutil, "win_service_iter", lambda: [FakeService()], raising=False)

    assert anti_cheat.running_protected_games() == []
    assert anti_cheat.running_protected_services() == []


def test_vanguard_services_are_environment_evidence_not_global_lock(monkeypatch):
    from nexus_engine import anti_cheat

    class FakeService:
        def __init__(self, name, status):
            self._name = name
            self._status = status

        def name(self):
            return self._name

        def display_name(self):
            return "Riot Vanguard"

        def status(self):
            return self._status

    services = [FakeService("vgk", "running"), FakeService("vgc", "running")]
    monkeypatch.setattr(anti_cheat, "_iter_process_names", lambda: [(321, "vgc.exe")])
    monkeypatch.setattr(anti_cheat.psutil, "win_service_iter", lambda: services, raising=False)

    assert anti_cheat.running_protected_games() == []
    context = anti_cheat.protected_runtime_context()
    assert context["active"] is False
    assert context["vanguard_user_processes"] == ["vgc.exe"]
    assert [item["name"] for item in context["vanguard_environment_services"]] == ["vgc", "vgk"]
    assert context["protected_runtime_services"] == []


def test_service_scan_failure_is_reported_without_assuming_absence(monkeypatch):
    from nexus_engine import anti_cheat

    def denied():
        raise OSError("SCM access denied")

    monkeypatch.setattr(anti_cheat, "_iter_process_names", lambda: [])
    monkeypatch.setattr(anti_cheat, "vanguard_processes", lambda: [])
    monkeypatch.setattr(anti_cheat.psutil, "win_service_iter", denied, raising=False)

    context = anti_cheat.protected_runtime_context()
    assert context["active"] is False
    assert context["service_scan_available"] is False
    assert context["protected_runtime_services"] == []


def test_preferred_running_game_prioritizes_protected_title():
    from nexus_engine.discovery import preferred_running_game

    games = [
        {"id": "roblox", "running": True, "display_name": "Roblox", "pid": 1},
        {"id": "valorant", "running": True, "display_name": "VALORANT", "pid": 2},
    ]
    assert preferred_running_game(games)["id"] == "valorant"


def test_preferred_running_game_falls_back_to_normal_title():
    from nexus_engine.discovery import preferred_running_game

    games = [
        {"id": "roblox", "running": True, "display_name": "Roblox", "pid": 1},
        {"id": "lol", "running": False, "display_name": "League", "pid": None},
    ]
    assert preferred_running_game(games)["id"] == "roblox"
