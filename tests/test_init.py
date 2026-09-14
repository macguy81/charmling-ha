"""Setup, the webhook, availability, unload and removal."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_capture_events, async_fire_time_changed

from custom_components.charmling.const import DOMAIN, EVENT_NAME

from .conftest import BASE, NODE, SECRET, WEBHOOK_ID, P


async def test_setup_seeds_from_state_and_makes_the_device(hass: HomeAssistant, paired) -> None:
    assert paired.state is ConfigEntryState.LOADED
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "off"
    assert hass.states.get(f"binary_sensor.{P}_at_the_desk").state == "on"
    assert hass.states.get(f"sensor.{P}_dog").state == "sitting"
    assert hass.states.get(f"sensor.{P}_work_kind").state == "coding"
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, NODE)})
    assert device is not None
    assert device.name == "Abi's MacBook Pro"
    assert device.manufacturer == "Charmling"
    assert device.sw_version == "1.9"


async def test_all_entities_exist_and_the_noisy_ones_are_off(hass: HomeAssistant, paired) -> None:
    registry = er.async_get(hass)
    mine = [e for e in registry.entities.values() if e.platform == DOMAIN]
    assert len(mine) == 38
    assert registry.async_get(f"sensor.{P}_idle").disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert registry.async_get(f"sensor.{P}_last_seen").disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert registry.async_get(f"sensor.{P}_dog_s_name").entity_category == "diagnostic"
    # unique ids never depend on the Mac's name
    assert registry.async_get(f"binary_sensor.{P}_on_air").unique_id == f"{NODE}_on_air"


async def test_setup_when_the_mac_is_asleep(hass: HomeAssistant, entry, aioclient_mock) -> None:
    """No answer from /state: the entry still loads, everything is unavailable, nothing crashes."""
    aioclient_mock.get(f"{BASE}/state", exc=TimeoutError())
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "unavailable"


async def test_webhook_needs_the_secret(hass: HomeAssistant, paired, push) -> None:
    assert await push({"type": "state", "states": {"on_air": True}}, secret="wrong") == 401
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "off"
    assert await push({"type": "state", "states": {"on_air": True}}, secret="") == 401
    assert await push({"type": "state", "states": {"on_air": True}}) == 200
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "on"


async def test_webhook_rejects_junk(hass: HomeAssistant, paired, push) -> None:
    assert await push(None, raw=b"not json") == 400
    assert await push([1, 2, 3]) == 400
    assert await push({"type": "state", "states": "on_air=on"}) == 200
    assert await push({"type": "nonsense"}) == 200
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "off"


async def test_webhook_cleans_values(hass: HomeAssistant, paired, push) -> None:
    await push({"type": "state", "states": {"on_air": {"nested": 1}, "dog": "x" * 500, "k" * 100: 1, "camera": True}})
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "off"       # nested value dropped
    assert hass.states.get(f"binary_sensor.{P}_camera").state == "on"        # sibling kept
    assert len(hass.states.get(f"sensor.{P}_dog").state) == 200              # truncated
    await push({"type": "state", "states": {f"k{i}": i for i in range(300)} | {"on_air": True}})
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "off"       # a 300-key dict is not a Mac


async def test_events_reach_the_bus_and_the_event_entity(hass: HomeAssistant, paired, push) -> None:
    seen = async_capture_events(hass, EVENT_NAME)
    await push({"type": "event", "event": "trick", "trick": "roll"})
    assert len(seen) == 1
    assert seen[0].data["type"] == "trick"
    assert seen[0].data["trick"] == "roll"
    assert seen[0].data["node"] == NODE
    assert seen[0].data["device_id"]
    ev = hass.states.get(f"event.{P}_moment")
    assert ev.attributes["event_type"] == "trick"
    assert ev.attributes["trick"] == "roll"
    # an unknown type still goes to the bus for automations, but the entity only lists known ones
    await push({"type": "event", "event": "dance"})
    assert len(seen) == 2
    assert hass.states.get(f"event.{P}_moment").attributes["event_type"] == "trick"
    # no name: nothing
    assert await push({"type": "event"}) == 200
    assert len(seen) == 2


async def test_bye_hello_and_silence(hass: HomeAssistant, paired, push, freezer) -> None:
    await push({"type": "bye"})
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "unavailable"
    assert hass.states.get(f"button.{P}_call_the_dog").state == "unavailable"
    await push({"type": "hello", "version": "2.0", "states": {"on_air": True}})
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "on"
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, NODE)})
    assert device.sw_version == "2.0"
    assert paired.data["version"] == "2.0"
    # ninety seconds of silence: gone
    freezer.tick(timedelta(seconds=125))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "unavailable"
    # one ping: back, with the last values intact
    await push({"type": "ping"})
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "on"


async def test_seed_does_not_clobber_a_push_that_landed_first(hass: HomeAssistant, paired) -> None:
    """A push that arrives while /state is in flight is newer than the snapshot: the seed must not overwrite it."""
    data = paired.runtime_data
    data.states["on_air"] = True          # what a webhook wrote a moment ago
    await data.async_start()              # the (older) /state snapshot says off
    assert data.states["on_air"] is True
    assert data.states["dog"] == "sitting"   # keys the push did not carry are still seeded


async def test_unload_and_reload(hass: HomeAssistant, paired, push) -> None:
    assert await hass.config_entries.async_unload(paired.entry_id)
    await hass.async_block_till_done()
    assert paired.state is ConfigEntryState.NOT_LOADED
    # the webhook is gone with it: HA answers an unknown webhook with an empty 200, never our handler
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "unavailable"
    assert await hass.config_entries.async_setup(paired.entry_id)
    await hass.async_block_till_done()
    assert paired.state is ConfigEntryState.LOADED
    assert await push({"type": "state", "states": {"on_air": True}}) == 200
    assert hass.states.get(f"binary_sensor.{P}_on_air").state == "on"


async def test_remove_tells_the_mac(hass: HomeAssistant, paired, mac) -> None:
    await hass.config_entries.async_remove(paired.entry_id)
    await hass.async_block_till_done()
    calls = [c for c in mac.mock_calls if str(c[1]).endswith("/unpair")]
    assert len(calls) == 1
    assert calls[0][3]["Authorization"] == f"Bearer {SECRET}"


async def test_remove_survives_a_sleeping_mac(hass: HomeAssistant, paired, aioclient_mock) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{BASE}/unpair", exc=TimeoutError())
    await hass.config_entries.async_remove(paired.entry_id)
    await hass.async_block_till_done()
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_diagnostics_redact_the_secret(hass: HomeAssistant, paired, hass_client) -> None:
    from custom_components.charmling.diagnostics import async_get_config_entry_diagnostics

    diag = await async_get_config_entry_diagnostics(hass, paired)
    assert diag["entry"]["secret"] == "**REDACTED**"
    assert diag["entry"]["webhook_id"] == "**REDACTED**"
    assert diag["states"]["dog"] == "sitting"
    assert WEBHOOK_ID not in str(diag)
