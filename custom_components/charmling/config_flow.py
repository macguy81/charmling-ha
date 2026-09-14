"""Config flow: find the Mac, type the six-digit code Charmling shows, done.

Four ways in, all ending at the same pair step:
- zeroconf: the Mac was discovered; press Add, type the code
- user: type the Mac's address, then the code
- reauth: the Mac stopped accepting our secret (it was unpaired there); type a new code
- reconfigure: the Mac moved; type its new address, re-pair only if it asks
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components import webhook
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import (
    CharmlingApi,
    CharmlingAuthError,
    CharmlingConflictError,
    CharmlingError,
)
from .const import (
    CONF_MAC_NAME,
    CONF_NODE,
    CONF_SECRET,
    CONF_VERSION,
    CONF_WEBHOOK_ID,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

HOST_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
})
CODE_SCHEMA = vol.Schema({vol.Required("code"): str})


class CharmlingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two steps at most: where the Mac is (usually found for you), and the code."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._node: str | None = None
        self._name: str = "Charmling"
        self._bounce: str | None = None      # an error to show back on the reconfigure form

    # ------------------------------------------------------------ discovery

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Charmling advertises itself as _charmling._tcp with its id and the Mac's name."""
        props = discovery_info.properties
        node = props.get("id")
        if not node:
            return self.async_abort(reason="not_charmling")
        # prefer the IPv4 address; a link-local IPv6 needs a scope id aiohttp will not have
        v4 = [ip for ip in discovery_info.ip_addresses if ip.version == 4]
        self._host = str(v4[0] if v4 else discovery_info.ip_address)
        self._port = discovery_info.port or DEFAULT_PORT
        self._node = node
        self._name = props.get("name") or discovery_info.name.split(".")[0]
        await self.async_set_unique_id(node)
        # already paired: the Mac may have a new address after a DHCP lease, or a new port
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_pair()

    # ---------------------------------------------------------------- manual

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Typed by hand, for a Mac that Bonjour could not see."""
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            return await self.async_step_pair()
        return self.async_show_form(step_id="user", data_schema=HOST_SCHEMA)

    # ---------------------------------------------------------------- reauth

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The Mac refused our secret: it was unpaired there. Pair again, same webhook."""
        self._host = entry_data[CONF_HOST]
        self._port = entry_data[CONF_PORT]
        self._node = entry_data[CONF_NODE]
        self._name = entry_data.get(CONF_MAC_NAME, self._name)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._pair(user_input["code"])
            if not isinstance(result, str):
                return result
            errors["base"] = result
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=CODE_SCHEMA,
            errors=errors,
            description_placeholders={"name": self._name, "host": self._host or ""},
        )

    # ----------------------------------------------------------- reconfigure

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The Mac moved. New address; the old secret is tried first, a code only if it fails."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if self._bounce:
            errors["base"], self._bounce = self._bounce, None
        elif user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            self._node = entry.data[CONF_NODE]
            self._name = entry.data.get(CONF_MAC_NAME, self._name)
            api = CharmlingApi(async_get_clientsession(self.hass), self._host, self._port, entry.data[CONF_SECRET])
            try:
                who = await api.identify()               # who is there, before anything else
                if who.get("id") != entry.data[CONF_NODE]:
                    errors["base"] = "different_mac"
                else:
                    await api.state()                     # does it still take our secret?
                    return self.async_update_reload_and_abort(
                        entry, data_updates={CONF_HOST: self._host, CONF_PORT: self._port},
                    )
            except CharmlingAuthError:
                return await self.async_step_pair()          # it forgot us: a code, then
            except CharmlingError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                HOST_SCHEMA, {CONF_HOST: entry.data[CONF_HOST], CONF_PORT: entry.data[CONF_PORT]}
            ),
            errors=errors,
            description_placeholders={"name": entry.data.get(CONF_MAC_NAME, "")},
        )

    # ------------------------------------------------------------------ pair

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The six digits in Charmling's pane, exchanged for a secret and a webhook."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._pair(user_input["code"])
            if not isinstance(result, str):
                return result
            errors["base"] = result
        return self.async_show_form(
            step_id="pair",
            data_schema=CODE_SCHEMA,
            errors=errors,
            description_placeholders={"name": self._name, "host": self._host or ""},
        )

    async def _pair(self, raw_code: str) -> ConfigFlowResult | str:
        """Pair; an error key on failure, the finished flow on success."""
        code = "".join(ch for ch in str(raw_code) if ch.isdigit())
        if len(code) != 6:
            return "invalid_code"
        existing = None
        if self.source == SOURCE_REAUTH:
            existing = self._get_reauth_entry()
        elif self.source == SOURCE_RECONFIGURE:
            existing = self._get_reconfigure_entry()
        # a re-pair keeps the webhook it already has; the Mac just learns the URL again
        webhook_id = existing.data[CONF_WEBHOOK_ID] if existing else webhook.async_generate_id()
        webhook_url = _webhook_url(self.hass, webhook_id)
        if not webhook_url.startswith("http"):
            return "no_url"
        api = CharmlingApi(async_get_clientsession(self.hass), self._host or "", self._port)
        # when we know which Mac we mean (discovered, or re-pairing), say so: a
        # different Mac at that address refuses and changes nothing
        expect = existing.data[CONF_NODE] if existing else self._node
        try:
            reply = await api.pair(code, webhook_url, webhook_id, expect_id=expect)
        except CharmlingAuthError:
            return "invalid_code"
        except CharmlingConflictError:
            if self.source == SOURCE_RECONFIGURE:
                self._bounce = "different_mac"
                return await self.async_step_reconfigure()
            return "different_mac"
        except CharmlingError as err:
            _LOGGER.warning("Pairing with Charmling failed: %s", err)
            return "cannot_connect"
        node = reply.get("id") or self._node
        secret = reply.get("secret")
        if not node or not secret:
            return "cannot_connect"
        name = reply.get("name") or self._name
        updates = {
            CONF_HOST: self._host,
            CONF_PORT: self._port,
            CONF_SECRET: secret,
            CONF_MAC_NAME: name,
            CONF_VERSION: reply.get("version", ""),
        }
        if existing is not None:
            if node != existing.data[CONF_NODE]:
                if self.source == SOURCE_RECONFIGURE:
                    self._bounce = "different_mac"           # back to the address form, with the reason
                    return await self.async_step_reconfigure()
                return "different_mac"
            return self.async_update_reload_and_abort(existing, data_updates=updates)
        # typed by hand while the same Mac sits in the discovered list: the person
        # chose this path, so finish it; the discovery flow is dropped when the entry is created
        await self.async_set_unique_id(node, raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})
        return self.async_create_entry(
            title=f"Charmling on {name}",
            data={**updates, CONF_NODE: node, CONF_WEBHOOK_ID: webhook_id},
        )


def _webhook_url(hass: HomeAssistant, webhook_id: str) -> str:
    """Where the Mac should push: HA's own idea of its internal URL, else its address."""
    try:
        return webhook.async_generate_url(hass, webhook_id, allow_external=False)
    except Exception:  # noqa: BLE001 — no internal URL configured and none derivable
        api = hass.config.api
        if api is not None:
            scheme = "https" if api.use_ssl else "http"
            return f"{scheme}://{api.local_ip}:{api.port}/api/webhook/{webhook_id}"
        return ""
