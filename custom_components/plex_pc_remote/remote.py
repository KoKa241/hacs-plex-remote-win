"""Navigation and extra Plex controls."""

import asyncio

from homeassistant.components.remote import RemoteEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .entity import PlexEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PlexRemote(entry.runtime_data)])


class PlexRemote(PlexEntity, RemoteEntity):
    _attr_name = "Remote"

    def __init__(self, coordinator):
        super().__init__(coordinator, "remote")

    @property
    def is_on(self):
        return self.coordinator.data["running"]

    @property
    def extra_state_attributes(self):
        registry = er.async_get(self.hass)
        return {
            "integration": DOMAIN,
            "tv_entity_id": registry.async_get_entity_id(
                "media_player", DOMAIN, f"{self.coordinator.server_id}_tv"
            ),
            "server_version": self.coordinator.data.get("version"),
            "input_ready": self.coordinator.data.get("input_ready"),
        }

    async def async_turn_on(self, **kwargs):
        await self.coordinator.command("turn_on")

    async def async_turn_off(self, **kwargs):
        await self.coordinator.command("turn_off")

    async def async_toggle(self, **kwargs):
        await self.coordinator.command("toggle")

    async def async_send_command(self, command, **kwargs):
        commands = [command] if isinstance(command, str) else list(command)
        repeats = int(kwargs.get("num_repeats", 1))
        delay = float(kwargs.get("delay_secs", 0.15))
        if not 1 <= repeats <= 20 or not 0 <= delay <= 5 or len(commands) > 50:
            raise HomeAssistantError("Command sequence/repeat/delay limit exceeded")
        if kwargs.get("hold_secs", 0):
            raise HomeAssistantError("Holding keys is not supported")
        allowed = self.coordinator.data.get("commands", [])
        if any(c not in allowed for c in commands):
            raise HomeAssistantError("Unsupported Plex command")
        for index in range(repeats):
            for position, item in enumerate(commands):
                if index or position:
                    await asyncio.sleep(delay)
                await self.coordinator.command(item)
