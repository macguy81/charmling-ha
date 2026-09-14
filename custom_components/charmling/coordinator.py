"""The Mac's latest states, pushed in over the webhook.

Not a polling coordinator: Charmling pushes every change the second it
happens and a heartbeat every thirty seconds. This holds the latest values,
knows when the Mac has gone quiet, and tells the entities.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .api import CharmlingApi, CharmlingAuthError, CharmlingError
from .const import DOMAIN, SIGNAL_UPDATE, STALE_AFTER

_LOGGER = logging.getLogger(__name__)


class CharmlingData:
    """One paired Mac."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: CharmlingApi, node: str, name: str) -> None:
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self.api = api
        self.node = node
        self.name = name
        self.version = ""
        self.states: dict[str, Any] = {}
        self.last_seen: datetime | None = None
        self.available = False
        self.last_event: tuple[str, dict[str, Any]] | None = None
        self._unsub_timer = None

    @property
    def signal(self) -> str:
        return SIGNAL_UPDATE.format(self.entry_id)

    @property
    def device_id(self) -> str | None:
        device = dr.async_get(self.hass).async_get_device(identifiers={(DOMAIN, self.node)})
        return device.id if device else None

    async def async_start(self) -> None:
        """Seed from the Mac if it answers, then watch for silence."""
        try:
            data = await self.api.state()
        except CharmlingAuthError:
            # it was unpaired on the Mac while we were away: ask for a new code
            _LOGGER.warning("Charmling on %s no longer accepts our pairing", self.name)
            self.entry.async_start_reauth(self.hass)
        except CharmlingError as err:
            _LOGGER.debug("Charmling on %s did not answer yet: %s", self.name, err)
        else:
            states = data.get("states")
            if isinstance(states, dict):
                self.apply(states)
            self.version = str(data.get("version") or self.version)
            self.mark_seen()
        self._unsub_timer = async_track_time_interval(self.hass, self._check_stale, timedelta(seconds=30))

    @callback
    def async_stop(self) -> None:
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def apply(self, states: dict[str, Any]) -> None:
        self.states.update(states)

    @callback
    def mark_seen(self) -> None:
        self.last_seen = dt_util.utcnow()
        if not self.available:
            self.available = True
            _LOGGER.info("Charmling on %s is here", self.name)
        async_dispatcher_send(self.hass, self.signal)

    @callback
    def mark_gone(self) -> None:
        if self.available:
            self.available = False
            _LOGGER.info("Charmling on %s has gone (the Mac slept, or the app quit)", self.name)
            async_dispatcher_send(self.hass, self.signal)

    @callback
    def _check_stale(self, _now: datetime) -> None:
        if self.last_seen and (dt_util.utcnow() - self.last_seen).total_seconds() > STALE_AFTER:
            self.mark_gone()

    @callback
    def event(self, event_type: str, data: dict[str, Any]) -> None:
        self.last_event = (event_type, data)
        async_dispatcher_send(self.hass, self.signal)
