"""Authenticated LAN API. Run: python -m server.app --config server/config.json."""

import argparse
import json
import logging
import secrets
from logging.handlers import RotatingFileHandler
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .control import COMMANDS, ControlError, Controller
from .desktop import DesktopAction


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(min_length=1, max_length=32)


def create_app(controller, token):
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("API token must contain at least 32 characters")
    app = FastAPI(title="Plex PC Remote", docs_url=None, redoc_url=None, openapi_url=None)

    def authenticate(authorization: str = Header(default="")):
        if not secrets.compare_digest(authorization.encode(), f"Bearer {token}".encode()):
            raise HTTPException(401, "Invalid token")

    @app.get("/api/status", dependencies=[Depends(authenticate)])
    def status():
        return controller.status()

    @app.post("/api/command", dependencies=[Depends(authenticate)])
    def command(body: Command):
        if body.command not in COMMANDS:
            raise HTTPException(422, "Unsupported command")
        try:
            return controller.command(body.command)
        except ControlError as exc:
            raise HTTPException(409, str(exc)) from exc
        except Exception as exc:
            logging.getLogger(__name__).exception("Plex command failed")
            raise HTTPException(503, "Windows action failed; check server log") from exc

    @app.post("/api/input", dependencies=[Depends(authenticate)])
    def desktop_input(body: DesktopAction):
        try:
            return controller.desktop_input(body)
        except (ControlError, UnicodeError) as exc:
            raise HTTPException(409, str(exc)) from exc
        except Exception as exc:
            # Do not log request bodies (typed text may contain private data).
            logging.getLogger(__name__).error("Desktop input failed: %s", type(exc).__name__)
            raise HTTPException(503, "Windows input failed") from exc

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("server/config.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    handler = RotatingFileHandler(
        args.config.with_suffix(".log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    from .windows import WindowsBackend

    controller = Controller(WindowsBackend(config["plex_path"]), config["server_id"])
    uvicorn.run(
        create_app(controller, config["token"]),
        host=config.get("host", "0.0.0.0"),
        port=config.get("port", 8321),
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
