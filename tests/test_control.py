from concurrent.futures import ThreadPoolExecutor

import pytest

from server.control import COMMANDS, KEYS, ControlError, Controller


class FakeBackend:
    def __init__(self):
        self.on = False
        self.calls = []
        self.focus_allowed = True

    def input_ready(self):
        return True

    def running(self):
        return self.on

    def start(self):
        self.on = True
        self.calls.append("start")

    def close(self):
        self.on = False
        self.calls.append("close")

    def focus(self):
        if not self.focus_allowed:
            raise ControlError("Focus denied")
        self.calls.append("focus")

    def press(self, keys):
        self.calls.append(keys)


@pytest.fixture
def controller():
    return Controller(FakeBackend(), "test-pc")


def test_power_only_controls_plex(controller):
    assert not controller.status()["running"]
    assert controller.command("toggle")["running"]
    assert not controller.command("toggle")["running"]
    assert controller.backend.calls == ["start", "close"]


@pytest.mark.parametrize("command", ["shutdown", "sleep", "reboot", "cmd", "powershell", ""])
def test_unknown_commands_have_no_effect(controller, command):
    with pytest.raises(ValueError):
        controller.command(command)
    assert controller.backend.calls == []


def test_no_input_when_off(controller):
    with pytest.raises(ControlError):
        controller.command("up")
    assert controller.backend.calls == []


def test_back_is_escape(controller):
    controller.command("turn_on")
    controller.command("back")
    assert controller.backend.calls[-2:] == ["focus", (0x1B,)]


def test_focus_failure_does_not_send_input(controller):
    controller.command("turn_on")
    controller.backend.focus_allowed = False
    with pytest.raises(ControlError):
        controller.command("select")
    assert controller.backend.calls == ["start"]


def test_concurrent_toggles_are_serialized(controller):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(controller.command, ["toggle"] * 40))
    assert not controller.status()["running"]
    assert controller.backend.calls == ["start", "close"] * 20


def test_every_key_command_requires_focus(controller):
    controller.command("turn_on")
    for command, keys in KEYS.items():
        controller.command(command)
        assert controller.backend.calls[-2:] == ["focus", keys]
    assert set(controller.status()["commands"]) == COMMANDS
