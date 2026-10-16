"""Small async client shared by flow and entities."""

from urllib.parse import urlsplit

import aiohttp


class ApiError(Exception):
    """Server error."""


class InvalidAuth(ApiError):
    """Invalid token."""


def validate_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ValueError("Use http(s)://host:port without a path or credentials")
    _ = parsed.port
    return url.rstrip("/")


class PlexAPI:
    def __init__(self, session, url, token):
        self.session = session
        self.url = validate_url(url)
        self.token = token

    async def request(self, command=None):
        path = "/api/status" if command is None else "/api/command"
        kwargs = {} if command is None else {"json": {"command": command}}
        try:
            async with self.session.request(
                "GET" if command is None else "POST",
                self.url + path,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=aiohttp.ClientTimeout(total=25),
                allow_redirects=False,
                **kwargs,
            ) as response:
                if response.status == 401:
                    raise InvalidAuth("Invalid API token")
                if response.status != 200:
                    raise ApiError(f"Server returned HTTP {response.status}")
                data = await response.json()
                if (
                    not isinstance(data, dict)
                    or not isinstance(data.get("running"), bool)
                    or not isinstance(data.get("server_id"), str)
                    or not data["server_id"]
                ):
                    raise ApiError("Invalid server response")
                return data
        except (TimeoutError, aiohttp.ClientError, ValueError) as exc:
            raise ApiError("Cannot communicate with Plex PC Remote") from exc

    async def input(self, payload):
        try:
            async with self.session.post(
                self.url + "/api/input",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=aiohttp.ClientTimeout(total=5),
                allow_redirects=False,
            ) as response:
                if response.status == 401:
                    raise InvalidAuth("Invalid API token")
                if response.status != 200:
                    raise ApiError(f"Windows input failed (HTTP {response.status})")
                data = await response.json()
                if not isinstance(data, dict) or data.get("ok") is not True:
                    raise ApiError("Invalid desktop input response")
                return data
        except (TimeoutError, aiohttp.ClientError, ValueError) as exc:
            raise ApiError("Desktop input was not confirmed; not retried automatically") from exc
