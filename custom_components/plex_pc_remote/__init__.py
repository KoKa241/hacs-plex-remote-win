"""Plex PC Remote integration."""

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PlexAPI
from .const import PLATFORMS
from .coordinator import PlexCoordinator


async def async_setup_entry(hass, entry):
    api = PlexAPI(async_get_clientsession(hass), entry.data["url"], entry.data["token"])
    coordinator = PlexCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
