"""Shared device metadata."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class PlexEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, suffix):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.server_id}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.server_id)},
            name="Plex PC",
            manufacturer="Plex PC Remote",
            model="Windows / Plex HTPC",
            sw_version=coordinator.data.get("version"),
        )
