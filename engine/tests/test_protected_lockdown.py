from __future__ import annotations

import pytest

from nexus_engine import anti_cheat
from nexus_engine.anti_cheat import ProtectedGameMutationError
from nexus_engine.hardware.memory import purge_standby_list
from nexus_engine.hardware.process import ProcessOptimizer
from nexus_engine.hardware.services import ServiceManager
from nexus_engine.models import BoostProfile
from nexus_engine.network.dns import DNSManager, DNSProvider
from nexus_engine.network.firewall import FirewallManager
from nexus_engine.network.mtu import MTUManager
from nexus_engine.network.tcp_tweaks import TcpTweaks
from nexus_engine.winexec import ProtectedPowerShellError


def test_policy_report_exposes_maximum_compatibility_lockdown(monkeypatch):
    monkeypatch.setattr(anti_cheat, "vanguard_processes", lambda: ["vgc.exe"])
    report = anti_cheat.anti_cheat_policy_report(
        "valorant", BoostProfile.AGGRESSIVE, BoostProfile.RIOT_SAFE
    )
    assert report["lockdown"] == "maximum_compatibility"
    assert report["capabilities"]["process_optimization"] is False
    assert report["capabilities"]["power_plan"] is True
    assert report["policy_reviewed_at"] == "2026-09-04"


def test_low_level_firewall_rejects_protected_title_without_touching_disk():
    with pytest.raises(ProtectedGameMutationError):
        FirewallManager().prepare(
            "valorant",
            "test",
            r"C:\does-not-need-to-exist\VALORANT.exe",
            ["192.0.2.10"],
        )


def test_direct_firewall_apply_cannot_bypass_prepare():
    with pytest.raises(ProtectedGameMutationError):
        FirewallManager().apply(
            {
                "name": "NexuFlow::valorant::test::x",
                "game_id": "valorant",
                "program": r"C:\fake.exe",
                "ips": ["192.0.2.10"],
            }
        )


def test_global_mutation_modules_lock_during_protected_runtime(monkeypatch):
    monkeypatch.setattr(anti_cheat, "running_protected_games", lambda: ["valorant"])

    with pytest.raises(ProtectedGameMutationError):
        DNSManager.apply(10, DNSProvider("Test", ("1.1.1.1",)))
    with pytest.raises(ProtectedGameMutationError):
        MTUManager.apply(10, 1492)
    with pytest.raises(ProtectedGameMutationError):
        TcpTweaks("{00000000-0000-0000-0000-000000000000}").apply()
    with pytest.raises(ProtectedGameMutationError):
        purge_standby_list()
    with pytest.raises(ProtectedGameMutationError):
        ServiceManager.pause([])


def test_process_optimizer_never_opens_protected_pid(monkeypatch):
    monkeypatch.setattr(anti_cheat, "protected_pid_game", lambda _pid: "cs2")

    with pytest.raises(ProtectedGameMutationError):
        ProcessOptimizer.snapshot(1234)


def test_legacy_protected_process_rollback_leaves_process_untouched(monkeypatch):
    import nexus_engine.hardware.process as process_module

    monkeypatch.setattr(process_module.psutil, "pid_exists", lambda _pid: True)
    monkeypatch.setattr(process_module, "protected_pid_game", lambda _pid: "lol")

    def should_not_open(_pid):
        raise AssertionError("protected process must not be opened")

    monkeypatch.setattr(process_module.psutil, "Process", should_not_open)
    result = ProcessOptimizer.restore({"pid": 1234, "priority": 0, "cpu_sets": []})
    assert result["restored"] is False
    assert result["safe_to_forget_after_process_exit"] is True


def test_gaming_health_avoids_powershell_adapter_introspection_in_protected_mode(monkeypatch):
    import nexus_engine.hardware.health as health_module

    def should_not_query_interface():
        raise AssertionError("protected gaming health must not spawn PowerShell adapter introspection")

    monkeypatch.setattr(health_module.InterfaceManager, "primary_ipv4", should_not_query_interface)
    monkeypatch.setattr(health_module, "nvidia_telemetry", lambda: {"available": False, "name": None})
    monkeypatch.setattr(health_module, "_power_scheme", lambda: {"guid": None, "name": None, "on_ac_power": True})
    result = health_module.gaming_health(protected_runtime=True)
    assert result["network"]["deferred"] is True


def test_dns_benchmark_avoids_adapter_and_current_resolver_when_protected(monkeypatch):
    import asyncio
    from app.modules.dns_benchmark.service import DNSBenchmarkService
    from nexus_engine.network.dns import DNSScore, DNSProvider
    import app.modules.dns_benchmark.service as dns_service_module

    monkeypatch.setattr(dns_service_module, "running_protected_games", lambda: ["cs2"])

    def should_not_query_interface():
        raise AssertionError("protected DNS benchmark must not query adapter through PowerShell")

    monkeypatch.setattr(dns_service_module.InterfaceManager, "primary_ipv4", should_not_query_interface)
    service = DNSBenchmarkService()

    async def fake_benchmark(current_servers):
        assert current_servers == []
        return [DNSScore(DNSProvider("Cloudflare", ("1.1.1.1",)), [10.0, 11.0])]

    monkeypatch.setattr(service.manager, "benchmark", fake_benchmark)
    result = asyncio.run(service.benchmark())
    assert result["diagnostic_only"] is True
    assert result["current_queried"] is False
    assert result["interface"]["deferred"] is True


def test_low_level_route_diagnostics_rejects_arbitrary_target_when_protected(monkeypatch):
    import nexus_engine.telemetry as telemetry_module

    monkeypatch.setattr(telemetry_module, "running_protected_games", lambda: ["cs2"])
    with pytest.raises(ValueError):
        telemetry_module.route_diagnostics("192.0.2.50")


def test_global_command_runner_blocks_powershell_and_pwsh_before_spawn(monkeypatch):
    import nexus_engine.winexec as winexec

    monkeypatch.setattr(winexec, "_protected_session_active", lambda: True)

    def must_not_spawn(*_args, **_kwargs):
        raise AssertionError("PowerShell process must not be created")

    monkeypatch.setattr(winexec.subprocess, "run", must_not_spawn)
    for executable in ("powershell.exe", "pwsh.exe", r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"):
        with pytest.raises(ProtectedPowerShellError):
            winexec.run_command([executable, "-Command", "Get-Date"])


def test_preflight_is_deferred_when_powershell_guard_is_active(monkeypatch):
    import nexus_engine.preflight as preflight

    monkeypatch.setattr(preflight.os, "name", "nt")
    monkeypatch.setattr(
        preflight,
        "powershell_json",
        lambda _script: (_ for _ in ()).throw(ProtectedPowerShellError("protected")),
    )
    report = preflight.preflight_report()
    assert report["checks"]["deferred"] is True
    assert report["checks"]["available"] is False


def test_protected_transition_rollbacks_use_no_powershell(monkeypatch):
    import nexus_engine.hardware.services as services_module
    import nexus_engine.network.dns as dns_module
    import nexus_engine.network.firewall as firewall_module
    import nexus_engine.network.mtu as mtu_module

    calls: list[list[str]] = []

    def capture(args, **_kwargs):
        calls.append([str(value) for value in args])
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(dns_module, "run_command", capture)
    monkeypatch.setattr(mtu_module, "run_command", capture)
    monkeypatch.setattr(firewall_module, "run_command", capture)
    monkeypatch.setattr(services_module, "run_command", capture)

    DNSManager.restore({"InterfaceIndex": 7, "StaticConfigured": True, "ServerAddresses": ["1.1.1.1", "1.0.0.1"]})
    MTUManager.restore(7, 1500)
    FirewallManager.delete("NexuFlow::roblox::pool::abc")
    ServiceManager.restore([{"Name": "DiagTrack", "WasRunning": True, "PausedByNexus": True}])

    assert calls
    assert all(call[0].lower() not in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"} for call in calls)
    assert any(call[:4] == ["netsh", "interface", "ipv4", "set"] for call in calls)
    assert any(call[:4] == ["netsh", "advfirewall", "firewall", "delete"] for call in calls)
    assert any(call[:2] == ["sc.exe", "start"] for call in calls)
