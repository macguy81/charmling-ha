"""Charmling for Home Assistant.

The Mac pushes: every change to a state the second it happens, moment
events (a call started, the dog woofed), a heartbeat every thirty seconds.
Nothing is polled. The webhook is the only way in; the secret from pairing
is the only key. The house talks back through three services, and whatever
is on the cord says it in its own way.

State leaves the Mac; content never does.
"""

from __future__ import annotations

import asyncio
import hmac
import logging
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Any

import voluptuous as vol
from aiohttp.web import Request, Response
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import CharmlingApi
from .const import (
    ACTIONS,
    CATEGORIES,
    CONF_MAC_NAME,
    CONF_NODE,
    CONF_SECRET,
    CONF_VERSION,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_NAME,
    MANUFACTURER,
    MODEL,
    PLANTS,
)
from .coordinator import CharmlingData
from .helpers import async_ask

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.EVENT,
    Platform.BUTTON,
    Platform.SWITCH,
]

SECRET_HEADER = "X-Charmling-Secret"
MAX_STATES = 200            # a Mac sends ~30 keys; anything wilder is not a Mac
MAX_TEXT = 200

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type CharmlingConfigEntry = ConfigEntry[CharmlingData]

SERVICE_SAY = "say"
SERVICE_WATER = "water"
SERVICE_DO = "do"

_DEVICE = vol.Optional("device_id")
_DEVICE_IDS = vol.Any(cv.string, [cv.string])
SCHEMA_SAY = vol.Schema({
    _DEVICE: _DEVICE_IDS,
    vol.Required("message"): vol.All(cv.string, vol.Length(min=1, max=MAX_TEXT)),
    vol.Optional("category", default="alert"): vol.In(CATEGORIES),
    vol.Optional("sound", default=True): cv.boolean,
})
SCHEMA_WATER = vol.Schema({
    _DEVICE: _DEVICE_IDS,
    vol.Required("plant"): vol.In(PLANTS),
})
SCHEMA_DO = vol.Schema({
    _DEVICE: _DEVICE_IDS,
    vol.Required("action"): vol.In(ACTIONS),
    vol.Optional("minutes"): vol.All(vol.Coerce(int), vol.Range(min=1, max=180)),
})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """The services exist once, for every paired Mac."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CharmlingConfigEntry) -> bool:
    """One paired Mac."""
    session = async_get_clientsession(hass)
    api = CharmlingApi(session, entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_SECRET])
    data = CharmlingData(hass, entry, api, entry.data[CONF_NODE], entry.data[CONF_MAC_NAME])
    data.version = entry.data.get(CONF_VERSION, "")
    entry.runtime_data = data

    # the device exists before any entity does, so the Mac shows up in
    # Devices the moment pairing finishes, even if it is asleep right now
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, data.node)},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name=data.name,
        sw_version=data.version or None,
    )

    webhook_id = entry.data[CONF_WEBHOOK_ID]
    webhook.async_register(
        hass, DOMAIN, f"Charmling on {data.name}", webhook_id,
        _make_webhook_handler(entry), allowed_methods=["POST"],
        # not local_only: a Mac on Tailscale or a VLAN is not "local" to HA's
        # eye, and the secret in the header is the real gate anyway
        local_only=False,
    )
    entry.async_on_unload(lambda: webhook.async_unregister(hass, webhook_id))
    entry.async_on_unload(data.async_stop)

    await data.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CharmlingConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Deleted in HA: tell the Mac so its pane shows a code again."""
    api = CharmlingApi(async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_SECRET])
    await api.unpair()


# ---------------------------------------------------------------- webhook


def _make_webhook_handler(entry: CharmlingConfigEntry) -> Callable[[HomeAssistant, str, Request], Awaitable[Response]]:
    async def handle(hass: HomeAssistant, webhook_id: str, request: Request) -> Response:
        given = request.headers.get(SECRET_HEADER, "")
        if not hmac.compare_digest(given.encode(), entry.data[CONF_SECRET].encode()):
            _LOGGER.warning("Charmling webhook for %s: wrong secret from %s", entry.title, request.remote)
            return Response(status=HTTPStatus.UNAUTHORIZED)
        try:
            body = await request.json()
        except ValueError:
            return Response(status=HTTPStatus.BAD_REQUEST, text="json please")
        if not isinstance(body, dict):
            return Response(status=HTTPStatus.BAD_REQUEST, text="object please")
        _handle_message(hass, entry, body)
        return Response(status=HTTPStatus.OK, text="ok")

    return handle


def _one_line(text: str) -> str:
    """A line the charm can show: no control characters, whitespace folded."""
    return " ".join(text.split())


def _clean_states(raw: Any) -> dict[str, Any]:
    """Only scalars, only sane sizes: what a Mac sends, nothing an attacker could."""
    if not isinstance(raw, dict) or len(raw) > MAX_STATES:
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or len(key) > 64:
            continue
        if isinstance(value, bool | int | float) or value is None:
            out[key] = value
        elif isinstance(value, str):
            out[key] = value[:MAX_TEXT]
    return out


@callback
def _handle_message(hass: HomeAssistant, entry: CharmlingConfigEntry, body: dict[str, Any]) -> None:
    data = entry.runtime_data
    kind = body.get("type")
    if kind == "state":
        data.apply(_clean_states(body.get("states")))
        data.mark_seen()
    elif kind == "event":
        event_type = str(body.get("event", ""))[:64]
        if not event_type:
            return
        payload = _clean_states({k: v for k, v in body.items() if k not in ("type", "event")})
        data.event(event_type, payload)
        hass.bus.async_fire(EVENT_NAME, {
            **payload,
            "type": event_type,
            "node": data.node,
            "device_id": data.device_id,
        })
        data.mark_seen()
    elif kind == "hello":
        data.set_version(str(body.get("version", ""))[:32])
        data.set_name(str(body.get("name", ""))[:80])
        data.apply(_clean_states(body.get("states")))
        data.mark_seen()
    elif kind == "bye":
        data.mark_gone()
    elif kind == "ping":
        data.mark_seen()
    else:
        _LOGGER.debug("Charmling on %s sent something new: %s", data.name, kind)


# --------------------------------------------------------------- services


def _entries_for_call(hass: HomeAssistant, call: ServiceCall) -> list[CharmlingConfigEntry]:
    """Which Macs a service call means: the targeted devices, or the only one."""
    loaded = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    wanted = call.data.get("device_id")
    if not wanted:
        if len(loaded) == 1:
            return loaded
        if not loaded:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_mac")
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="pick_a_mac")
    if isinstance(wanted, str):
        wanted = [wanted]
    registry = dr.async_get(hass)
    out: list[CharmlingConfigEntry] = []
    for device_id in wanted:
        device = registry.async_get(device_id)
        if device is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="unknown_device",
                translation_placeholders={"device_id": device_id},
            )
        for e in loaded:
            if e.entry_id in device.config_entries and e not in out:
                out.append(e)
    if not out:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_a_mac")
    return out


async def _ask_all(hass: HomeAssistant, call: ServiceCall, what: str, make: Callable[[CharmlingApi], Awaitable[object]]) -> None:
    """Every targeted Mac is asked, even if an earlier one is asleep; then one error for all that failed."""
    entries = _entries_for_call(hass, call)
    results = await asyncio.gather(
        *(async_ask(e.runtime_data, what, make(e.runtime_data.api)) for e in entries), return_exceptions=True
    )
    failed = [r for r in results if isinstance(r, Exception)]
    if not failed:
        return
    if len(failed) == 1:
        raise failed[0]
    raise HomeAssistantError("; ".join(str(r) for r in failed))


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    async def say(call: ServiceCall) -> None:
        text = _one_line(call.data["message"])
        await _ask_all(hass, call, "say", lambda api: api.say(call.data["category"], text, call.data["sound"]))

    async def water(call: ServiceCall) -> None:
        await _ask_all(hass, call, "water", lambda api: api.water(call.data["plant"]))

    async def do(call: ServiceCall) -> None:
        extra = {"minutes": call.data["minutes"]} if "minutes" in call.data else {}
        await _ask_all(hass, call, call.data["action"], lambda api: api.do(call.data["action"], **extra))

    hass.services.async_register(DOMAIN, SERVICE_SAY, say, schema=SCHEMA_SAY)
    hass.services.async_register(DOMAIN, SERVICE_WATER, water, schema=SCHEMA_WATER)
    hass.services.async_register(DOMAIN, SERVICE_DO, do, schema=SCHEMA_DO)
