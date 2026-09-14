"""Talking to the Mac: a small local HTTP API Charmling serves on the LAN.

Every call carries the shared secret from pairing as a bearer token. The
Mac answers in JSON. Nothing here ever fetches a title or a line of text;
the Mac's /state is the same set of states it pushes to the webhook.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=6)


class CharmlingError(Exception):
    """The Mac could not be reached or refused."""


class CharmlingAuthError(CharmlingError):
    """The secret (or the pairing code) was refused."""


class CharmlingConflictError(CharmlingError):
    """The Mac at that address is not the Mac we meant."""


class CharmlingApi:
    """The Mac's endpoints."""

    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, secret: str | None = None) -> None:
        self._session = session
        self.host = host
        self.port = port
        self.secret = secret

    @property
    def base(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}"

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.secret:
            h["Authorization"] = f"Bearer {self.secret}"
        return h

    async def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self._session.request(
                method, f"{self.base}{path}", json=body, headers=self._headers(), timeout=TIMEOUT
            ) as resp:
                if resp.status in (401, 403):
                    raise CharmlingAuthError(f"{path}: refused ({resp.status})")
                if resp.status == 409:
                    raise CharmlingConflictError(f"{path}: not that Mac")
                if resp.status >= 400:
                    text = await resp.text()
                    raise CharmlingError(f"{path}: HTTP {resp.status} {text[:120]}")
                if resp.content_type == "application/json":
                    return await resp.json()
                return {}
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CharmlingError(f"cannot reach the Mac at {self.base}: {err}") from err

    async def identify(self) -> dict[str, Any]:
        """Who is at this address: id, name, version, paired. No secret needed; it is what Bonjour says anyway."""
        return await self._request("GET", "/id")

    async def pair(self, code: str, webhook_url: str, webhook_id: str, expect_id: str | None = None) -> dict[str, Any]:
        """Exchange the six-digit code shown in Charmling for the secret.

        With expect_id, the Mac refuses (and changes nothing) if it is not that Mac,
        so a re-pair aimed at the wrong address cannot hijack another Mac's pairing.
        """
        body = {"code": code, "webhook_url": webhook_url, "webhook_id": webhook_id}
        if expect_id:
            body["expect_id"] = expect_id
        return await self._request("POST", "/pair", body)

    async def state(self) -> dict[str, Any]:
        return await self._request("GET", "/state")

    async def say(self, category: str, text: str, sound: bool = True) -> None:
        await self._request("POST", "/say", {"as": category, "say": text, "sound": sound})

    async def water(self, plant: str) -> None:
        await self._request("POST", "/water", {"plant": plant})

    async def do(self, action: str, **kwargs: Any) -> None:
        await self._request("POST", "/do", {"action": action, **kwargs})

    async def unpair(self) -> None:
        """Best effort: the Mac may be asleep, and its own 401 handling covers that."""
        with contextlib.suppress(CharmlingError):
            await self._request("POST", "/unpair")
