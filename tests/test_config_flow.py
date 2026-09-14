"""Discovery, manual, reauth and reconfigure, and every way pairing can go wrong."""

from __future__ import annotations

from dataclasses import replace
from ipaddress import ip_address

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from custom_components.charmling.const import CONF_NODE, CONF_SECRET, CONF_WEBHOOK_ID, DOMAIN

from .conftest import BASE, HOST, NAME, NODE, PORT, SECRET

DISCOVERY = ZeroconfServiceInfo(
    ip_address=ip_address(HOST),
    ip_addresses=[ip_address("fe80::1"), ip_address(HOST)],
    hostname="abis-macbook-pro.local.",
    name=f"Charmling on {NAME}._charmling._tcp.local.",
    port=PORT,
    type="_charmling._tcp.local.",
    properties={"id": NODE, "name": NAME, "ver": "1.9"},
)


def pair_ok(aioclient_mock, node: str = NODE, name: str = NAME):
    aioclient_mock.post(f"{BASE}/pair", json={"id": node, "name": name, "secret": "new-secret", "version": "1.9"})


async def test_user_flow(hass: HomeAssistant, aioclient_mock) -> None:
    pair_ok(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: f" {HOST} ", CONF_PORT: PORT})
    assert result["step_id"] == "pair"
    assert result["description_placeholders"]["host"] == HOST
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123 456"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Charmling on {NAME}"
    assert result["data"][CONF_NODE] == NODE
    assert result["data"][CONF_SECRET] == "new-secret"
    assert result["data"][CONF_HOST] == HOST
    assert len(result["data"][CONF_WEBHOOK_ID]) > 16
    # what the Mac was told
    sent = aioclient_mock.mock_calls[-1][2]
    assert sent["code"] == "123456"
    assert sent["webhook_url"].startswith("http")
    assert sent["webhook_url"].endswith(f"/api/webhook/{result['data'][CONF_WEBHOOK_ID]}")
    assert "expect_id" not in sent          # a hand-typed address: we do not know who is there


@pytest.mark.parametrize(
    ("typed", "port", "host", "want_port"),
    [
        ("192.0.2.10", 41417, "192.0.2.10", 41417),
        ("http://192.0.2.10:41417/", 41417, "192.0.2.10", 41417),
        ("192.0.2.10:41500", 41417, "192.0.2.10", 41500),
        ("abis-macbook-pro.local", 41417, "abis-macbook-pro.local", 41417),
        ("[fe80::1]:41417", 41417, "fe80::1", 41417),
        (" HTTPS://Abis-MacBook-Pro.local ", 41417, "abis-macbook-pro.local", 41417),
    ],
)
async def test_user_flow_takes_what_people_paste(hass: HomeAssistant, aioclient_mock, typed, port, host, want_port) -> None:
    aioclient_mock.post(f"http://{'[' + host + ']' if ':' in host else host}:{want_port}/pair", json={"id": NODE, "name": NAME, "secret": "s", "version": "1"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: typed, CONF_PORT: port})
    assert result["step_id"] == "pair", result
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == host
    assert result["data"][CONF_PORT] == want_port
    assert aioclient_mock.mock_calls[-1][2]["api_port"] == 8123


async def test_user_flow_rejects_nonsense(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: "http://", CONF_PORT: 41417})
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_host"}


async def test_zeroconf_flow(hass: HomeAssistant, aioclient_mock) -> None:
    pair_ok(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=DISCOVERY)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pair"
    assert result["description_placeholders"] == {"name": NAME, "host": HOST}   # the IPv4 one, not fe80::1
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST
    assert aioclient_mock.mock_calls[-1][2]["expect_id"] == NODE   # discovered: we know who we mean


async def test_zeroconf_without_id_is_not_ours(hass: HomeAssistant) -> None:
    info = replace(DISCOVERY, properties={"name": "x"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_charmling"


async def test_zeroconf_updates_the_address_of_a_paired_mac(hass: HomeAssistant, paired) -> None:
    moved = replace(DISCOVERY, ip_address=ip_address("192.0.2.99"), ip_addresses=[ip_address("192.0.2.99")], port=41500)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=moved)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert paired.data[CONF_HOST] == "192.0.2.99"
    assert paired.data[CONF_PORT] == 41500


@pytest.mark.parametrize(
    ("status", "error"),
    [(403, "invalid_code"), (401, "invalid_code"), (500, "cannot_connect")],
)
async def test_pair_refused(hass: HomeAssistant, aioclient_mock, status: int, error: str) -> None:
    aioclient_mock.post(f"{BASE}/pair", status=status, text="no")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: HOST, CONF_PORT: PORT})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "000000"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    # and the form is still usable afterwards
    aioclient_mock.clear_requests()
    pair_ok(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_pair_unreachable(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{BASE}/pair", exc=TimeoutError())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: HOST, CONF_PORT: PORT})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_pair_with_a_short_code_never_calls_the_mac(hass: HomeAssistant, aioclient_mock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: HOST, CONF_PORT: PORT})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "12"})
    assert result["errors"] == {"base": "invalid_code"}
    assert not aioclient_mock.mock_calls


async def test_pair_with_a_bad_reply(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.post(f"{BASE}/pair", json={"id": NODE})   # no secret
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: HOST, CONF_PORT: PORT})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_already_paired_mac_typed_by_hand(hass: HomeAssistant, paired, aioclient_mock) -> None:
    pair_ok(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: HOST, CONF_PORT: PORT})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_wins_over_an_open_discovery(hass: HomeAssistant, aioclient_mock) -> None:
    """The Mac sits in the discovered list; the person types its address instead. Both must not end up as entries."""
    pair_ok(aioclient_mock)
    disc = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_ZEROCONF}, data=DISCOVERY)
    assert disc["step_id"] == "pair"
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: HOST, CONF_PORT: PORT})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reauth(hass: HomeAssistant, paired, aioclient_mock) -> None:
    aioclient_mock.post(f"{BASE}/pair", json={"id": NODE, "name": NAME, "secret": "second-secret", "version": "2.0"})
    paired.async_start_reauth(hass)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(flows[0]["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert paired.data[CONF_SECRET] == "second-secret"
    sent = [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/pair")][-1][2]
    assert sent["webhook_id"] == paired.data[CONF_WEBHOOK_ID]     # the same webhook, so nothing else changes
    assert sent["expect_id"] == NODE


async def test_reauth_refuses_another_mac(hass: HomeAssistant, paired, aioclient_mock) -> None:
    aioclient_mock.post(f"{BASE}/pair", status=409, json={"error": "not that Mac", "id": "other"})
    paired.async_start_reauth(hass)
    await hass.async_block_till_done()
    flow = hass.config_entries.flow.async_progress_by_handler(DOMAIN)[0]
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "different_mac"}
    assert paired.data[CONF_SECRET] == SECRET


async def test_reconfigure_same_mac_keeps_the_pairing(hass: HomeAssistant, paired, aioclient_mock) -> None:
    new = "http://192.0.2.77:41417"
    aioclient_mock.get(f"{new}/id", json={"id": NODE, "name": NAME, "version": "1.9", "paired": True})
    aioclient_mock.get(f"{new}/state", json={"id": NODE, "states": {}})
    result = await paired.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "192.0.2.77", CONF_PORT: 41417})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert paired.data[CONF_HOST] == "192.0.2.77"
    assert paired.data[CONF_SECRET] == SECRET


async def test_reconfigure_a_different_mac_is_refused_without_pairing(hass: HomeAssistant, paired, aioclient_mock) -> None:
    new = "http://192.0.2.78:41417"
    aioclient_mock.get(f"{new}/id", json={"id": "someone-else", "name": "Studio", "version": "1.9", "paired": False})
    result = await paired.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "192.0.2.78", CONF_PORT: 41417})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "different_mac"}
    assert not [c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/pair")]
    assert paired.data[CONF_HOST] == HOST


async def test_reconfigure_asks_for_a_code_when_the_mac_forgot_us(hass: HomeAssistant, paired, aioclient_mock) -> None:
    new = "http://192.0.2.79:41417"
    aioclient_mock.get(f"{new}/id", json={"id": NODE, "name": NAME, "version": "1.9", "paired": False})
    aioclient_mock.get(f"{new}/state", status=401)
    aioclient_mock.post(f"{new}/pair", json={"id": NODE, "name": NAME, "secret": "third", "version": "1.9"})
    result = await paired.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "192.0.2.79", CONF_PORT: 41417})
    assert result["step_id"] == "pair"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert paired.data[CONF_HOST] == "192.0.2.79"
    assert paired.data[CONF_SECRET] == "third"


async def test_reconfigure_unreachable(hass: HomeAssistant, paired, aioclient_mock) -> None:
    aioclient_mock.get("http://192.0.2.80:41417/id", exc=TimeoutError())
    result = await paired.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: "192.0.2.80", CONF_PORT: 41417})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_no_internal_url(hass: HomeAssistant, aioclient_mock, monkeypatch) -> None:
    """HA cannot say where it lives: the flow says so instead of handing the Mac a broken URL."""
    from custom_components.charmling import config_flow

    monkeypatch.setattr(config_flow, "_webhook_url", lambda hass, wid: "")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={CONF_HOST: HOST, CONF_PORT: PORT})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"code": "123456"})
    assert result["errors"] == {"base": "no_url"}
    assert not aioclient_mock.mock_calls


async def test_flow_is_registered_as_a_config_flow(hass: HomeAssistant) -> None:
    assert DOMAIN in config_entries.HANDLERS
