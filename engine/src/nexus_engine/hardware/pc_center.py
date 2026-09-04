"""Fixed Windows Settings destinations, never a shell or arbitrary URL."""
from __future__ import annotations
import os

PC_SETTINGS = {
    "game_mode": "ms-settings:gaming-gamemode",
    "captures": "ms-settings:gaming-gamedvr",
    "graphics": "ms-settings:display-advancedgraphics",
    "startup": "ms-settings:startupapps",
    "storage": "ms-settings:storagesense",
    "power": "ms-settings:powersleep",
    "network": "ms-settings:network-status",
}


def open_pc_settings(section: str) -> dict:
    if section not in PC_SETTINGS:
        raise ValueError("Destino de ajustes não permitido")
    if os.name != "nt":
        raise OSError("Estes ajustes estão disponíveis somente no Windows")
    os.startfile(PC_SETTINGS[section])  # type: ignore[attr-defined]
    return {"ok": True, "opened": True, "settings_changed": False,
            "message": "Ajustes do Windows abertos. Nenhuma configuração foi alterada automaticamente."}
