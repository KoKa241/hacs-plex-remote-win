"""Win32 SendInput with pointer-sized structures and Unicode keyboard packets."""

import ctypes as C

from .control import ControlError
from .desktop import SHORTCUTS

DWORD = C.c_uint32
WORD = C.c_uint16
LONG = C.c_int32
ULONG_PTR = C.c_size_t


class MouseInput(C.Structure):
    _fields_ = [
        ("dx", LONG),
        ("dy", LONG),
        ("mouseData", DWORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KeyboardInput(C.Structure):
    _fields_ = [
        ("wVk", WORD),
        ("wScan", WORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HardwareInput(C.Structure):
    _fields_ = [("uMsg", DWORD), ("wParamL", WORD), ("wParamH", WORD)]


class InputUnion(C.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]


class Input(C.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", DWORD), ("data", InputUnion)]


def keyboard(key=0, scan=0, flags=0):
    if key in (0x2E, 0x5B):
        flags |= 1  # Extended Delete/Windows keys.
    return Input(type=1, data=InputUnion(ki=KeyboardInput(key, scan, flags, 0, 0)))


def mouse(flags, dx=0, dy=0, data=0):
    return Input(type=0, data=InputUnion(mi=MouseInput(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)))


def packets(action):
    if action.kind == "move":
        return [mouse(0x0001, action.dx, action.dy)]
    if action.kind == "scroll":
        return [mouse(0x0800, data=action.steps * 120)]
    if action.kind == "click":
        down, up = (0x0002, 0x0004) if action.button == "left" else (0x0008, 0x0010)
        return [mouse(down), mouse(up)]
    if action.kind == "shortcut":
        keys = SHORTCUTS[action.key]
        return [keyboard(k) for k in keys] + [keyboard(k, flags=2) for k in reversed(keys)]
    result = []
    # Windows expects UTF-16 code units, including surrogate pairs for emoji.
    encoded = action.text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-16-le")
    for offset in range(0, len(encoded), 2):
        unit = int.from_bytes(encoded[offset : offset + 2], "little")
        if unit in (9, 10):
            key = 0x09 if unit == 9 else 0x0D
            result.extend([keyboard(key), keyboard(key, flags=2)])
        else:
            result.extend([keyboard(scan=unit, flags=4), keyboard(scan=unit, flags=6)])
    return result


class Point(C.Structure):
    _fields_ = [("x", LONG), ("y", LONG)]


def move_cursor(user32, dx, dy):
    user32.GetCursorPos.argtypes = [C.POINTER(Point)]
    user32.GetCursorPos.restype = C.c_int
    user32.SetCursorPos.argtypes = [C.c_int, C.c_int]
    user32.SetCursorPos.restype = C.c_int
    point = Point()
    if not user32.GetCursorPos(C.byref(point)) or not user32.SetCursorPos(point.x + dx, point.y + dy):
        raise ControlError(
            "Windows cursor unavailable: run the server in the signed-in user's desktop session, "
            "not as a background service; unlock Windows"
        )


def send(action):
    user32 = C.WinDLL("user32", use_last_error=True)
    if action.kind == "move":
        move_cursor(user32, action.dx, action.dy)
        return
    user32.GetAsyncKeyState.argtypes = [C.c_int]
    user32.GetAsyncKeyState.restype = C.c_short
    user32.SendInput.argtypes = [C.c_uint, C.POINTER(Input), C.c_int]
    user32.SendInput.restype = C.c_uint
    if any(user32.GetAsyncKeyState(k) & 0x8000 for k in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
        raise ControlError("Release physical modifier keys before remote input")
    events = packets(action)
    buffer = (Input * len(events))(*events)
    sent = user32.SendInput(len(events), buffer, C.sizeof(Input))
    if sent != len(events):
        # Complete releases after partial insertion; never retry text or presses.
        releases = [
            e
            for e in events
            if (e.type == 1 and e.ki.dwFlags & 2) or (e.type == 0 and e.mi.dwFlags & (0x0004 | 0x0010))
        ]
        if releases:
            user32.SendInput(len(releases), (Input * len(releases))(*releases), C.sizeof(Input))
        raise ControlError("Windows blocked input (locked screen, UAC or higher-privilege application)")
