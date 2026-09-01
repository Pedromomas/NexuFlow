from nexus_engine.catalog import GameCatalog


def test_builtin_catalog_has_supported_games():
    catalog = GameCatalog.load()
    assert {"roblox", "valorant", "cs2", "lol"}.issubset(catalog.games)
    assert "RobloxPlayerBeta.exe" in catalog.get("roblox").process_names
