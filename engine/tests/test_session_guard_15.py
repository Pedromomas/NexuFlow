from nexus_engine.hardware import session_guard


class _Process:
    def __init__(self, name: str) -> None:
        self.info = {"name": name}


def test_session_guard_is_advisory_and_privacy_minimized(monkeypatch):
    monkeypatch.setattr(session_guard, "running_protected_games", lambda: [])
    monkeypatch.setattr(
        session_guard.psutil,
        "process_iter",
        lambda _attrs: [_Process("Discord.exe"), _Process("private-app.exe")],
    )

    report = session_guard.session_guard_report()

    assert report["read_only"] is True
    assert report["mutation_enabled"] is False
    assert report["candidates"] == ["discord.exe"]
    assert "pid" not in report
    assert "paths" not in report
    assert "private-app.exe" not in str(report)


def test_session_guard_defers_all_process_scanning_when_protected(monkeypatch):
    monkeypatch.setattr(session_guard, "running_protected_games", lambda: ["cs2"])
    monkeypatch.setattr(
        session_guard.psutil,
        "process_iter",
        lambda _attrs: (_ for _ in ()).throw(AssertionError("must not scan")),
    )

    report = session_guard.session_guard_report()

    assert report["deferred"] is True
    assert report["mutation_enabled"] is False
    assert report["candidates"] == []
