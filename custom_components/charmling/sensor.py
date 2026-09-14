"""Numbers and small words the Mac knows about itself. Never a title, never a line of text."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CharmlingConfigEntry
from .entity import CharmlingEntity

PARALLEL_UPDATES = 0

WORK_KINDS = ["coding", "writing", "design", "reading", "browsing", "chat", "mail",
              "meeting", "media", "spreadsheets", "other", "idle"]
DENSITIES = ["light", "normal", "heavy", "unknown"]
DOG_STATES = ["idle", "walking", "sitting", "napping", "lying_down", "trick", "looking", "carried", "dropping",
              "standing_down", "away"]
LEASHES = ["short", "medium", "long", "extra_long"]
FOCUS_MODES = ["off", "do_not_disturb", "work", "personal", "sleep", "driving", "fitness", "gaming",
               "mindfulness", "reading", "custom"]

DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    # changes every heartbeat: off unless wanted, so the recorder is not fed a row every 30 s
    SensorEntityDescription(key="idle_seconds", translation_key="idle_seconds", native_unit_of_measurement=UnitOfTime.SECONDS,
                            device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.MEASUREMENT,
                            entity_registry_enabled_default=False),
    SensorEntityDescription(key="away_minutes", translation_key="away_minutes", native_unit_of_measurement=UnitOfTime.MINUTES,
                            device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="focus_remaining", translation_key="focus_remaining", native_unit_of_measurement=UnitOfTime.MINUTES,
                            device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="work_kind", translation_key="work_kind", device_class=SensorDeviceClass.ENUM, options=WORK_KINDS),
    SensorEntityDescription(key="front_app", translation_key="front_app"),
    SensorEntityDescription(key="next_meeting_minutes", translation_key="next_meeting_minutes", native_unit_of_measurement=UnitOfTime.MINUTES,
                            state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="meeting_density", translation_key="meeting_density", device_class=SensorDeviceClass.ENUM, options=DENSITIES),
    SensorEntityDescription(key="focus_mode", translation_key="focus_mode", device_class=SensorDeviceClass.ENUM, options=FOCUS_MODES),
    SensorEntityDescription(key="charm", translation_key="charm"),
    SensorEntityDescription(key="beads", translation_key="beads", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="basket", translation_key="basket", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="banners_10min", translation_key="banners_10min", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="cord_friends", translation_key="cord_friends", state_class=SensorStateClass.MEASUREMENT),
    SensorEntityDescription(key="dog", translation_key="dog", device_class=SensorDeviceClass.ENUM, options=DOG_STATES),
    SensorEntityDescription(key="dog_name", translation_key="dog_name", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="leash", translation_key="leash", device_class=SensorDeviceClass.ENUM, options=LEASHES, entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(key="score", translation_key="score"),
    SensorEntityDescription(key="last_seen", translation_key="last_seen", device_class=SensorDeviceClass.TIMESTAMP,
                            entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False),
)


async def async_setup_entry(hass: HomeAssistant, entry: CharmlingConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities(CharmlingSensor(entry.runtime_data, d) for d in DESCRIPTIONS)


class CharmlingSensor(CharmlingEntity, SensorEntity):
    @property
    def native_value(self):
        key = self.entity_description.key
        if key == "last_seen":
            return self.data.last_seen
        v = self.value
        if v is None or v == "":
            return None
        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            s = str(v).lower().replace(" ", "_")
            return s if s in (self.entity_description.options or []) else None
        if self.entity_description.native_unit_of_measurement or self.entity_description.state_class:
            try:
                n = int(v) if float(v).is_integer() else float(v)
            except (TypeError, ValueError):
                return None
            # the Mac says -1 for "no meeting in the next 8 h, or no calendar access": that is unknown, not a number
            if key == "next_meeting_minutes" and n < 0:
                return None
            return n
        return str(v)

    @property
    def available(self) -> bool:
        # last_seen stays readable after the Mac goes quiet: that is the point of it
        if self.entity_description.key == "last_seen":
            return self.data.last_seen is not None
        return super().available
