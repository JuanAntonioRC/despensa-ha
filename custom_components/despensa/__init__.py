"""Despensa: inventario de casa dentro de Home Assistant."""
from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "despensa"
STATIC_URL = "/despensa_static"
FRONTEND = Path(__file__).parent / "frontend"
VERSION = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Las rutas estáticas no se pueden quitar: se registran una vez por arranque de HA.
    if not hass.data.get(DOMAIN):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND), cache_headers=False)]
        )
        hass.data[DOMAIN] = True
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path="despensa",
        webcomponent_name="despensa-panel",
        module_url=f"{STATIC_URL}/despensa-panel.js?v={VERSION}",
        sidebar_title="Despensa",
        sidebar_icon="mdi:fridge-outline",
        require_admin=False,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    frontend.async_remove_panel(hass, "despensa")
    return True
