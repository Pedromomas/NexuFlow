from __future__ import annotations

import ipaddress
import json
import sys
from pathlib import Path

from .models import Endpoint, EndpointPool, GameDefinition


class CatalogError(RuntimeError):
    pass


def default_catalog_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "data" / "games.json"
    return Path(__file__).resolve().parent / "data" / "games.json"


class GameCatalog:
    def __init__(self, games: dict[str, GameDefinition]):
        self.games = games

    @classmethod
    def load(cls, path: Path | None = None) -> "GameCatalog":
        raw = json.loads((path or default_catalog_path()).read_text(encoding="utf-8"))
        if raw.get("schema") != 1:
            raise CatalogError("Unsupported game catalog schema")
        games: dict[str, GameDefinition] = {}
        for item in raw.get("games", []):
            gid = str(item["id"]).lower()
            pools: list[EndpointPool] = []
            for pool in item.get("pools", []):
                endpoints: list[Endpoint] = []
                for ep in pool.get("endpoints", []):
                    ip = str(ipaddress.ip_address(ep["ip"]))
                    endpoints.append(Endpoint(str(ep["id"]), ip, gid, str(pool["id"]), ep.get("region")))
                pools.append(EndpointPool(str(pool["id"]), gid, bool(pool.get("interchangeable", False)), tuple(endpoints)))
            games[gid] = GameDefinition(
                id=gid,
                display_name=str(item.get("display_name", gid)),
                process_names=tuple(item.get("process_names", [])),
                install_hints=tuple(item.get("install_hints", [])),
                pools=tuple(pools),
            )
        return cls(games)

    def get(self, game_id: str) -> GameDefinition:
        try:
            return self.games[game_id.lower()]
        except KeyError as exc:
            raise CatalogError(f"Unknown game: {game_id}") from exc
