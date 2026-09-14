"""The moments in the automation editor's device picker."""

from __future__ import annotations

from homeassistant.components import automation
from homeassistant.components.device_automation import DeviceAutomationType
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_get_device_automations, async_mock_service

from custom_components.charmling.const import DOMAIN, EVENT_TYPES


async def test_every_moment_is_offered(hass: HomeAssistant, paired) -> None:
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, paired.data["node"])})
    triggers = await async_get_device_automations(hass, DeviceAutomationType.TRIGGER, device.id)
    ours = [t for t in triggers if t["domain"] == DOMAIN]
    assert {t["type"] for t in ours} == set(EVENT_TYPES)
    assert all(t["device_id"] == device.id and t["platform"] == "device" for t in ours)


async def test_a_device_trigger_fires_for_its_device_only(hass: HomeAssistant, paired, push) -> None:
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, paired.data["node"])})
    calls = async_mock_service(hass, "test", "automation")
    assert await async_setup_component(hass, automation.DOMAIN, {
        automation.DOMAIN: [{
            "trigger": {"platform": "device", "domain": DOMAIN, "device_id": device.id, "type": "woof"},
            "action": {"service": "test.automation", "data": {"who": "{{ trigger.event.data.node }}"}},
        }]
    })
    await push({"type": "event", "event": "woof"})
    assert len(calls) == 1
    assert calls[0].data["who"] == paired.data["node"]
    await push({"type": "event", "event": "bark"})          # a different moment
    assert len(calls) == 1
    hass.bus.async_fire("charmling_event", {"type": "woof", "device_id": "another-mac"})   # a different Mac
    await hass.async_block_till_done()
    assert len(calls) == 1
