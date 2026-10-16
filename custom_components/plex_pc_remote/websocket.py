"""Authenticated HA WebSocket relay. Windows credentials never reach the browser."""

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_CONTROL
from homeassistant.components import websocket_api
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

PAYLOAD = vol.Any(
    {
        vol.Required("kind"): "move",
        vol.Required("dx"): vol.All(int, vol.Range(min=-500, max=500)),
        vol.Required("dy"): vol.All(int, vol.Range(min=-500, max=500)),
    },
    {vol.Required("kind"): "click", vol.Required("button"): vol.In(["left", "right"])},
    {vol.Required("kind"): "scroll", vol.Required("steps"): vol.All(int, vol.Range(min=-10, max=10))},
    {vol.Required("kind"): "text", vol.Required("text"): vol.All(str, vol.Length(min=1, max=2000))},
    {
        vol.Required("kind"): "shortcut",
        vol.Required("key"): vol.In(
            [
                "escape",
                "enter",
                "backspace",
                "tab",
                "delete",
                "alt_f4",
                "task_manager",
                "alt_tab",
                "show_desktop",
                "select_all",
                "copy",
                "paste",
            ]
        ),
    },
)


async def handle_input(hass, connection, msg):
    entity_id = msg["entity_id"]
    if not connection.user.permissions.check_entity(entity_id, POLICY_CONTROL):
        connection.send_error(msg["id"], "unauthorized", "No permission to control this computer")
        return
    entity = er.async_get(hass).async_get(entity_id)
    if entity is None or entity.platform != DOMAIN or not entity_id.startswith("remote."):
        connection.send_error(msg["id"], "invalid_entity", "Select a Plex PC Remote entity")
        return
    entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    coordinator = getattr(entry, "runtime_data", None) if entry else None
    if coordinator is None or not coordinator.last_update_success:
        connection.send_error(msg["id"], "unavailable", "Windows server is unavailable")
        return
    try:
        await coordinator.desktop_input(msg["payload"])
    except HomeAssistantError as exc:
        connection.send_error(msg["id"], "input_failed", str(exc))
    else:
        connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "plex_pc_remote/input",
        vol.Required("entity_id"): str,
        vol.Required("payload"): PAYLOAD,
    }
)
@websocket_api.async_response
async def websocket_input(hass, connection, msg):
    await handle_input(hass, connection, msg)


def async_register_input(hass):
    websocket_api.async_register_command(hass, websocket_input)
