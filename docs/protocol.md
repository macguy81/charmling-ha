# The protocol

How the Mac and Home Assistant talk. Everything here is on your own
network, in plain JSON, and small enough to read with `curl`. This is the
contract the integration is tested against; anything else that speaks it
(a script, another home platform) gets the same device.

## Discovery

The Mac advertises itself over Bonjour / mDNS:

```
service  _charmling._tcp.local.
name     Charmling on Abi's MacBook Pro
port     41417 (any free port if that one is taken)
TXT      id=<32 hex chars>   a random id the app made once and keeps
         name=<the Mac's name>
         ver=<the app's version>
```

Home Assistant's zeroconf discovery watches for `_charmling._tcp.local.`
and offers the Mac under Settings → Devices & services. `id` is the
device's unique id; if it is missing the advert is ignored.

## The Mac's endpoints

A small HTTP/1.1 server on the Mac, one request per connection
(`Connection: close`), JSON in and out, bodies up to 256 KiB. All but the
first two require `Authorization: Bearer <secret>`.

### `GET /id`

Who is here. No secret: it is what the Bonjour record says anyway.

```json
{"id": "3f1c…", "name": "Abi's MacBook Pro", "version": "1.9", "paired": false}
```

### `POST /pair`

```json
{"code": "482913", "webhook_url": "http://homeassistant.local:8123/api/webhook/<id>",
 "webhook_id": "<id>", "expect_id": "3f1c…"}
```

`code` is the six digits Charmling's pane shows, made when the pane opens,
good for ten minutes and ten tries; after ten wrong tries a fresh one
appears. `expect_id` is optional: when present and not this Mac's id, the
Mac answers **409** and changes nothing, so a re-pair aimed at the wrong
address cannot take over another Mac. Home Assistant sends it whenever it
knows which Mac it means (discovered, or re-pairing).

Reply, **200**:

```json
{"id": "3f1c…", "name": "Abi's MacBook Pro", "secret": "<43 url-safe chars>", "version": "1.9"}
```

**403** for a wrong, expired or burned code (the reply never says which
digit was wrong). **400** without a `webhook_url`. Pairing replaces any
earlier pairing: a Mac pairs with one Home Assistant at a time; the
previous one starts getting 401s and offers a re-pair.

The Mac stores the webhook URL and the secret in its Keychain (this
device only), restarts its bridge, and within a second posts a `hello`.

### `GET /state`

```json
{"id": "3f1c…", "name": "Abi's MacBook Pro", "version": "1.9",
 "states": {"on_air": false, "at_desk": true, "idle_seconds": 4, "work_kind": "coding", "dog": "sitting", …}}
```

The same keys the webhook carries (see below). Home Assistant reads it
once on every start, so a restart never waits for the next push.

### `POST /say`

```json
{"as": "alert", "say": "🔔 door", "sound": true}
```

`as` is `arrival`, `alert`, `done`, `ambient` or `emergency` (unknown
values read as `alert`); `say` is folded to one line and cut at 200
characters. **400** when `say` is empty.

### `POST /water`

```json
{"plant": "bonsai"}
```

`bonsai` or `dragon`.

### `POST /do`

```json
{"action": "focus", "minutes": 40}
```

`action` is one of `call`, `trick`, `speak`, `pat`, `hush`, `unhush`,
`mute`, `unmute`, `focus`, `stop_focus`, `unclip`, `clip`, `nap`, `wake`.
**200** when done, **409** when it cannot be done right now (no dog on the
cord, for the dog's actions), **400** for no action.

### `POST /unpair`

Forgets the pairing; the pane shows a code again. Home Assistant calls it
when the device is deleted there.

### Errors

**401** for a missing or wrong secret on the guarded endpoints. **404**
for anything else. Every error body is `{"error": "…"}`.

## The webhook: the Mac pushes

`POST <webhook_url>` with header `X-Charmling-Secret: <secret>` and a JSON
body. Home Assistant answers `200 ok` (the text `ok`, which is how the Mac
knows the integration is still there: an empty 200 is Home Assistant's
answer for a webhook it no longer has, and the Mac then shows a code
again), `401` for a wrong secret, `400` for a body that is not a JSON
object.

The Mac pushes on one connection at a time, so messages arrive in the
order they were made.

### `state`

```json
{"type": "state", "states": {"on_air": true}}
```

Only what changed since the last message, one message per second at most.
Everything is re-sent every five minutes. Values are booleans, integers or
short strings; Home Assistant drops nested values, keys over 64
characters, strings over 200 characters, and any message with more than
200 keys.

### `hello`

```json
{"type": "hello", "version": "1.9", "states": { …every key… }}
```

On pairing, on every wake from sleep, and after Home Assistant was
unreachable. The version updates the device page.

### `event`

```json
{"type": "event", "event": "trick", "trick": "roll"}
```

The moment's name in `event`, its fields beside it. Home Assistant fires
`charmling_event` on the bus with `type`, `node`, `device_id` and those
fields, and updates the event entity when the name is one it knows.

### `ping`

```json
{"type": "ping"}
```

Every thirty seconds when nothing changed. Ninety seconds without any
message and Home Assistant marks the device unavailable.

### `bye`

```json
{"type": "bye"}
```

On sleep, on quit, on unpair. The device goes unavailable at once.

## The keys

| Key | Type | |
|---|---|---|
| `on_air`, `in_call`, `camera`, `in_call_app`, `presenting` | bool | |
| `at_desk`, `screen_locked`, `display_asleep`, `do_not_disturb` | bool | `screen_locked` true means locked |
| `focus_mode` | string | off / do_not_disturb / work / personal / sleep / driving / fitness / gaming / mindfulness / reading / custom |
| `idle_seconds`, `away_minutes` | int | |
| `focus` | bool | `focus_remaining` int, minutes |
| `screen_full` | bool | `work_kind` string, one of the twelve |
| `front_app` | string | only when the group is on |
| `next_meeting_minutes` | int | −1 for none / no access |
| `meeting_density` | string | light / normal / heavy / unknown |
| `wander` | bool | `charm` string |
| `beads`, `basket`, `banners_10min`, `cord_friends` | int | |
| `pet_out`, `hushed`, `muted` | bool | `dog`, `dog_name`, `leash` string |
| `score` | string | only when the group is on |

## Trying it by hand

```bash
curl -s http://abis-macbook-pro.local:41417/id
curl -s -H "Authorization: Bearer $SECRET" http://abis-macbook-pro.local:41417/state | jq .states.on_air
curl -s -H "Authorization: Bearer $SECRET" -H "Content-Type: application/json" \
     -d '{"as":"alert","say":"hello from curl"}' http://abis-macbook-pro.local:41417/say
```

The secret is not shown anywhere on purpose; take it from Home Assistant's
`.storage/core.config_entries` if you need it for a script, or pair your
script as its own "Home Assistant" with the code.

## What is deliberately absent

No TLS (the network is yours; the secret is the gate, and a wrong one is
answered in constant time). No polling. No content: not a title, not a
line of text, not a name of a file or a meeting. The Mac decides what to
send; Home Assistant only ever gets what the pane's groups allow.
