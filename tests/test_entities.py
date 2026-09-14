"""Every platform's reading of what the Mac sends."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.charmling.const import DOMAIN

from .conftest import P


async def test_binary_sensors(hass: HomeAssistant, paired, push) -> None:
    await push({"type": "state", "states": {"on_air": True, "screen_locked": True, "focus": "yes", "wander": "off"}})
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "on"
    assert hass.states.get(f"binary_sensor.{P}_on_air").attributes["device_class"] == "running"
    # lock class: "on" means unlocked, so a locked screen reads off
    assert hass.states.get(f"binary_sensor.{P}_screen").state == "off"
    assert hass.states.get(f"binary_sensor.{P}_screen").attributes["device_class"] == "lock"
    assert hass.states.get(f"binary_sensor.{P}_focus_session").state == "on"
    assert hass.states.get(f"binary_sensor.{P}_wander_mode").state == "off"
    assert hass.states.get(f"binary_sensor.{P}_at_the_desk").attributes["device_class"] == "occupancy"


async def test_sensors(hass: HomeAssistant, paired, push) -> None:
    await push({"type": "state", "states": {"in_call": True, "display_asleep": False, "do_not_disturb": True, "focus_mode": "work", "leash": "extra long"}})
    assert hass.states.get(f"binary_sensor.{P}_in_a_call").state == "on"
    assert hass.states.get(f"binary_sensor.{P}_display_asleep").state == "off"
    assert hass.states.get(f"binary_sensor.{P}_do_not_disturb").state == "on"
    assert hass.states.get(f"sensor.{P}_focus_mode").state == "work"
    assert hass.states.get(f"sensor.{P}_leash").state == "extra_long"
    await push({"type": "state", "states": {
        "work_kind": "HACKING", "meeting_density": "Heavy", "beads": "many", "next_meeting_minutes": -1,
        "focus_remaining": 12.0, "away_minutes": 3.5, "dog": "lying down", "charm": "", "score": None,
    }})
    assert hass.states.get(f"sensor.{P}_work_kind").state == "unknown"           # not one of the options
    assert hass.states.get(f"sensor.{P}_meeting_density").state == "heavy"       # case folded
    assert hass.states.get(f"sensor.{P}_beads_waiting").state == "unknown"       # not a number
    assert hass.states.get(f"sensor.{P}_next_meeting_in").state == "unknown"     # -1 is "no meeting", not a number
    assert hass.states.get(f"sensor.{P}_focus_remaining").state == "12"
    assert hass.states.get(f"sensor.{P}_away").state == "3.5"
    assert hass.states.get(f"sensor.{P}_dog").state == "lying_down"     # an enum: the Mac's "lying down" folded
    assert hass.states.get(f"sensor.{P}_charm").state == "unknown"               # empty string
    assert hass.states.get(f"sensor.{P}_live_score").state == "unknown"
    assert hass.states.get(f"sensor.{P}_work_kind").attributes["options"][0] == "coding"
    await push({"type": "state", "states": {"work_kind": "writing", "next_meeting_minutes": 0}})
    assert hass.states.get(f"sensor.{P}_work_kind").state == "writing"
    assert hass.states.get(f"sensor.{P}_next_meeting_in").state == "0"


async def test_last_seen_outlives_the_mac(hass: HomeAssistant, paired, push) -> None:
    """Enabled by the person, last_seen keeps its timestamp after the Mac goes."""
    from homeassistant.helpers import entity_registry as er

    er.async_get(hass).async_update_entity(f"sensor.{P}_last_seen", disabled_by=None)
    await hass.config_entries.async_reload(paired.entry_id)
    await hass.async_block_till_done()
    st = hass.states.get(f"sensor.{P}_last_seen")
    assert st.state not in ("unknown", "unavailable")
    assert st.attributes["device_class"] == "timestamp"
    await push({"type": "bye"})
    assert hass.states.get(f"sensor.{P}_last_seen").state == st.state
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "unavailable"


async def test_switches(hass: HomeAssistant, paired, mac, push) -> None:
    assert hass.states.get(f"switch.{P}_hushed").state == "off"
    await hass.services.async_call("switch", "turn_on", {"entity_id": f"switch.{P}_hushed"}, blocking=True)
    assert [c for c in mac.mock_calls if str(c[1]).endswith("/do")][-1][2] == {"action": "hush"}
    assert hass.states.get(f"switch.{P}_hushed").state == "on"          # optimistic, until the Mac confirms
    await push({"type": "state", "states": {"hushed": True}})
    assert hass.states.get(f"switch.{P}_hushed").state == "on"
    await hass.services.async_call("switch", "turn_off", {"entity_id": f"switch.{P}_bark_muted"}, blocking=True)
    assert [c for c in mac.mock_calls if str(c[1]).endswith("/do")][-1][2] == {"action": "unmute"}


async def test_buttons(hass: HomeAssistant, paired, mac) -> None:
    await hass.services.async_call("button", "press", {"entity_id": f"button.{P}_focus_25_minutes"}, blocking=True)
    assert [c for c in mac.mock_calls if str(c[1]).endswith("/do")][-1][2] == {"action": "focus", "minutes": 25}
    await hass.services.async_call("button", "press", {"entity_id": f"button.{P}_call_the_dog"}, blocking=True)
    assert [c for c in mac.mock_calls if str(c[1]).endswith("/do")][-1][2] == {"action": "call"}


async def test_everything_belongs_to_the_one_device(hass: HomeAssistant, paired) -> None:
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, paired.data["node"])})
    mine = [e for e in er.async_get(hass).entities.values() if e.platform == DOMAIN]
    assert all(e.device_id == device.id for e in mine)
    assert {e.domain for e in mine} == {"binary_sensor", "sensor", "event", "button", "switch"}
