"""Plex PC Remote integration."""

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlexAPI
from .const import DOMAIN, PLATFORMS
from .coordinator import PlexCoordinator
from .frontend import async_remove_panel, async_setup_frontend
from .homekit import async_register_homekit_service


async def async_setup(hass, config):
    async_register_homekit_service(hass)
    return True


async def async_setup_entry(hass, entry):
    await async_setup_frontend(hass)
    api = PlexAPI(async_get_clientsession(hass), entry.data["url"], entry.data["token"])
    coordinator = PlexCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    hass.data.setdefault(DOMAIN, {}).setdefault("loaded_entries", set()).add(entry.entry_id)
    return True


async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        loaded = hass.data.setdefault(DOMAIN, {}).setdefault("loaded_entries", set())
        loaded.discard(entry.entry_id)
        if not loaded:
            async_remove_panel(hass)
    return unloaded
