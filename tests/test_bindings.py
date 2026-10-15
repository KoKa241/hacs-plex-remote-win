import json
import time
from unittest.mock import Mock

import pytest
from test_control import FakeBackend

from server.bindings import PROFILE, bindings_match, install_bindings
from server.control import KEYS, ControlError, Controller


def test_install_updates_old_map_and_preserves_backup(tmp_path):
    target = tmp_path / "inputmaps" / "keyboard.json"
    target.parent.mkdir()
    old = '{"mapping":{"F11":"increase_volume"}}'
    target.write_text(old)
    started = time.time() - 1
    assert install_bindings(target)
    assert bindings_match(target)
    assert target.stat().st_mtime > started
    backups = list(target.parent.glob("*.bak"))
    assert len(backups) == 1 and backups[0].read_text() == old
    mtime = target.stat().st_mtime
    assert not install_bindings(target)
    assert target.stat().st_mtime == mtime


def test_no_standard_function_shortcut_collisions():
    assert all(not any(0x70 <= key <= 0x7B for key in keys) for keys in KEYS.values())
    assert KEYS["volume_up"] != KEYS["fullscreen"]
    assert KEYS["play_pause"] != KEYS["play"]
    mapping = json.loads(PROFILE.read_text())["mapping"]
    assert mapping["F13"] == "play_pause"
    assert mapping["F23"] == "increase_volume"


def test_pending_restart_blocks_keys_but_allows_power_cycle():
    backend = FakeBackend()
    backend.on = True
    backend.input_ready = Mock(return_value=False)
    controller = Controller(backend, "pc")
    assert not controller.status()["input_ready"]
    with pytest.raises(ControlError, match="Restart Plex"):
        controller.command("volume_up")
    assert not backend.calls
    controller.command("turn_off")
    controller.command("turn_on")
    backend.input_ready.return_value = True
    controller.command("volume_up")
    assert backend.calls == ["close", "start", "focus", KEYS["volume_up"]]
