"""UI setup and credential recovery."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApiError, InvalidAuth, PlexAPI
from .const import DOMAIN


class PlexFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        return await self._form("user", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._form("reauth_confirm", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._form("reconfigure", user_input)

    async def _form(self, step, user_input):
        errors = {}
        if user_input is not None:
            try:
                api = PlexAPI(async_get_clientsession(self.hass), user_input["url"], user_input["token"])
                data = await api.request()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ValueError:
                errors["base"] = "invalid_url"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                if step != "user":
                    entry = (
                        self._get_reauth_entry()
                        if step == "reauth_confirm"
                        else self._get_reconfigure_entry()
                    )
                    if entry.unique_id != data["server_id"]:
                        return self.async_abort(reason="wrong_device")
                    return self.async_update_reload_and_abort(entry, data_updates=user_input)
                await self.async_set_unique_id(data["server_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Plex PC", data=user_input)
        return self.async_show_form(
            step_id=step,
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("url", default="http://192.168.1.100:8321"): str,
                    vol.Required("token"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                }
            ),
        )
