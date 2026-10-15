"""Run separately with Home Assistant 2025.6.3 installed (Python 3.13)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from homeassistant.components import frontend
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.plex_pc_remote import frontend as ui
from custom_components.plex_pc_remote import homekit as hk
from custom_components.plex_pc_remote.media_player import PlexTV
from custom_components.plex_pc_remote.remote import PlexRemote


@pytest_asyncio.fixture
async def hass(tmp_path):
    instance = HomeAssistant(str(tmp_path))
    await er.async_load(instance)
    yield instance
    await instance.async_stop(force=True)


def coordinator():
    return SimpleNamespace(
        server_id="pc-123",
        data={"running": True, "version": "1.1.0", "input_ready": True},
        command=AsyncMock(),
        last_update_success=True,
    )


@pytest.mark.asyncio
async def test_frontend_registration_and_reload(hass):
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())
    hass.data[frontend.DATA_EXTRA_MODULE_URL] = frontend.UrlManager(lambda *args: None, [])
    await ui.async_setup_frontend(hass)
    await ui.async_setup_frontend(hass)
    assert hass.http.async_register_static_paths.await_count == 1
    assert ui.PANEL_PATH in hass.data[frontend.DATA_PANELS]
    panel = hass.data[frontend.DATA_PANELS][ui.PANEL_PATH]
    assert panel.config["_panel_custom"]["module_url"] == ui.MODULE_URL
    ui.async_remove_panel(hass)
    assert not (ui.PANEL_PATH in hass.data[frontend.DATA_PANELS])
    await ui.async_setup_frontend(hass)
    assert ui.PANEL_PATH in hass.data[frontend.DATA_PANELS]
    assert hass.http.async_register_static_paths.await_count == 1


@pytest.mark.asyncio
async def test_homekit_key_is_scoped_to_exact_tv(hass):
    c = coordinator()
    tv = PlexTV(c)
    tv.entity_id = "media_player.renamed_tv"
    await tv._homekit_key(
        Event("homekit_tv_remote_key_pressed", {"entity_id": "media_player.other", "key_name": "arrow_up"})
    )
    c.command.assert_not_awaited()
    for key, command in [
        ("arrow_up", "up"),
        ("arrow_down", "down"),
        ("arrow_left", "left"),
        ("arrow_right", "right"),
        ("select", "select"),
        ("back", "back"),
        ("exit", "back"),
    ]:
        await tv._homekit_key(
            Event("homekit_tv_remote_key_pressed", {"entity_id": tv.entity_id, "key_name": key})
        )
        c.command.assert_awaited_with(command)


@pytest.mark.asyncio
async def test_play_pause_and_volume_service_dispatch():
    c = coordinator()
    tv = PlexTV(c)
    await tv.async_media_play_pause()
    await tv.async_media_play_pause()
    assert [call.args[0] for call in c.command.await_args_list] == ["play_pause", "play_pause"]
    await tv.async_volume_up()
    c.command.assert_awaited_with("volume_up")
    assert tv.state == "on"  # No invented playback state.


@pytest.mark.asyncio
async def test_actual_homekit_remote_calls_toggle_when_playback_unknown(hass):
    from homeassistant.components.homekit.type_media_players import TelevisionMediaPlayer

    hass.states.async_set("media_player.plex", "on")
    accessory = object.__new__(TelevisionMediaPlayer)
    accessory.hass = hass
    accessory.entity_id = "media_player.plex"
    accessory._supports_play_pause = True
    accessory.async_call_service = Mock()
    accessory.set_remote_key(11)
    accessory.set_remote_key(11)
    assert [call.args[1] for call in accessory.async_call_service.call_args_list] == [
        "media_play_pause",
        "media_play_pause",
    ]


@pytest.mark.asyncio
async def test_remote_resolves_renamed_tv(hass):
    registry = er.async_get(hass)
    tv = registry.async_get_or_create(
        "media_player", "plex_pc_remote", "pc-123_tv", suggested_object_id="renamed"
    )
    remote = PlexRemote(coordinator())
    remote.hass = hass
    assert remote.extra_state_attributes["tv_entity_id"] == tv.entity_id
    assert remote.extra_state_attributes["input_ready"] is True


@pytest.mark.asyncio
async def test_homekit_button_creates_accessory_only_once(hass, monkeypatch):
    from homeassistant.components.homekit import util

    registry = er.async_get(hass)
    tv = registry.async_get_or_create("media_player", "plex_pc_remote", "pc-123_tv")
    hass.states.async_set(tv.entity_id, "on", {"device_class": "tv"})
    entries = []

    async def create(domain, context, data):
        assert domain == "homekit" and context == {"source": "accessory"}
        assert data["entity_id"] == tv.entity_id
        entries.append(
            SimpleNamespace(
                data={"mode": "accessory", "filter": {"include_entities": [tv.entity_id]}}, options={}
            )
        )
        return {"type": "create_entry"}

    hass.config_entries = SimpleNamespace(
        async_entries=lambda domain: entries, flow=SimpleNamespace(async_init=AsyncMock(side_effect=create))
    )
    monkeypatch.setattr(hk, "async_setup_component", AsyncMock(return_value=True))
    monkeypatch.setattr(util, "async_find_next_available_port", lambda *args: 21065)
    monkeypatch.setattr(hk.persistent_notification, "async_create", Mock())
    hk.async_register_homekit_service(hass)
    for _ in range(2):
        await hass.services.async_call(
            "plex_pc_remote", "expose_homekit", {"entity_id": tv.entity_id}, blocking=True
        )
    assert hass.config_entries.flow.async_init.await_count == 1


@pytest.mark.asyncio
async def test_homekit_native_flow_creates_tv_in_accessory_mode(hass):
    from homeassistant.components.homekit.config_flow import HomeKitConfigFlow

    hass.states.async_set(
        "media_player.renamed_tv", "on", {"friendly_name": "Plex PC TV", "device_class": "tv"}
    )
    hass.config_entries = SimpleNamespace(async_entries=lambda *args, **kwargs: [])
    flow = HomeKitConfigFlow()
    flow.hass = hass
    flow.context = {"source": "accessory"}
    result = await flow.async_step_accessory({"entity_id": "media_player.renamed_tv", "port": 21065})
    assert result["type"] == "create_entry"
    assert result["data"]["mode"] == "accessory"
    assert result["data"]["filter"]["include_entities"] == ["media_player.renamed_tv"]
