from pathlib import Path
from nexus_engine.state import StateStore


def test_state_round_trip(tmp_path: Path):
    store = StateStore(tmp_path / "state.json")
    value = {"schema": 1, "active": True, "foo": [1, 2, 3]}
    store.save(value)
    assert store.load() == value
    store.clear()
    assert store.load()["active"] is False


def test_state_recovers_from_backup(tmp_path: Path):
    store = StateStore(tmp_path / "state.json")
    first = {"schema": 1, "active": True, "generation": 1}
    second = {"schema": 1, "active": True, "generation": 2}
    store.save(first)
    store.save(second)
    store.path.write_text("{broken", encoding="utf-8")
    recovered = store.load()
    assert recovered["generation"] == 1
    assert recovered["recovered_from_backup"] is True
