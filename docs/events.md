# Moments

A moment is something that happened, as opposed to a state that is true
for a while. The Mac fires them the instant they happen; Home Assistant
gets them two ways at once.

**On the bus**, as `charmling_event`, with `type` naming the moment,
`node` (the Mac's id), `device_id`, and the moment's own fields. This is
the one for automations:

```yaml
triggers:
  - trigger: event
    event_type: charmling_event
    event_data:
      type: woof
```

Leave `event_data` at just `type` unless you have more than one Mac, then
add `device_id` (Developer Tools → Events → listen to `charmling_event`
shows the exact payload).

**As device triggers**, which is the easiest: in the automation editor
choose Trigger → Device, pick the Mac, and every moment is in the list as
a sentence ("the dog on Abi's MacBook Pro woofed", "Abi's MacBook Pro went
on air"). Nothing to type. In YAML that is:

```yaml
triggers:
  - trigger: device
    domain: charmling
    device_id: 1c9a2b…
    type: woof
```

**On the event entity** `event…_moment`, which holds the last moment and
its fields as attributes, so it shows in the logbook and on a dashboard,
and can trigger a state-based automation:

```yaml
triggers:
  - trigger: state
    entity_id: event.abi_s_macbook_pro_moment
    attribute: event_type
    to: focus_started
```

## The list

| Type | When | Fields |
|---|---|---|
| `call_started` | the microphone went on air (three-second hold on the way off, none on the way on) | `test: true` when fired by the pane's Test on air |
| `call_ended` | off air | |
| `focus_started` | a focus session began | `minutes` |
| `focus_ended` | it was stopped before the end | |
| `break` | it ran to the end | |
| `stretch` | the stretch-break nudge (every 50 minutes at the desk) | |
| `ritual` | the charm did its ritual: the Maneki beckoned, the fox rang its bell | `charm` |
| `bead` | something was hung on the cord | (never the label) |
| `cord_pulled` | the cord was pulled | |
| `bark` | a full bark (a delivery, or a house emergency) | |
| `woof` | one woof (a delivery) | |
| `trick` | he did the trick | `trick` |
| `nap` | he lay down | `why`: `nap` (the nap clock), `absence` (you left), `focus` (a focus session), `hand` (a pat or hush sent him down) |
| `wake` | up again | |
| `delivered` | he carried a line to the pointer and said it | |
| `back_at_desk` | input after five or more minutes without | |
| `left_desk` | five minutes without input | |

Every moment also refreshes the device's availability, like a heartbeat.

## Which to use

A moment is right when you want to react *once* to something happening:
flash a bulb on the woof, start a playlist when focus starts. A state is
right when you want something to *stay* true while the situation lasts:
the lamp is red for as long as `on_air` is on. Moments are not replayed
after a Home Assistant restart; states are re-sent by the Mac.
