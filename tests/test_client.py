"""Exercise the actual HA HTTP client against a local aiohttp endpoint."""

import asyncio
import importlib.util
from pathlib import Path

import aiohttp
import pytest
from aiohttp import web

spec = importlib.util.spec_from_file_location(
    "plex_client", Path(__file__).resolve().parents[1] / "custom_components/plex_pc_remote/api.py"
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://user:pass@localhost",
        "http://localhost/x",
        "http://localhost?token=a",
        "http://localhost:bad",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        api.validate_url(url)


@pytest.mark.parametrize(
    "status,payload,error",
    [
        (401, {}, api.InvalidAuth),
        (409, {}, api.ApiError),
        (503, {}, api.ApiError),
        (200, {"running": "false", "server_id": "pc"}, api.ApiError),
        (200, {"running": False}, api.ApiError),
        (200, {"running": False, "server_id": "pc"}, None),
    ],
)
def test_client_responses(status, payload, error):
    async def run():
        async def handler(request):
            assert request.headers["Authorization"] == "Bearer secret"
            if request.method == "POST":
                assert await request.json() == {"command": "back"}
            return web.json_response(payload, status=status)

        app = web.Application()
        app.router.add_get("/api/status", handler)
        app.router.add_post("/api/command", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        try:
            await site.start()
            port = site._server.sockets[0].getsockname()[1]
            async with aiohttp.ClientSession() as session:
                client = api.PlexAPI(session, f"http://127.0.0.1:{port}/", "secret")
                for command in (None, "back"):
                    if error:
                        with pytest.raises(error):
                            await client.request(command)
                    else:
                        assert await client.request(command) == payload
        finally:
            await runner.cleanup()

    asyncio.run(run())
