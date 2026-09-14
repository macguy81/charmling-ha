# The house talks back

Three actions. Each targets a Mac's device; with one Mac paired the target
can be left out. Each is also on the device page under "Device actions",
and the most useful ones are buttons and switches there too.

All three go to the Mac over your network with the pairing secret, and
answer within a second. If the Mac is asleep the action fails with
"could not be reached"; if the Mac has unpaired, it fails with "no longer
accepts this pairing" and a re-pair flow appears under Settings → Devices
& services. With several targets, every Mac is tried and the error names
the ones that failed.

## `charmling.say`

A line, said the way whatever is on the cord says things.

```yaml
action: charmling.say
target:
  device_id: 1c9a2b…        # optional with one Mac
data:
  message: "🔔 someone at the door"
  category: alert            # arrival · alert · done · ambient · emergency
  sound: true                # false keeps it silent
```

`message` is up to 200 characters, shown above the charm or the dog. It is
folded to one line. Emoji work.

`category` is the manner, and the manner is what makes it feel like the
house rather than a notification:

| Category | The charm | The dog |
|---|---|---|
| `arrival` | its ritual (the Maneki beckons, the fox rings) and the line | the greeting: he walks over, the line above his head |
| `alert` | double take, a bead, the line | delivered in person: walks to the pointer, one woof (a look, when hushed), the line |
| `done` | a flick of the cord, a bead, the line | delivered in person |
| `ambient` | a bead, nothing else | a bead, nothing else |
| `emergency` | confetti, double take, a bead, the line held, a system notification, a sound | a full bark, hush or no hush, mute or no mute; the notification too |

`ambient` is for things you want to find later, not be interrupted by:
the bead hangs on the cord and clicking it opens Home Assistant.
`emergency` is for smoke and water: it cuts through hush and mute, so
keep it for that.

## `charmling.water`

```yaml
action: charmling.water
data:
  plant: bonsai              # bonsai · dragon
```

Tends the Garden the way the menu does, once per day; confetti if it
grew. Meant for a real plant's moisture sensor: when the real bonsai is
watered, the one on the cord is too.

## `charmling.do`

```yaml
action: charmling.do
data:
  action: focus              # see the list
  minutes: 25                # for focus only; 1–180, 25 if left out
```

| Action | The dog | Without a dog |
|---|---|---|
| `call` | walks to the pointer | not now |
| `trick` | the trick, whatever he was doing | the charm's ritual |
| `speak` | one woof (a beg, when hushed) | not now |
| `pat` | a pat: a look up, and he remembers; three quick ones and he rolls over | a double take |
| `hush` / `unhush` | hushed for an hour / un-hushed with a woof about it | not now |
| `mute` / `unmute` | the bark clip silent / back | not now |
| `focus` / `stop_focus` | a focus session (the cord stands down, the dog naps) / stop it | the same |
| `unclip` / `clip` | the leash off, he roams / back on, he comes home | Wander Mode on / off for the charm |
| `nap` / `wake` | ten to fifteen minutes down / up | not now |

"Not now" is a 409 from the Mac and reads as "cannot do that right now"
in the automation trace; it is not an error worth alerting on.

## From a dashboard

The buttons (Call the dog, Do the trick, Speak, Pat, Focus 25 minutes,
Stop focus, Nap, Wake) and switches (Hushed, Bark muted) are entities, so
a tile card of them is the whole dog remote:

```yaml
type: entities
title: The dog
entities:
  - sensor.abi_s_macbook_pro_dog
  - switch.abi_s_macbook_pro_hushed
  - switch.abi_s_macbook_pro_bark_muted
  - button.abi_s_macbook_pro_call_the_dog
  - button.abi_s_macbook_pro_do_the_trick
  - button.abi_s_macbook_pro_speak
  - button.abi_s_macbook_pro_pat
```
