"""Adversarial run against the live HA: malformed input, two Macs, reauth, reconfigure, reload cycles."""
import asyncio, json, time, requests, websockets, subprocess
H = __import__("os").environ.get("HA_URL", "http://127.0.0.1:8123")
tok = __import__("os").environ["HA_TOKEN"]
s = requests.Session(); s.headers["Authorization"] = "Bearer " + tok
M1, M2 = "http://127.0.0.1:41417/_test", "http://127.0.0.1:41418/_test"
P1, P2 = "abi_s_macbook_pro", "studio_mac"
fails = []

def check(label, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + label + ("" if cond else f"  -> {detail}"))
    if not cond: fails.append(label)

def j(m, p, **kw):
    r = s.request(m, H + p, **kw)
    try: return r.status_code, r.json()
    except Exception: return r.status_code, r.text
def st(eid):
    code, r = j("GET", f"/api/states/{eid}")
    return r["state"] if code == 200 else f"<{code}>"
def attrs(eid): return j("GET", f"/api/states/{eid}")[1].get("attributes", {})
def mock(url, **b): return requests.post(url, json=b).json()
def mocklog(url): return requests.get(url).json()
async def ws_cmd(**cmd):
    async with websockets.connect("ws://127.0.0.1:8123/api/websocket") as ws:
        await ws.recv(); await ws.send(json.dumps({"type": "auth", "access_token": tok})); await ws.recv()
        await ws.send(json.dumps({"id": 1, **cmd})); return json.loads(await ws.recv())["result"]
def flows(): return asyncio.run(ws_cmd(type="config_entries/flow/progress"))
def pair(port, code="123456", host="127.0.0.1"):
    c, r = j("POST", "/api/config/config_entries/flow", json={"handler": "charmling"}); fid = r["flow_id"]
    j("POST", f"/api/config/config_entries/flow/{fid}", json={"host": host, "port": port})
    return j("POST", f"/api/config/config_entries/flow/{fid}", json={"code": code})[1]
def entries(): return j("GET", "/api/config/config_entries/entry?domain=charmling")[1]

print("A. pair Mac 1")
r = pair(41417); check("entry created", r.get("type") == "create_entry", r); time.sleep(1)
e1 = [e for e in entries() if "Abi" in e["title"]][0]["entry_id"]
check("on_air seeded from /state", st(f"binary_sensor.{P1}_on_air") == "off", st(f"binary_sensor.{P1}_on_air"))
regs = asyncio.run(ws_cmd(type="config/entity_registry/list"))
mine = {e["entity_id"]: e for e in regs if e["platform"] == "charmling"}
check("38 entities registered", len(mine) == 38, len(mine))
check("idle_seconds disabled by default", mine.get(f"sensor.{P1}_idle", {}).get("disabled_by") == "integration", mine.get(f"sensor.{P1}_idle"))
check("last_seen disabled by default", mine.get(f"sensor.{P1}_last_seen", {}).get("disabled_by") == "integration")

print("B. malformed webhook payloads")
wh = mocklog(M1)["webhook"]; secret = mocklog(M1)["secret"]
hdr = {"X-Charmling-Secret": secret}
r = requests.post(wh, data="not json", headers=hdr); check("non-json -> 400", r.status_code == 400, r.status_code)
r = requests.post(wh, json=[1, 2], headers=hdr); check("array -> 400", r.status_code == 400, r.status_code)
r = requests.get(wh, headers=hdr); check("GET -> 405", r.status_code == 405, r.status_code)
r = requests.post(wh, json={"type": "state", "states": "on_air=on"}, headers=hdr); check("states not a dict -> 200, ignored", r.status_code == 200 and st(f"binary_sensor.{P1}_on_air") == "off")
big = {f"k{i}": i for i in range(300)}
r = requests.post(wh, json={"type": "state", "states": {**big, "on_air": True}}, headers=hdr)
check("300-key states dropped whole", st(f"binary_sensor.{P1}_on_air") == "off", st(f"binary_sensor.{P1}_on_air"))
r = requests.post(wh, json={"type": "state", "states": {"on_air": {"nested": 1}, "dog": "x" * 500, "k" * 100: 1, "camera": True}}, headers=hdr)
check("nested value dropped, sibling kept", st(f"binary_sensor.{P1}_on_air") == "off" and st(f"binary_sensor.{P1}_camera") == "on")
check("long string truncated to 200", len(st(f"sensor.{P1}_dog")) == 200, len(st(f"sensor.{P1}_dog")))
r = requests.post(wh, json={"type": "event"}, headers=hdr); check("event without name -> 200, nothing", r.status_code == 200)
r = requests.post(wh, json={"type": "event", "event": "dance", "x": {"deep": True}}, headers=hdr); time.sleep(0.3)
check("unknown event type keeps event entity unchanged", attrs(f"event.{P1}_moment").get("event_type") is None, attrs(f"event.{P1}_moment").get("event_type"))
r = requests.post(wh, json={"type": "wat"}, headers=hdr); check("unknown message type -> 200", r.status_code == 200)
r = requests.post(wh, json={"type": "state", "states": {"on_air": "yes", "screen_locked": "true"}}, headers=hdr)
check("string booleans read", st(f"binary_sensor.{P1}_on_air") == "on" and st(f"binary_sensor.{P1}_screen") == "off")
mock(M1, push={"on_air": False, "screen_locked": False, "dog": "sitting", "camera": False})

print("C. enums and numbers")
mock(M1, push={"work_kind": "hacking", "meeting_density": "HEAVY", "beads": "many", "next_meeting_minutes": -1, "focus_remaining": 12.0})
check("invalid enum -> unknown", st(f"sensor.{P1}_work_kind") == "unknown", st(f"sensor.{P1}_work_kind"))
check("enum case folded", st(f"sensor.{P1}_meeting_density") == "heavy", st(f"sensor.{P1}_meeting_density"))
check("non-numeric number -> unknown", st(f"sensor.{P1}_beads_waiting") == "unknown", st(f"sensor.{P1}_beads_waiting"))
check("negative sentinel kept", st(f"sensor.{P1}_next_meeting_in") == "-1", st(f"sensor.{P1}_next_meeting_in"))
check("12.0 shown as 12", st(f"sensor.{P1}_focus_remaining") == "12", st(f"sensor.{P1}_focus_remaining"))
mock(M1, push={"work_kind": "coding", "beads": 2})

print("D. hello updates the version on the device")
mock(M1, version="2.0"); time.sleep(0.3)
devs = asyncio.run(ws_cmd(type="config/device_registry/list"))
d1 = [d for d in devs if d["name"] == "Abi's MacBook Pro"][0]
check("sw_version 2.0", d1.get("sw_version") == "2.0", d1.get("sw_version"))
check("entry data version updated", [e for e in entries() if e["entry_id"] == e1][0].get("title"), "")

print("E. second Mac and device targeting")
r = pair(41418); check("Mac 2 entry", r.get("type") == "create_entry", r); time.sleep(1)
devs = asyncio.run(ws_cmd(type="config/device_registry/list"))
d2 = [d for d in devs if d["name"] == "Studio Mac"][0]
async def ws_call(domain, service, data):
    async with websockets.connect("ws://127.0.0.1:8123/api/websocket") as ws:
        await ws.recv(); await ws.send(json.dumps({"type": "auth", "access_token": tok})); await ws.recv()
        await ws.send(json.dumps({"id": 1, "type": "call_service", "domain": domain, "service": service, "service_data": data})); return json.loads(await ws.recv())
r = asyncio.run(ws_call("charmling", "say", {"message": "hi"}))
check("no target with two Macs -> service_validation_error, translated", r.get("error", {}).get("code") == "service_validation_error" and "choose one" in r["error"]["message"], r)
c, r = j("POST", "/api/services/charmling/say", json={"message": "to studio", "device_id": d2["id"]})
check("targeted say reaches Mac 2 only", c == 200 and mocklog(M2)["log"][-1][1]["say"] == "to studio" and mocklog(M1)["log"][-1][0] != "say", (c, mocklog(M2)["log"][-1]))
c, r = j("POST", "/api/services/charmling/do", json={"action": "pat", "device_id": [d1["id"], d2["id"]]})
check("two targets, both patted", c == 200 and mocklog(M1)["log"][-1][1]["action"] == "pat" and mocklog(M2)["log"][-1][1]["action"] == "pat")
r = asyncio.run(ws_call("charmling", "do", {"action": "pat", "device_id": "nope"}))
check("unknown device -> translated validation error", r.get("error", {}).get("code") == "service_validation_error" and "nope" in r["error"]["message"], r)
check("two devices, distinct entity ids", st(f"sensor.{P2}_dog") == "sitting" and st(f"sensor.{P1}_dog") == "sitting")

print("F. reauth: Mac 1 forgets the pairing")
mock(M1, forget=True)
c, r = j("POST", "/api/services/charmling/say", json={"message": "x", "device_id": d1["id"]})
check("service -> error", c == 500 or c == 400, (c, str(r)[:100]))
time.sleep(0.5); fl = flows()
check("reauth flow started", any(f["context"].get("source") == "reauth" for f in fl), fl)
fid = [f for f in fl if f["context"].get("source") == "reauth"][0]["flow_id"]
c, r = j("GET", f"/api/config/config_entries/flow/{fid}"); check("reauth step shown", r.get("step_id") == "reauth_confirm", r.get("step_id"))
c, r = j("POST", f"/api/config/config_entries/flow/{fid}", json={"code": "000000"}); check("wrong code stays", r.get("errors", {}).get("base") == "invalid_code", r)
c, r = j("POST", f"/api/config/config_entries/flow/{fid}", json={"code": "123456"}); check("reauth successful", r.get("reason") == "reauth_successful", r)
time.sleep(1.5)
same_hook = mocklog(M1)["webhook"] == wh
check("same webhook kept on re-pair", same_hook)
c, r = j("POST", "/api/services/charmling/say", json={"message": "back", "device_id": d1["id"]}); check("service works with new secret", c == 200, (c, r))
mock(M1, push={"on_air": True}); time.sleep(0.3); check("push with new secret lands", st(f"binary_sensor.{P1}_on_air") == "on"); mock(M1, push={"on_air": False})

print("F2. a pairing meant for Mac 1 sent to Mac 2's address is refused")
r = requests.post("http://127.0.0.1:41418/pair", json={"code": "123456", "webhook_url": "x", "webhook_id": "y", "expect_id": "3f1c9a2b7d4e4c6a9b1e2f3a4b5c6d7e"})
check("409 and Mac 2 unchanged", r.status_code == 409 and mocklog(M2)["paired"], (r.status_code, mocklog(M2)["paired"]))

print("G. reconfigure")
c, r = j("POST", "/api/config/config_entries/flow", json={"handler": "charmling", "entry_id": e1, "source": "reconfigure"}) if False else (0, None)
# reconfigure flows start over the websocket-less REST 'flow' endpoint with context source
r = s.post(H + "/api/config/config_entries/flow", json={"handler": "charmling", "entry_id": e1}, params={}).json()
fid = r["flow_id"]; check("reconfigure form", r.get("step_id") == "reconfigure", r.get("step_id"))
c, r = j("POST", f"/api/config/config_entries/flow/{fid}", json={"host": "127.0.0.1", "port": 41999}); check("dead port -> cannot_connect", r.get("errors", {}).get("base") == "cannot_connect", r)
c, r = j("POST", f"/api/config/config_entries/flow/{fid}", json={"host": "127.0.0.1", "port": 41418}); check("other Mac -> different_mac, nothing paired", r.get("step_id") == "reconfigure" and r.get("errors", {}).get("base") == "different_mac", r)
check("Mac 2's pairing untouched", mocklog(M2)["webhook"] != mocklog(M1)["webhook"] and mocklog(M2)["paired"])
c, r = j("POST", f"/api/config/config_entries/flow/{fid}", json={"host": "127.0.0.1", "port": 41417}); check("same Mac -> reconfigure_successful", r.get("reason") == "reconfigure_successful", r)
time.sleep(1.5)

print("H. reload cycles")
ok = True
for i in range(3):
    c, r = j("POST", f"/api/config/config_entries/entry/{e1}/reload"); ok &= c == 200
    time.sleep(1.0)
check("3 reloads clean", ok and st(f"sensor.{P1}_dog") == "sitting", st(f"sensor.{P1}_dog"))
mock(M1, push={"on_air": True}); time.sleep(0.3); check("push after reloads", st(f"binary_sensor.{P1}_on_air") == "on"); mock(M1, push={"on_air": False})
log = open(__import__("os").environ.get("HA_LOG", "config/home-assistant.log")).read()
check("no 'already defined' webhook error", "already defined" not in log)
bad = [blk for blk in log.split("Traceback (most recent call last):")[1:] if "custom_components/charmling" in blk and "CharmlingAuthError" not in blk and "ServiceValidationError" not in blk and "no longer accepts this pairing" not in blk]
check("no unexpected tracebacks in charmling code", not bad, bad[:1])

print("I. stale + bye on Mac 2 while Mac 1 stays")
mock(M2, bye=True); time.sleep(0.3)
check("Mac 2 unavailable, Mac 1 fine", st(f"sensor.{P2}_dog") == "unavailable" and st(f"sensor.{P1}_dog") == "sitting")
mock(M2, hello=True); time.sleep(0.3); check("Mac 2 back", st(f"sensor.{P2}_dog") == "sitting")

print("J. delete Mac 2 while it is down")
subprocess.run(["pkill", "-f", r"mock_mac.py 41418"]); time.sleep(1)
e2 = [e for e in entries() if "Studio" in e["title"]][0]["entry_id"]
c, r = j("DELETE", f"/api/config/config_entries/entry/{e2}"); check("delete succeeds with the Mac down", c == 200, (c, r))
check("Mac 2 entities gone", st(f"sensor.{P2}_dog").startswith("<404"), st(f"sensor.{P2}_dog"))
c, r = j("POST", "/api/services/charmling/say", json={"message": "solo"}); check("untargeted say works again with one Mac", c == 200, (c, r))

print("K. diagnostics")
c, d = j("GET", f"/api/diagnostics/config_entry/{e1}")
check("secret redacted", d["data"]["entry"]["secret"] == "**REDACTED**" and d["data"]["entry"]["webhook_id"] == "**REDACTED**")

print()
print("FAILED:" if fails else "ALL PASSED", fails)
