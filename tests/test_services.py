"""The three actions, targeting, and what happens when the Mac says no."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.charmling.const import CONF_MAC_NAME, CONF_NODE, CONF_SECRET, CONF_WEBHOOK_ID, DOMAIN

from .conftest import BASE, NODE, STATES


def calls_to(mac, path: str):
    return [c for c in mac.mock_calls if str(c[1]).endswith(path)]


async def test_say(hass: HomeAssistant, paired, mac) -> None:
    await hass.services.async_call(DOMAIN, "say", {"message": "🔔 door", "category": "arrival", "sound": False}, blocking=True)
    (call,) = calls_to(mac, "/say")
    assert call[2] == {"as": "arrival", "say": "🔔 door", "sound": False}
    assert call[3]["Authorization"] == "Bearer s3cr3t-token-from-pairing"


async def test_say_defaults_and_one_line(hass: HomeAssistant, paired, mac) -> None:
    await hass.services.async_call(DOMAIN, "say", {"message": "water\nleak\t basement"}, blocking=True)
    (call,) = calls_to(mac, "/say")
    assert call[2] == {"as": "alert", "say": "water leak basement", "sound": True}


async def test_say_validates(hass: HomeAssistant, paired) -> None:
    with pytest.raises(Exception):  # noqa: B017 — vol.Invalid wrapped by the service layer
        await hass.services.async_call(DOMAIN, "say", {"message": "", "category": "shout"}, blocking=True)
    with pytest.raises(Exception):  # noqa: B017
        await hass.services.async_call(DOMAIN, "say", {"message": "x" * 201}, blocking=True)


async def test_water_and_do(hass: HomeAssistant, paired, mac) -> None:
    await hass.services.async_call(DOMAIN, "water", {"plant": "dragon"}, blocking=True)
    assert calls_to(mac, "/water")[0][2] == {"plant": "dragon"}
    await hass.services.async_call(DOMAIN, "do", {"action": "focus", "minutes": 40}, blocking=True)
    assert calls_to(mac, "/do")[0][2] == {"action": "focus", "minutes": 40}
    await hass.services.async_call(DOMAIN, "do", {"action": "trick"}, blocking=True)
    assert calls_to(mac, "/do")[1][2] == {"action": "trick"}
    with pytest.raises(Exception):  # noqa: B017
        await hass.services.async_call(DOMAIN, "do", {"action": "dance"}, blocking=True)
    with pytest.raises(Exception):  # noqa: B017
        await hass.services.async_call(DOMAIN, "do", {"action": "focus", "minutes": 999}, blocking=True)


async def test_no_mac_paired(hass: HomeAssistant, paired) -> None:
    """The services outlive the entries; with none loaded they say so instead of crashing."""
    await hass.config_entries.async_unload(paired.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "say")
    with pytest.raises(ServiceValidationError, match="No Mac"):
        await hass.services.async_call(DOMAIN, "say", {"message": "hi"}, blocking=True)


async def test_two_macs_need_a_target(hass: HomeAssistant, paired, aioclient_mock) -> None:
    other = MockConfigEntry(
        domain=DOMAIN, unique_id="other-mac", title="Charmling on Studio",
        data={CONF_HOST: "192.0.2.20", CONF_PORT: 41417, CONF_NODE: "other-mac", CONF_MAC_NAME: "Studio",
              CONF_SECRET: "other-secret", CONF_WEBHOOK_ID: "f" * 32},
    )
    aioclient_mock.get("http://192.0.2.20:41417/state", json={"states": STATES})
    aioclient_mock.post("http://192.0.2.20:41417/say", json={"ok": True})
    other.add_to_hass(hass)
    assert await hass.config_entries.async_setup(other.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError, match="choose one"):
        await hass.services.async_call(DOMAIN, "say", {"message": "hi"}, blocking=True)

    registry = dr.async_get(hass)
    studio = registry.async_get_device(identifiers={(DOMAIN, "other-mac")})
    await hass.services.async_call(DOMAIN, "say", {"message": "hi studio", "device_id": studio.id}, blocking=True)
    said = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/say")]
    assert len(said) == 1
    assert str(said[0][1]).startswith("http://192.0.2.20")

    mac1 = registry.async_get_device(identifiers={(DOMAIN, NODE)})
    await hass.services.async_call(DOMAIN, "say", {"message": "both", "device_id": [mac1.id, studio.id]}, blocking=True)
    said = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/say")]
    assert len(said) == 3

    with pytest.raises(ServiceValidationError, match="no device"):
        await hass.services.async_call(DOMAIN, "say", {"message": "hi", "device_id": "nope"}, blocking=True)


async def test_every_target_is_tried(hass: HomeAssistant, paired, aioclient_mock) -> None:
    """Mac 1 asleep must not stop Mac 2 from hearing it; the error names the sleeper."""
    other = MockConfigEntry(
        domain=DOMAIN, unique_id="other-mac", title="Charmling on Studio",
        data={CONF_HOST: "192.0.2.20", CONF_PORT: 41417, CONF_NODE: "other-mac", CONF_MAC_NAME: "Studio",
              CONF_SECRET: "other-secret", CONF_WEBHOOK_ID: "f" * 32},
    )
    aioclient_mock.get("http://192.0.2.20:41417/state", json={"states": STATES})
    aioclient_mock.post("http://192.0.2.20:41417/say", json={"ok": True})
    other.add_to_hass(hass)
    assert await hass.config_entries.async_setup(other.entry_id)
    await hass.async_block_till_done()
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{BASE}/say", exc=TimeoutError())
    aioclient_mock.post("http://192.0.2.20:41417/say", json={"ok": True})
    registry = dr.async_get(hass)
    ids = [registry.async_get_device(identifiers={(DOMAIN, NODE)}).id, registry.async_get_device(identifiers={(DOMAIN, "other-mac")}).id]
    with pytest.raises(HomeAssistantError, match="Abi's MacBook Pro"):
        await hass.services.async_call(DOMAIN, "say", {"message": "both", "device_id": ids}, blocking=True)
    said = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/say")]
    assert [str(c[1]).split("//")[1].split(":")[0] for c in said] == ["192.0.2.10", "192.0.2.20"]


async def test_the_mac_refusing_the_secret_starts_a_reauth(hass: HomeAssistant, paired, aioclient_mock) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{BASE}/say", status=401)
    with pytest.raises(HomeAssistantError, match="no longer accepts"):
        await hass.services.async_call(DOMAIN, "say", {"message": "hi"}, blocking=True)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == "reauth"
    # a second refusal does not open a second flow
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "say", {"message": "hi"}, blocking=True)
    await hass.async_block_till_done()
    assert len(hass.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1


async def test_the_mac_saying_not_now(hass: HomeAssistant, paired, aioclient_mock) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{BASE}/do", status=409, json={"error": "cannot do that right now"})
    with pytest.raises(HomeAssistantError, match="cannot do that right now"):
        await hass.services.async_call(DOMAIN, "do", {"action": "trick"}, blocking=True)
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)


async def test_the_mac_unreachable(hass: HomeAssistant, paired, aioclient_mock) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{BASE}/water", exc=TimeoutError())
    with pytest.raises(HomeAssistantError, match="could not be reached"):
        await hass.services.async_call(DOMAIN, "water", {"plant": "bonsai"}, blocking=True)
