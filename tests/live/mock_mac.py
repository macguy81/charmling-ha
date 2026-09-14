"""A pretend Charmling on a Mac: the endpoints, the pairing code, the webhook push."""
import asyncio
import secrets
import sys

from aiohttp import ClientSession, web

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 41417
CODE = "123456"
SECRET = None
WEBHOOK = None
NODE = sys.argv[2] if len(sys.argv) > 2 else "3f1c9a2b7d4e4c6a9b1e2f3a4b5c6d7e"
NAME = sys.argv[3] if len(sys.argv) > 3 else "Abi's MacBook Pro"
states = {"on_air": False, "camera": False, "in_call_app": False, "presenting": False,
          "at_desk": True, "screen_locked": False, "idle_seconds": 4, "away_minutes": 0,
          "focus": False, "focus_remaining": 0, "screen_full": False, "work_kind": "coding",
          "next_meeting_minutes": 42, "meeting_density": "light", "wander": False, "charm": "maneki",
          "beads": 2, "basket": 0, "banners_10min": 1, "cord_friends": 0, "pet_out": True,
          "dog": "sitting", "dog_name": "Biscuit", "hushed": False, "muted": False, "leash": "medium",
          "in_call": False, "display_asleep": False, "do_not_disturb": False, "focus_mode": "off"}
log = []

def auth(req):
    return SECRET and req.headers.get("Authorization") == f"Bearer {SECRET}"

async def ident(req):
    return web.json_response({"id": NODE, "name": NAME, "version": "1.9", "paired": bool(SECRET)})

async def pair(req):
    global SECRET, WEBHOOK
    b = await req.json()
    if b.get("expect_id") and b["expect_id"] != NODE:
        return web.json_response({"error": "not that Mac", "id": NODE}, status=409)
    if b.get("code") != CODE:
        return web.json_response({"error": "bad code"}, status=403)
    SECRET = secrets.token_urlsafe(24); WEBHOOK = b["webhook_url"]
    log.append(("pair", b))
    return web.json_response({"id": NODE, "name": NAME, "secret": SECRET, "version": "1.9"})

async def state(req):
    if not auth(req): return web.Response(status=401)
    return web.json_response({"id": NODE, "name": NAME, "version": "1.9", "states": states})

async def say(req):
    if not auth(req): return web.Response(status=401)
    log.append(("say", await req.json())); return web.json_response({"ok": True})

async def water(req):
    if not auth(req): return web.Response(status=401)
    log.append(("water", await req.json())); return web.json_response({"ok": True})

async def do(req):
    if not auth(req): return web.Response(status=401)
    b = await req.json(); log.append(("do", b))
    if b["action"] == "hush": states["hushed"] = True; asyncio.create_task(push({"hushed": True}))
    if b["action"] == "unhush": states["hushed"] = False; asyncio.create_task(push({"hushed": False}))
    return web.json_response({"ok": True})

async def unpair(req):
    global SECRET
    if not auth(req): return web.Response(status=401)
    SECRET = None; log.append(("unpair", {})); return web.json_response({"ok": True})

async def control(req):
    """Test driver: POST {"push": {...}} or {"event": "woof", ...} or {"bye": true} or GET log."""
    global SECRET
    if req.method == "GET": return web.json_response({"log": log, "paired": bool(SECRET), "webhook": WEBHOOK, "secret": SECRET})
    b = await req.json()
    if "forget" in b: SECRET = None; return web.json_response({"status": "forgot"})
    if "raw" in b: r = await send(b["raw"]); return web.json_response({"status": r})
    if "push" in b: states.update(b["push"]); r = await push(b["push"])
    elif "version" in b: r = await send({"type": "hello", "version": b["version"], "states": states})
    elif "event" in b: r = await send({"type": "event", **b})
    elif "bye" in b: r = await send({"type": "bye"})
    elif "hello" in b: r = await send({"type": "hello", "version": "1.9", "states": states})
    return web.json_response({"status": r})

async def send(body):
    if not WEBHOOK: return "unpaired"
    url = WEBHOOK if WEBHOOK.startswith("http") else "http://127.0.0.1:8123" + WEBHOOK
    async with ClientSession() as s, s.post(url, json=body, headers={"X-Charmling-Secret": SECRET}) as r:
        return r.status

async def push(changed):
    return await send({"type": "state", "states": changed})

app = web.Application()
app.add_routes([web.post("/pair", pair), web.get("/id", ident), web.get("/state", state), web.post("/say", say), web.post("/water", water),
                web.post("/do", do), web.post("/unpair", unpair), web.route("*", "/_test", control)])
web.run_app(app, host="127.0.0.1", port=PORT, print=None)
