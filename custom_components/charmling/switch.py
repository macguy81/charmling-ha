"""Two things the house may flip on the Mac: hush, and the bark mute."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CharmlingConfigEntry
from .entity import CharmlingEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class CharmlingSwitchDescription(SwitchEntityDescription):
    on_action: str
    off_action: str


DESCRIPTIONS: tuple[CharmlingSwitchDescription, ...] = (
    CharmlingSwitchDescription(key="hushed", translation_key="hushed", on_action="hush", off_action="unhush", icon="mdi:volume-off"),
    CharmlingSwitchDescription(key="muted", translation_key="muted", on_action="mute", off_action="unmute", icon="mdi:volume-mute"),
)


async def async_setup_entry(hass: HomeAssistant, entry: CharmlingConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(CharmlingSwitch(entry.runtime_data, d) for d in DESCRIPTIONS)


class CharmlingSwitch(CharmlingEntity, SwitchEntity):
    entity_description: CharmlingSwitchDescription

    @property
    def is_on(self) -> bool | None:
        v = self.value
        if v is None:
            return None
        return v.lower() in ("on", "true", "1", "yes") if isinstance(v, str) else bool(v)

    async def _do(self, action: str, want: bool) -> None:
        await self.ask(action, self.data.api.do(action))
        # the Mac confirms over the webhook within a second; show it now anyway
        self.data.states[self.entity_description.key] = want
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._do(self.entity_description.on_action, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._do(self.entity_description.off_action, False)
