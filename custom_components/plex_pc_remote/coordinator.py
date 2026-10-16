"""Polling and serialized command delivery."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, InvalidAuth
from .const import DOMAIN


class PlexCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, entry):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
            config_entry=entry,
        )
        self.api = api
        self.command_lock = asyncio.Lock()
        self.server_id = entry.unique_id

    async def _request(self, command=None):
        data = await self.api.request(command)
        if data["server_id"] != self.server_id:
            raise ApiError("Server identity changed; remove and add the integration again")
        return data

    async def _async_update_data(self):
        async with self.command_lock:
            try:
                return await self._request()
            except InvalidAuth as exc:
                raise ConfigEntryAuthFailed from exc
            except ApiError as exc:
                raise UpdateFailed(str(exc)) from exc

    async def command(self, command):
        async with self.command_lock:
            try:
                data = await self._request(command)
            except ApiError as exc:
                # A rejected action does not mean Plex was turned off.
                raise HomeAssistantError(str(exc)) from exc
            self.async_set_updated_data(data)

    async def desktop_input(self, payload):
        async with self.command_lock:
            if not self.data.get("desktop_input"):
                raise HomeAssistantError("Update the Windows server to 1.2.0")
            try:
                data = await self.api.input(payload)
                if data.get("server_id") != self.server_id:
                    raise ApiError("Server identity changed")
            except ApiError as exc:
                raise HomeAssistantError(str(exc)) from exc
