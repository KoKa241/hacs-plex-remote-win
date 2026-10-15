"""Opt-in creation of a single HomeKit TV accessory through HA's config flow."""

import asyncio

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.setup import async_setup_component

from .const import DOMAIN


def accessory_for_entity(entries, entity_id):
    for entry in entries:
        config = {**entry.data, **entry.options}
        if config.get("mode") == "accessory" and entity_id in config.get("filter", {}).get(
            "include_entities", []
        ):
            return entry
    return None


def async_register_homekit_service(hass):
    lock = asyncio.Lock()

    async def expose(call):
        entity_id = call.data["entity_id"]
        entry = er.async_get(hass).async_get(entity_id)
        if entry is None or entry.platform != DOMAIN or not entity_id.startswith("media_player."):
            raise HomeAssistantError("Select a Plex PC Remote TV entity")
        state = hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            raise HomeAssistantError("Connect the Windows server first")
        async with lock:
            existing = accessory_for_entity(hass.config_entries.async_entries("homekit"), entity_id)
            if existing is None:
                if not await async_setup_component(hass, "homekit", {}):
                    raise HomeAssistantError("HomeKit Bridge could not start; check the Home Assistant log")
                from homeassistant.components.homekit.const import DEFAULT_CONFIG_FLOW_PORT
                from homeassistant.components.homekit.util import async_find_next_available_port

                port = async_find_next_available_port(hass, DEFAULT_CONFIG_FLOW_PORT)
                result = await hass.config_entries.flow.async_init(
                    "homekit",
                    context={"source": "accessory"},
                    data={"entity_id": entity_id, "port": port},
                )
                if result["type"] != "create_entry":
                    raise HomeAssistantError("HomeKit accessory creation failed; use HomeKit Bridge settings")
            persistent_notification.async_create(
                hass,
                "Телевизор Plex настроен в HomeKit Bridge. Откройте уведомление HomeKit с QR-кодом "
                "(или Настройки → Устройства и службы → HomeKit Bridge), затем на iPhone: "
                "Дом → + → Добавить аксессуар. Для стрелок откройте пульт Apple TV в Пункте управления. "
                "Если аксессуар уже сопряжён, повторное добавление не требуется.",
                title="Plex → Apple Home",
                notification_id=f"{DOMAIN}_homekit_{entity_id}",
            )

    async_register_admin_service(
        hass,
        DOMAIN,
        "expose_homekit",
        expose,
        schema=vol.Schema({vol.Required("entity_id"): cv.entity_id}),
    )
