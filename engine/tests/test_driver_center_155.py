from __future__ import annotations

import inspect

from nexus_engine.hardware import driver_center


def test_driver_scan_defers_before_windows_update_query_when_protected(monkeypatch):
    monkeypatch.setattr(driver_center, "running_protected_games", lambda: ["valorant"])
    monkeypatch.setattr(
        driver_center,
        "_query_windows_update",
        lambda: (_ for _ in ()).throw(AssertionError("must not query during protected gameplay")),
    )

    report = driver_center.scan_driver_updates()

    assert report["deferred"] is True
    assert report["updates"] == []
    assert report["installation_performed"] is False


def test_driver_scan_sanitizes_windows_update_results(monkeypatch):
    monkeypatch.setattr(driver_center, "running_protected_games", lambda: [])
    monkeypatch.setattr(driver_center, "_is_windows", lambda: True)
    monkeypatch.setattr(
        driver_center,
        "_query_windows_update",
        lambda: {
            "result_code": 2,
            "updates": [
                {
                    "title": "Contoso Display Driver",
                    "manufacturer": "Contoso",
                    "model": "GPU 9000",
                    "driver_class": "Display",
                    "provider": "Contoso",
                    "driver_date": "2026-08-30T00:00:00Z",
                    "downloaded": False,
                    "mandatory": False,
                    "hardware_id": "PCI\\PRIVATE",
                    "device_instance_id": "PRIVATE-ID",
                    "path": "C:\\Users\\person\\private.inf",
                }
            ],
        },
    )

    report = driver_center.scan_driver_updates()

    assert report["available"] is True
    assert report["status"] == "updates_available"
    assert report["updates_offered"] == 1
    assert report["download_performed"] is False
    assert report["installation_performed"] is False
    serialized = str(report).casefold()
    assert "private-id" not in serialized
    assert "person" not in serialized
    assert "hardware_id" not in serialized


def test_no_updates_is_not_claimed_as_vendor_latest(monkeypatch):
    monkeypatch.setattr(driver_center, "running_protected_games", lambda: [])
    monkeypatch.setattr(driver_center, "_is_windows", lambda: True)
    monkeypatch.setattr(driver_center, "_query_windows_update", lambda: {"result_code": 2, "updates": []})

    report = driver_center.scan_driver_updates()

    assert report["status"] == "no_updates_offered"
    assert "não prova" in report["caution"].casefold()


def test_driver_center_has_no_silent_download_or_install_surface():
    source = inspect.getsource(driver_center).casefold()
    for forbidden in (
        "createupdateinstaller",
        "createdownloader",
        "iupdateinstaller",
        "pnputil /add-driver",
        "pnputil /delete-driver",
        "devcon",
    ):
        assert forbidden not in source
    assert driver_center.WINDOWS_OPTIONAL_UPDATES_URI == "ms-settings:windowsupdate-optionalupdates"
