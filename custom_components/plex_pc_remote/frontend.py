"""Ship a complete remote panel with the integration, without a second HACS repo."""

import asyncio
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN

URL = "/plex_pc_remote/plex-remote.js"
MODULE_URL = URL + "?v=1.3.1"
PANEL_PATH = "plex-pc-remote"


async def async_setup_frontend(hass):
    data = hass.data.setdefault(DOMAIN, {})
    async with data.setdefault("frontend_lock", asyncio.Lock()):
        await _async_setup_frontend(hass)


async def _async_setup_frontend(hass):
    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("static_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL, str(Path(__file__).parent / "www" / "plex-remote.js"), False)]
        )
        # Loads the same element in Lovelace's card picker, too.
        frontend.add_extra_js_url(hass, MODULE_URL)
        data["static_registered"] = True
    if not data.get("panel_registered"):
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_PATH,
            webcomponent_name="plex-pc-remote-panel",
            sidebar_title="Plex пульт",
            sidebar_icon="mdi:remote-tv",
            module_url=MODULE_URL,
        )
        data["panel_registered"] = True


def async_remove_panel(hass):
    data = hass.data.get(DOMAIN, {})
    if data.pop("panel_registered", False):
        frontend.async_remove_panel(hass, PANEL_PATH)
