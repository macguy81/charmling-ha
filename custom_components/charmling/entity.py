"""The base every Charmling entity shares: one device per Mac, pushed updates."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity, EntityDescription

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import CharmlingData
from .helpers import async_ask


class CharmlingEntity(Entity):
    """Belongs to one Mac; redraws when the Mac pushes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, data: CharmlingData, description: EntityDescription) -> None:
        self.data = data
        self.entity_description = description
        self._attr_unique_id = f"{data.node}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.node)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=data.name,
            sw_version=data.version or None,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, self.data.signal, self._pushed))

    @callback
    def _pushed(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self.data.available

    @property
    def value(self):
        """The Mac's latest value for this key, or None when it has not sent one."""
        return self.data.states.get(self.entity_description.key)

    async def ask(self, what: str, coro) -> None:
        """A request to the Mac, with a re-pair started if it refuses the secret."""
        await async_ask(self.data, what, coro)
