"""Allowlisted Plex commands; no arbitrary shell or computer power actions."""

import threading

# Dedicated bindings installed by setup.py; navigation uses real arrow/Esc keys.
KEYS = {
    "up": (0x26,),
    "down": (0x28,),
    "left": (0x25,),
    "right": (0x27,),
    "select": (0x0D,),
    "back": (0x1B,),
    "play_pause": (0x7C,),
    "play": (0x7D,),
    "pause": (0x7E,),
    "stop": (0x7F,),
    "seek_backward": (0x80,),
    "seek_forward": (0x81,),
    "previous": (0x82,),
    "next": (0x83,),
    "home": (0x84,),
    "volume_down": (0x85,),
    "volume_up": (0x86,),
    "mute": (0x87,),
    "subtitles": (0x11, 0x7C),
    "audio": (0x11, 0x7D),
    "fullscreen": (0x11, 0x7E),
    "info": (0x11, 0x7F),
}
COMMANDS = frozenset(KEYS) | {"turn_on", "turn_off", "toggle", "focus"}


class ControlError(Exception):
    """An action could not safely be performed."""


class Controller:
    def __init__(self, backend, server_id):
        self.backend = backend
        self.server_id = server_id
        self.lock = threading.Lock()

    def status(self):
        with self.lock:
            return self._status()

    def _status(self):
        return {
            "server_id": self.server_id,
            "running": self.backend.running(),
            "version": "1.2.1",
            "desktop_input": True,
            "input_ready": self.backend.input_ready(),
            "commands": sorted(COMMANDS),
        }

    def command(self, command):
        if command not in COMMANDS:
            raise ValueError("Unsupported command")
        with self.lock:
            if command == "toggle":
                command = "turn_off" if self.backend.running() else "turn_on"
            if command == "turn_on":
                self.backend.start()
            elif command == "turn_off":
                self.backend.close()
            else:
                if not self.backend.running():
                    raise ControlError("Plex is not running")
                if command != "focus" and not self.backend.input_ready():
                    raise ControlError("Restart Plex HTPC to load the updated remote keyboard profile")
                self.backend.focus()
                if command != "focus":
                    self.backend.press(KEYS[command])
            return self._status()

    def desktop_input(self, action):
        # Desktop actions intentionally target the currently active Windows app.
        # Do not call focus(), start(), or apply Plex's inputmap here.
        with self.lock:
            self.backend.desktop_input(action)
        return {"ok": True, "server_id": self.server_id}
