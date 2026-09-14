"""Shared fixtures: a paired Mac, a mocked HTTP side of it, a way to push to the webhook."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.charmling.const import (
    CONF_MAC_NAME,
    CONF_NODE,
    CONF_SECRET,
    CONF_VERSION,
    CONF_WEBHOOK_ID,
    DOMAIN,
)

NODE = "3f1c9a2b7d4e4c6a9b1e2f3a4b5c6d7e"
NAME = "Abi's MacBook Pro"
SECRET = "s3cr3t-token-from-pairing"
WEBHOOK_ID = "0123456789abcdef0123456789abcdef"
HOST, PORT = "192.0.2.10", 41417
BASE = f"http://{HOST}:{PORT}"
P = "abi_s_macbook_pro"

STATES: dict[str, Any] = {
    "on_air": False, "camera": False, "in_call_app": False, "presenting": False,
    "at_desk": True, "screen_locked": False, "idle_seconds": 4, "away_minutes": 0,
    "focus": False, "focus_remaining": 0, "screen_full": False, "work_kind": "coding",
    "next_meeting_minutes": 42, "meeting_density": "light", "wander": False, "charm": "maneki",
    "beads": 2, "basket": 0, "banners_10min": 1, "cord_friends": 0, "pet_out": True,
    "dog": "sitting", "dog_name": "Biscuit", "hushed": False, "muted": False, "leash": "medium",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let HA load custom_components from this repo."""


@pytest.fixture
def entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=NODE,
        title=f"Charmling on {NAME}",
        data={
            CONF_HOST: HOST, CONF_PORT: PORT, CONF_NODE: NODE, CONF_MAC_NAME: NAME,
            CONF_SECRET: SECRET, CONF_WEBHOOK_ID: WEBHOOK_ID, CONF_VERSION: "1.9",
        },
    )


@pytest.fixture
def mac(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """The Mac's endpoints, answering happily."""
    aioclient_mock.get(f"{BASE}/id", json={"id": NODE, "name": NAME, "version": "1.9", "paired": True})
    aioclient_mock.get(f"{BASE}/state", json={"id": NODE, "name": NAME, "version": "1.9", "states": STATES})
    aioclient_mock.post(f"{BASE}/say", json={"ok": True})
    aioclient_mock.post(f"{BASE}/water", json={"ok": True})
    aioclient_mock.post(f"{BASE}/do", json={"ok": True})
    aioclient_mock.post(f"{BASE}/unpair", json={"ok": True})
    return aioclient_mock


@pytest.fixture
async def paired(hass: HomeAssistant, entry: MockConfigEntry, mac: AiohttpClientMocker) -> MockConfigEntry:
    """A set-up entry with a reachable Mac."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def push(hass: HomeAssistant, hass_client_no_auth) -> Callable[..., Awaitable[int]]:
    """POST a message to the entry's webhook as the Mac would; returns the status."""
    client = await hass_client_no_auth()

    async def _push(body: Any, secret: str = SECRET, webhook_id: str = WEBHOOK_ID, raw: bytes | None = None) -> int:
        headers = {"X-Charmling-Secret": secret}
        if raw is not None:
            resp = await client.post(f"/api/webhook/{webhook_id}", data=raw, headers=headers)
        else:
            resp = await client.post(f"/api/webhook/{webhook_id}", json=body, headers=headers)
        await hass.async_block_till_done()
        return resp.status

    return _push
