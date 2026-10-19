import ctypes

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_control import FakeBackend

from server.app import create_app
from server.control import Controller
from server.desktop import ACTION_ADAPTER
from server.native_input import Input, packets


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "move", "dx": 20, "dy": -12},
        {"kind": "click", "button": "right"},
        {"kind": "scroll", "steps": -2},
        {"kind": "text", "text": "Привет 🙂"},
        {"kind": "shortcut", "key": "task_manager"},
        {"kind": "shortcut", "key": "alt_f4"},
    ],
)
def test_desktop_input_works_without_plex_or_focus(payload):
    backend = FakeBackend()
    controller = Controller(backend, "pc")
    client = TestClient(create_app(controller, "x" * 32))
    result = client.post("/api/input", json=payload, headers={"Authorization": "Bearer " + "x" * 32})
    assert result.status_code == 200
    assert result.json() == {"ok": True, "server_id": "pc"}
    assert backend.calls == [payload]
    assert not backend.on


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "move", "dx": 501, "dy": 0},
        {"kind": "move", "dx": True, "dy": 0},
        {"kind": "move", "dx": 1.5, "dy": 0},
        {"kind": "move", "dx": 1, "dy": 0, "shell": "cmd"},
        {"kind": "shortcut", "key": "shutdown"},
        {"kind": "click", "button": "middle"},
        {"kind": "text", "text": "x" * 2001},
        {"kind": "text", "text": ""},
        {"kind": "scroll", "steps": 100},
        {"kind": "key_down", "key": "alt"},
    ],
)
def test_invalid_desktop_payload_rejected(payload):
    with pytest.raises(ValidationError):
        ACTION_ADAPTER.validate_python(payload)


def test_unicode_is_utf16_and_every_unit_released():
    text = "Я🙂"
    events = packets(ACTION_ADAPTER.validate_python({"kind": "text", "text": text}))
    units = [int.from_bytes(text.encode("utf-16-le")[i : i + 2], "little") for i in range(0, 6, 2)]
    assert [e.ki.wScan for e in events[::2]] == units
    assert [e.ki.dwFlags for e in events] == [4, 6] * 3
    assert all(e.ki.wVk == 0 for e in events)
    assert ctypes.sizeof(Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_modifiers_released_in_reverse_order():
    events = packets(ACTION_ADAPTER.validate_python({"kind": "shortcut", "key": "task_manager"}))
    assert [e.ki.wVk for e in events] == [0x11, 0x10, 0x1B, 0x1B, 0x10, 0x11]
    assert [e.ki.dwFlags for e in events] == [0, 0, 0, 2, 2, 2]


def test_click_is_atomic_without_held_state():
    events = packets(ACTION_ADAPTER.validate_python({"kind": "click", "button": "left"}))
    assert [e.mi.dwFlags for e in events] == [2, 4]


def test_text_newlines_become_enter_without_double_crlf():
    events = packets(ACTION_ADAPTER.validate_python({"kind": "text", "text": "\r\n\t"}))
    assert [e.ki.wVk for e in events] == [13, 13, 9, 9]


def test_cursor_moves_from_current_position_and_reports_desktop_failure():
    from unittest.mock import Mock

    from server.control import ControlError
    from server.native_input import Point, move_cursor

    def position(pointer):
        point = ctypes.cast(pointer, ctypes.POINTER(Point)).contents
        point.x, point.y = -200, 400
        return 1

    user32 = Mock()
    user32.GetCursorPos.side_effect = position
    user32.SetCursorPos.return_value = 1
    move_cursor(user32, 30, -20)
    user32.SetCursorPos.assert_called_once_with(-170, 380)
    user32.SetCursorPos.return_value = 0
    with pytest.raises(ControlError, match="desktop session"):
        move_cursor(user32, 10, 10)
    user32.GetCursorPos.side_effect = None
    user32.GetCursorPos.return_value = 0
    user32.SetCursorPos.reset_mock()
    with pytest.raises(ControlError):
        move_cursor(user32, 10, 10)
    user32.SetCursorPos.assert_not_called()


def test_windows_key_is_pressed_and_released():
    events = packets(ACTION_ADAPTER.validate_python({"kind": "shortcut", "key": "windows"}))
    assert [e.ki.wVk for e in events] == [0x5B, 0x5B]
    assert [e.ki.dwFlags for e in events] == [1, 3]
