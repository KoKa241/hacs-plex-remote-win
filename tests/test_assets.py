import json
import re
from pathlib import Path

import yaml

from server.control import COMMANDS, KEYS

ROOT = Path(__file__).resolve().parents[1]


def test_card_commands_exist():
    card = yaml.safe_load((ROOT / "examples/remote-card.yaml").read_text())
    for row in card["cards"][1:]:
        for button in row["cards"]:
            assert button["tap_action"]["data"]["command"] in COMMANDS


def test_bindings_cover_server_keys():
    mapping = json.loads((ROOT / "server/keyboard.json").read_text())["mapping"]
    names = {0x26: "Up", 0x28: "Down", 0x25: "Left", 0x27: "Right", 0x0D: "Return", 0x1B: "Esc"}
    names.update({0x6F + i: f"F{i}" for i in range(1, 13)})
    for command, keys in KEYS.items():
        name = ("Ctrl+" if len(keys) > 1 else "") + names[keys[-1]]
        matches = [action for pattern, action in mapping.items() if re.fullmatch(pattern, name)]
        assert len(matches) == 1, (command, name, matches)
    assert not {"poweroff", "reboot", "suspend", "exit"} & set(mapping.values())
