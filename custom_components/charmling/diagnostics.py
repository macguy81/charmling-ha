"""Diagnostics: what the Mac last sent, minus the secret."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import CharmlingConfigEntry
from .const import CONF_SECRET, CONF_WEBHOOK_ID


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: CharmlingConfigEntry) -> dict[str, Any]:
    data = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), {CONF_SECRET, CONF_WEBHOOK_ID}),
        "available": data.available,
        "last_seen": data.last_seen.isoformat() if data.last_seen else None,
        "version": data.version,
        "states": data.states,
        "last_event": data.last_event,
    }
