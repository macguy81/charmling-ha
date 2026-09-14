"""The moments: a call started, the dog woofed, focus began. One event entity per Mac."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity, EventEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CharmlingConfigEntry
from .const import EVENT_TYPES
from .coordinator import CharmlingData
from .entity import CharmlingEntity

PARALLEL_UPDATES = 0

DESCRIPTION = EventEntityDescription(key="moment", translation_key="moment", event_types=EVENT_TYPES)


async def async_setup_entry(hass: HomeAssistant, entry: CharmlingConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([CharmlingEvent(entry.runtime_data)])


class CharmlingEvent(CharmlingEntity, EventEntity):
    def __init__(self, data: CharmlingData) -> None:
        super().__init__(data, DESCRIPTION)
        self._seen: tuple[str, dict[str, Any]] | None = None

    @callback
    def _pushed(self) -> None:
        ev = self.data.last_event
        if ev is not None and ev is not self._seen:
            self._seen = ev
            event_type, payload = ev
            if event_type in EVENT_TYPES:
                self._trigger_event(event_type, payload)
        self.async_write_ha_state()
