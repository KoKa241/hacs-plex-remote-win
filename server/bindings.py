"""Install our keyboard profile and detect when Plex must reload it."""

import json
import os
import shutil
import time
from pathlib import Path

PROFILE = Path(__file__).with_name("keyboard.json")


def bindings_match(target):
    try:
        return json.loads(Path(target).read_text(encoding="utf-8")) == json.loads(
            PROFILE.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return False


def install_bindings(target):
    """Return True only when the file changed. Never erase a previous profile."""
    target = Path(target)
    if bindings_match(target):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, target.with_name(f"keyboard.backup-{time.time_ns()}.json.bak"))
    temporary = target.with_suffix(".json.tmp")
    shutil.copy2(PROFILE, temporary)
    os.utime(temporary, None)
    temporary.replace(target)
    return True
