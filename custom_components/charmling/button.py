"""Things to press from a dashboard: call the dog, ask for the trick, start a focus."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CharmlingConfigEntry
from .entity import CharmlingEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class CharmlingButtonDescription(ButtonEntityDescription):
    action: str
    extra: dict | None = None


DESCRIPTIONS: tuple[CharmlingButtonDescription, ...] = (
    CharmlingButtonDescription(key="call", translation_key="call", action="call", icon="mdi:bullhorn-outline"),
    CharmlingButtonDescription(key="trick", translation_key="trick", action="trick", icon="mdi:star-outline"),
    CharmlingButtonDescription(key="speak", translation_key="speak", action="speak", icon="mdi:dog"),
    CharmlingButtonDescription(key="pat", translation_key="pat", action="pat", icon="mdi:hand-heart-outline"),
    CharmlingButtonDescription(key="focus_25", translation_key="focus_25", action="focus", extra={"minutes": 25}, icon="mdi:timer-play-outline"),
    CharmlingButtonDescription(key="stop_focus", translation_key="stop_focus", action="stop_focus", icon="mdi:timer-stop-outline"),
    CharmlingButtonDescription(key="nap", translation_key="nap", action="nap", icon="mdi:sleep"),
    CharmlingButtonDescription(key="wake", translation_key="wake", action="wake", icon="mdi:alarm"),
)


async def async_setup_entry(hass: HomeAssistant, entry: CharmlingConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(CharmlingButton(entry.runtime_data, d) for d in DESCRIPTIONS)


class CharmlingButton(CharmlingEntity, ButtonEntity):
    entity_description: CharmlingButtonDescription

    async def async_press(self) -> None:
        d = self.entity_description
        await self.ask(d.action, self.data.api.do(d.action, **(d.extra or {})))
