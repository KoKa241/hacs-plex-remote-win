"""TV entity exported through HomeKit Bridge."""

import logging

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerState,
)
from homeassistant.components.media_player import (
    MediaPlayerEntityFeature as F,
)
from homeassistant.exceptions import HomeAssistantError

from .const import HOMEKIT_KEYS
from .entity import PlexEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PlexTV(entry.runtime_data)])


class PlexTV(PlexEntity, MediaPlayerEntity):
    _attr_name = "TV"
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = (
        F.TURN_ON | F.TURN_OFF | F.PLAY | F.PAUSE | F.STOP | F.NEXT_TRACK | F.PREVIOUS_TRACK | F.VOLUME_STEP
    )

    def __init__(self, coordinator):
        super().__init__(coordinator, "tv")

    @property
    def state(self):
        # Process status is real; keyboard delivery cannot reveal playback state.
        return MediaPlayerState.ON if self.coordinator.data["running"] else MediaPlayerState.OFF

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.hass.bus.async_listen("homekit_tv_remote_key_pressed", self._homekit_key))

    async def _homekit_key(self, event):
        if event.data.get("entity_id") != self.entity_id:
            return
        if command := HOMEKIT_KEYS.get(event.data.get("key_name")):
            try:
                await self.coordinator.command(command)
            except HomeAssistantError as exc:
                _LOGGER.warning("HomeKit Plex command failed: %s", exc)

    async def async_turn_on(self):
        await self.coordinator.command("turn_on")

    async def async_turn_off(self):
        await self.coordinator.command("turn_off")

    async def async_toggle(self):
        await self.coordinator.command("toggle")

    async def async_media_play(self):
        await self.coordinator.command("play")

    async def async_media_pause(self):
        await self.coordinator.command("pause")

    async def async_media_play_pause(self):
        await self.coordinator.command("play_pause")

    async def async_media_stop(self):
        await self.coordinator.command("stop")

    async def async_media_next_track(self):
        await self.coordinator.command("next")

    async def async_media_previous_track(self):
        await self.coordinator.command("previous")

    async def async_volume_up(self):
        await self.coordinator.command("volume_up")

    async def async_volume_down(self):
        await self.coordinator.command("volume_down")
