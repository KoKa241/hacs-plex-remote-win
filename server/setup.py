"""Generate private configuration and install explicit Plex HTPC key bindings."""

import argparse
import json
import os
import secrets
import uuid
from pathlib import Path

from .bindings import install_bindings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plex-path", default=r"C:\Program Files\Plex\Plex HTPC\Plex HTPC.exe")
    args = parser.parse_args()
    executable = Path(args.plex_path)
    if not executable.is_file() or executable.name.lower() != "plex htpc.exe":
        parser.error("Specify the full path to Plex HTPC.exe")
    target = Path(__file__).parent / "config.json"
    if not target.exists():
        target.write_text(
            json.dumps(
                {
                    "plex_path": str(executable),
                    "host": "0.0.0.0",
                    "port": 8321,
                    "server_id": str(uuid.uuid4()),
                    "token": secrets.token_urlsafe(32),
                },
                indent=2,
            )
        )
    folder = Path(os.environ["LOCALAPPDATA"]) / "Plex HTPC" / "inputmaps"
    folder.mkdir(parents=True, exist_ok=True)
    mapping = folder / "keyboard.json"
    install_bindings(mapping)
    print(f"Config: {target.resolve()}\nBindings: {mapping}\nRestart Plex HTPC. Token is in config.json.")


if __name__ == "__main__":
    main()
