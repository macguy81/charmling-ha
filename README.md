<p align="center"><img src="custom_components/charmling/brand/logo@2x.png" alt="Charmling" height="128"></p>

# Charmling for Home Assistant

Your Mac, as a device in Home Assistant: whether you are at the desk, on a
call, in a focus session, what kind of work is in front of you, what the dog
is doing. Pushed the second it changes, over your own network. And the other
way: the house can have the charm or the dog say something, tend the
Garden when a real plant is watered, call the dog over, start a focus.

State leaves the Mac; content never does. Home Assistant never receives a
window title, a line of text, a meeting name, or a bead's label. Only
on/off, small numbers and short words.

## Install

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=macguy81&repository=charmling-ha&category=integration)

One press of that button opens your Home Assistant with this repository
ready to add in HACS. Press **Add**, then **Download**, restart Home
Assistant, and go to Settings → Devices & services: your Mac is waiting there.

By hand, without HACS: in HACS → Integrations → ⋮ → Custom repositories,
paste `https://github.com/macguy81/charmling-ha`, type Integration. Or copy
`custom_components/charmling` into your `config/custom_components/` folder
and restart Home Assistant.

## Pair

1. On the Mac, open Charmling's menu → **🏠 Home Assistant…**. The pane shows
   a six-digit code.
2. In Home Assistant, go to **Settings → Devices & services**. The Mac shows
   up as discovered ("Charmling on Abi's MacBook Pro"). Press **Add**.
3. Type the code. Done.

Not found? Press **Add integration**, search Charmling, type the Mac's
address (the pane shows the port). The Mac and Home Assistant must be on the
same network, or reach each other over something like Tailscale.

Pairing hands Home Assistant a secret and hands the Mac a webhook. Every
message from the Mac carries the secret; every request from Home Assistant
to the Mac carries it too. Delete the device in Home Assistant and the Mac
forgets the pairing. Press **Unpair** on the Mac and Home Assistant asks you
to pair again (a reauth flow, same device, same entities). If the Mac moves
to a new address, Bonjour usually tells Home Assistant; if not, **Reconfigure**
on the device takes the new address.

## Why not just the companion app?

The official companion app reports the camera, the microphone, the front
app and an Apple Focus, and it is good; run both if you like. Charmling
adds meaning (in a call, presenting, the kind of work, minutes to the next
meeting, at the desk by your hands on the keys), pushes every change in a
second with a proper goodbye when the Mac sleeps, and lets the house talk
back through the charm or the dog. [The longer answer, and what the
community's on-air-light threads taught us](docs/why.md).

## The docs

- [Why this, and what the community taught us](docs/why.md)

- [Every entity, and where it comes from](docs/entities.md)
- [Moments (events)](docs/events.md)
- [The house talks back (actions)](docs/actions.md)
- [The cookbook: automations for everything](docs/cookbook.md)
- [The protocol between the Mac and Home Assistant](docs/protocol.md)
- [Privacy](docs/privacy.md)
- [Troubleshooting](docs/troubleshooting.md)

## What you get

One device per Mac, named after it, with these entities. Names below are
for a Mac called "Abi's MacBook Pro"; yours follow your Mac's name.

| Entity | What it is |
|---|---|
| `binary_sensor.abi_s_macbook_pro_on_air` | the microphone is open by any app: a call (a muted Zoom keeps it open). Three-second hold on the way off. |
| `binary_sensor…_in_a_call` | on air, and the app recording is a call app: a voice memo is not a meeting |
| `binary_sensor…_camera` | a camera is open by any app |
| `binary_sensor…_call_app_in_front` | Zoom, Teams, Meet, FaceTime, Webex or a huddle is the front app |
| `binary_sensor…_presenting` | Keynote or PowerPoint in front, or a full-screen call |
| `binary_sensor…_at_the_desk` | input in the last five minutes (occupancy) |
| `binary_sensor…_screen` | lock class: off means the screen is locked |
| `binary_sensor…_display_asleep` | the screen went dark |
| `binary_sensor…_do_not_disturb`, `sensor…_focus_mode` | a macOS Focus is on, and which kind (work, sleep, do not disturb…) |
| `binary_sensor…_focus_session`, `sensor…_focus_remaining` | the focus session and its minutes left |
| `binary_sensor…_full_screen` | something full-screen in front |
| `sensor…_work_kind` | coding, writing, design, reading, browsing, chat, mail, meeting, media, spreadsheets, other, idle. A category from the front app, never a title. |
| `sensor…_app_in_front` | the app's name (Safari, Xcode). Off by default on the Mac. |
| `sensor…_idle`, `sensor…_away` | seconds idle (disabled by default: it changes every heartbeat), minutes away |
| `sensor…_next_meeting_in` | minutes to the next meeting; −1 when none in 8 h or no calendar access. Never the title. |
| `sensor…_meeting_density` | light, normal, heavy: how full the day is |
| `sensor…_charm`, `binary_sensor…_wander_mode` | which charm is on the cord, and whether it roams |
| `sensor…_beads_waiting`, `sensor…_basket`, `sensor…_notification_banners_10_min`, `sensor…_on_the_shared_cord` | counts, never labels |
| `binary_sensor…_pet_out`, `sensor…_dog`, `sensor…_dog_s_name`, `sensor…_leash` | the dog and what he is doing: idle, walking, sitting, napping, lying down, trick, looking, carried, standing down |
| device triggers | every moment below, as a sentence in the automation editor's device picker |
| `switch…_hushed`, `switch…_bark_muted` | read and set |
| `sensor…_live_score` | the followed match. Off by default on the Mac. |
| `event…_moment` | the moments (below), as an event entity |
| `sensor…_last_seen` | the last heartbeat (disabled by default) |
| buttons | Call the dog, Do the trick, Speak, Pat, Focus 25 minutes, Stop focus, Nap, Wake |

The whole device goes **unavailable** when the Mac sleeps, the app quits, or
ninety seconds pass without a heartbeat, so an automation can trust "at the
desk: off" rather than a stale on.

## Moments

Fired on the bus as `charmling_event` with `type`, `node` and `device_id`,
and mirrored on the event entity: `call_started`, `call_ended`,
`focus_started` (`minutes`), `focus_ended`, `break`, `stretch`, `ritual`
(`charm`), `bead`, `bark`, `woof`, `trick`, `nap` (`why`), `wake`,
`delivered`, `back_at_desk`, `left_desk`.

In the automation editor: Trigger → Device → the Mac → "the dog woofed".
In YAML, either the device trigger or the bus event:

```yaml
triggers:
  - trigger: device
    domain: charmling
    device_id: 1c9a2b…
    type: woof
  # or
  - trigger: event
    event_type: charmling_event
    event_data: {type: woof}
```

## The house talks back

Three actions, all targeting the Mac's device (or no target, when one Mac is paired).

**`charmling.say`** — a line, said the way whatever is on the cord says
things. `category` picks the manner: `arrival` (the greeting: the charm's
ritual, or the dog walks over), `alert` (the dog delivers it in person, one
woof, or a look when hushed; the charm double-takes and hangs a bead),
`done` (a flick and a bead), `ambient` (a bead only, nothing else),
`emergency` (a full bark, hush or no hush, confetti, a system notification).

```yaml
action: charmling.say
data:
  message: "🔔 someone at the door"
  category: alert
```

**`charmling.water`** — `plant: bonsai` or `dragon`. Tends the Garden the
way the menu does, once per day; confetti if it grew. For a real plant's
moisture sensor.

**`charmling.do`** — `action`: `call`, `trick`, `speak`, `pat`, `hush`,
`unhush`, `mute`, `unmute`, `focus` (with `minutes`), `stop_focus`,
`unclip`, `clip`, `nap`, `wake`.

## Automations people actually make

The on-air lamp:

```yaml
alias: Office door lamp
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_on_air
actions:
  - action: light.turn_on
    target: {entity_id: light.office_door}
    data:
      color_name: "{{ 'red' if trigger.to_state.state == 'on' else 'white' }}"
```

Focus dims the room; the break brings it back:

```yaml
alias: Focus scene
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: focus_started}
actions:
  - action: scene.turn_on
    target: {entity_id: scene.office_focus}
```

The doorbell, delivered by the dog:

```yaml
alias: Doorbell, in person
triggers:
  - trigger: state
    entity_id: binary_sensor.front_door_button
    to: "on"
actions:
  - action: charmling.say
    data: {message: "🔔 door", category: alert}
```

The bonsai's real moisture sensor waters the Garden:

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.bonsai_moisture
    above: 40
actions:
  - action: charmling.water
    data: {plant: bonsai}
```

Treat the office as empty when the Mac has been away a while:

```yaml
conditions:
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_at_the_desk
    state: "off"
    for: "00:15:00"
```

## How it works

The Mac runs a small listener on port 41417, advertised over Bonjour as
`_charmling._tcp` so Home Assistant discovers it. The Mac is known by a
random id it made once, not by its name, so renaming it renames the device
and nothing else. Pairing is one POST with the code; the Mac answers with a
secret. A pairing that names a different Mac is refused, so a re-pair aimed
at the wrong address cannot take over another Mac. From then on the Mac pushes to a
Home Assistant webhook: a hello with every state on connect and on wake,
only what changed after that, a heartbeat every thirty seconds, a goodbye
on sleep and quit. Home Assistant reaches the Mac for `say`, `water` and
`do`, and reads `/state` once on start. Nothing is polled; nothing leaves
your network.

## Tested

hassfest (Home Assistant's own integration validator) and ruff pass in CI
on every push, along with a pytest suite (`tests/`, on
pytest-homeassistant-custom-component, 59 tests) covering every flow, the webhook,
every platform, the services and their failure modes. `tests/live` holds
a second suite that drives a real Home Assistant with two pretend Macs
through pairing, malformed input, two devices, reauth, reconfigure,
reloads and restarts.

## Notes

- On-air is the microphone. A voice memo counts. That is the correct
  reading of "the mic is live".
- The Mac's pane lets you switch groups of signals off (the app in front and
  the score are off to begin with). Switched-off entities read unknown.
- Home Assistant behind HTTPS with a self-signed certificate: the Mac will
  refuse the webhook. Set an `http://` internal URL in Settings → System →
  Network.
- macOS asks once for Local Network permission when Charmling looks for
  Home Assistant. Declining is fine; pairing by address still works.
