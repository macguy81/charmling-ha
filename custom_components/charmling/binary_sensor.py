"""On/off things the Mac knows about itself."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CharmlingConfigEntry
from .entity import CharmlingEntity

PARALLEL_UPDATES = 0

DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(key="on_air", translation_key="on_air", device_class=BinarySensorDeviceClass.RUNNING, icon="mdi:microphone"),
    BinarySensorEntityDescription(key="camera", translation_key="camera", device_class=BinarySensorDeviceClass.RUNNING, icon="mdi:video"),
    BinarySensorEntityDescription(key="in_call_app", translation_key="in_call_app", icon="mdi:phone"),
    BinarySensorEntityDescription(key="presenting", translation_key="presenting", icon="mdi:presentation-play"),
    BinarySensorEntityDescription(key="at_desk", translation_key="at_desk", device_class=BinarySensorDeviceClass.OCCUPANCY),
    BinarySensorEntityDescription(key="screen_locked", translation_key="screen_locked", device_class=BinarySensorDeviceClass.LOCK),
    BinarySensorEntityDescription(key="focus", translation_key="focus", icon="mdi:target"),
    BinarySensorEntityDescription(key="screen_full", translation_key="screen_full", icon="mdi:fullscreen"),
    BinarySensorEntityDescription(key="wander", translation_key="wander", icon="mdi:scissors-cutting"),
    BinarySensorEntityDescription(key="pet_out", translation_key="pet_out", icon="mdi:dog-side"),
)


async def async_setup_entry(hass: HomeAssistant, entry: CharmlingConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(CharmlingBinarySensor(entry.runtime_data, d) for d in DESCRIPTIONS)


class CharmlingBinarySensor(CharmlingEntity, BinarySensorEntity):
    @property
    def is_on(self) -> bool | None:
        v = self.value
        if v is None:
            return None
        on = v.lower() in ("on", "true", "1", "yes") if isinstance(v, str) else bool(v)
        # device_class lock reads "on" as unlocked, so a locked screen is "off"
        if self.entity_description.key == "screen_locked":
            return not on
        return on
