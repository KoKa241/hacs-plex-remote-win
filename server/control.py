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
    "play_pause": (0x70,),
    "play": (0x71,),
    "pause": (0x72,),
    "stop": (0x73,),
    "seek_backward": (0x74,),
    "seek_forward": (0x75,),
    "previous": (0x76,),
    "next": (0x77,),
    "home": (0x78,),
    "volume_down": (0x79,),
    "volume_up": (0x7A,),
    "mute": (0x7B,),
    "subtitles": (0x11, 0x70),
    "audio": (0x11, 0x71),
    "fullscreen": (0x11, 0x72),
    "info": (0x11, 0x73),
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
            "version": "1.0.0",
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
                self.backend.focus()
                if command != "focus":
                    self.backend.press(KEYS[command])
            return self._status()
