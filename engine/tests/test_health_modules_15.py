from __future__ import annotations

import inspect
from types import SimpleNamespace

from nexus_engine.diagnostics import stutter_health
from nexus_engine.hardware import windows_gaming
from nexus_engine.network import nic_health


def test_nic_health_defers_before_powershell_when_protected(monkeypatch):
    monkeypatch.setattr(nic_health, "running_protected_games", lambda: ["cs2"])

    def must_not_query():
        raise AssertionError("PowerShell must not run during protected gameplay")

    monkeypatch.setattr(nic_health, "_query_windows_nic", must_not_query)
    report = nic_health.nic_health_report()
    assert report["deferred"] is True
    assert report["protected_games"] == ["cs2"]
    assert report["mutation_performed"] is False


def test_nic_health_classifies_read_only_driver_state(monkeypatch):
    monkeypatch.setattr(nic_health, "_is_windows", lambda: True)
    monkeypatch.setattr(nic_health, "running_protected_games", lambda: [])
    monkeypatch.setattr(
        nic_health,
        "_query_windows_nic",
        lambda: {
            "available": True,
            "adapter": {"name": "Ethernet", "interface_index": 7},
            "rss": {"supported": True, "enabled": False},
            "advanced_properties": [
                {"registry_keyword": "*EEE", "registry_value": 1, "display_name": "Energy Efficient Ethernet", "display_value": "Enabled"},
                {"registry_keyword": "*InterruptModeration", "registry_value": 0, "display_name": "Interrupt Moderation", "display_value": "Disabled"},
            ],
        },
    )
    report = nic_health.nic_health_report()
    assert report["available"] is True
    assert report["features"]["energy_efficient_ethernet"]["enabled"] is True
    assert report["features"]["receive_side_scaling"]["enabled"] is False
    assert report["features"]["interrupt_moderation"]["enabled"] is False
    assert {item["feature"] for item in report["recommendations"]} >= {
        "energy_efficient_ethernet",
        "receive_side_scaling",
    }


def test_nic_health_source_contains_no_adapter_mutation():
    source = inspect.getsource(nic_health).casefold()
    for forbidden in ("set-netadapter", "enable-netadapter", "disable-netadapter", "set-netipinterface"):
        assert forbidden not in source


def test_windows_gaming_report_is_registry_only_and_path_private(monkeypatch):
    monkeypatch.setattr(windows_gaming, "_is_windows", lambda: True)
    monkeypatch.setattr(
        windows_gaming,
        "_read_game_mode",
        lambda: {"available": True, "status": "enabled", "enabled": True, "source_value": "AutoGameModeEnabled"},
    )
    monkeypatch.setattr(
        windows_gaming,
        "_read_gpu_preferences",
        lambda: {"available": True, "stored_entries": 3, "system_default": 1, "power_saving": 0, "high_performance": 2, "unrecognized": 0},
    )
    report = windows_gaming.windows_gaming_report()
    assert report["read_only"] is True
    assert report["process_inspection"] is False
    assert report["protected_process_access"] is False
    assert report["graphics_preferences"]["high_performance"] == 2
    assert report["graphics_preferences"]["application_paths_exported"] is False


def test_windows_gaming_source_never_writes_registry_or_reads_processes():
    source = inspect.getsource(windows_gaming)
    for forbidden in ("SetValue", "CreateKey", "DeleteValue", "process_iter", "psutil.Process"):
        assert forbidden not in source
    assert "KEY_READ" in source


def test_stutter_classification_is_conservative():
    quiet = stutter_health.classify_stutter_snapshot({
        "cpu": {"total_percent": 20.0, "peak_core_percent": 40.0},
        "memory": {"percent": 40.0, "available_gb": 8.0},
        "rates": {"context_switches_per_second": 1_000, "interrupts_per_second": 500, "disk_megabytes_per_second": 2.0},
    })
    assert quiet["classification"] == "no_obvious_system_pressure_in_sample"
    assert quiet["stutter_cause_confirmed"] is False

    pressured = stutter_health.classify_stutter_snapshot({
        "cpu": {"total_percent": 96.0, "peak_core_percent": 100.0},
        "memory": {"percent": 95.0, "available_gb": 0.5},
        "rates": {"context_switches_per_second": 200_000, "interrupts_per_second": 60_000, "disk_megabytes_per_second": 300.0},
    })
    assert pressured["classification"] == "possible_system_pressure"
    assert pressured["stutter_cause_confirmed"] is False
    assert {signal["code"] for signal in pressured["signals"]} >= {"cpu_pressure", "memory_pressure"}


def test_stutter_snapshot_uses_counters_but_never_starts_etw(monkeypatch):
    counter_before = SimpleNamespace(ctx_switches=100, interrupts=50)
    counter_after = SimpleNamespace(ctx_switches=200, interrupts=75)
    disk_before = SimpleNamespace(read_bytes=1000, write_bytes=2000)
    disk_after = SimpleNamespace(read_bytes=3000, write_bytes=5000)
    net_before = SimpleNamespace(bytes_sent=100, bytes_recv=200)
    net_after = SimpleNamespace(bytes_sent=300, bytes_recv=500)
    sequence = iter((counter_before, counter_after))
    monkeypatch.setattr(stutter_health.psutil, "cpu_stats", lambda: next(sequence))
    monkeypatch.setattr(stutter_health.psutil, "cpu_percent", lambda interval, percpu: [10.0, 20.0])
    monkeypatch.setattr(stutter_health.psutil, "disk_io_counters", lambda: disk_before if not hasattr(test_stutter_snapshot_uses_counters_but_never_starts_etw, "disk_seen") else disk_after)
    monkeypatch.setattr(stutter_health.psutil, "net_io_counters", lambda: net_before if not hasattr(test_stutter_snapshot_uses_counters_but_never_starts_etw, "net_seen") else net_after)
    # Replace stateful counter helpers with deterministic iterators.
    disk_sequence = iter((disk_before, disk_after))
    net_sequence = iter((net_before, net_after))
    monkeypatch.setattr(stutter_health.psutil, "disk_io_counters", lambda: next(disk_sequence))
    monkeypatch.setattr(stutter_health.psutil, "net_io_counters", lambda: next(net_sequence))
    monkeypatch.setattr(stutter_health.psutil, "virtual_memory", lambda: SimpleNamespace(percent=30.0, available=8 * 1024 ** 3))
    monkeypatch.setattr(stutter_health.psutil, "swap_memory", lambda: SimpleNamespace(percent=0.0))
    monkeypatch.setattr(stutter_health.psutil, "cpu_freq", lambda: SimpleNamespace(current=4200.0))
    monkeypatch.setattr(stutter_health.psutil, "cpu_count", lambda logical: 2)
    times = iter((10.0, 11.0))
    monkeypatch.setattr(stutter_health.time, "monotonic", lambda: next(times))

    report = stutter_health.stutter_health_snapshot(0)
    assert report["available"] is True
    assert report["process_inspection"] is False
    assert report["driver_attribution"] is False
    assert report["etw"]["trace_started"] is False

    source = inspect.getsource(stutter_health).casefold()
    for forbidden in ("starttrace", "controltrace", "xperf", "wpr.exe", "subprocess", "process_iter"):
        assert forbidden not in source
