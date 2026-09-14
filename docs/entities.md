# Every entity, and where it comes from

One device per Mac, named after the Mac. Entity ids below are for a Mac
called "Abi's MacBook Pro" (`abi_s_macbook_pro`); yours follow your Mac's
name. Rename the Mac and the entity ids stay: the device is known by a
random id the app made once, not by the name.

Every value is pushed by the Mac the second it changes. Nothing is polled.
The Mac re-sends everything every five minutes and on every wake, so a
Home Assistant restart never leaves a stale reading for long; on restart
the integration also asks the Mac for a full snapshot.

State leaves the Mac; content never does. No entity ever carries a window
title, a line of text, a meeting name, a file name or a bead's label.

## Reading "unknown" and "unavailable"

**Unavailable** (the whole device at once): the Mac sent `bye` (sleep, or
the app quit), or ninety seconds passed without a heartbeat (the Mac
sends one every thirty). Automations can trust "at the desk: off" only
while the device is available; treat unavailable as "the Mac is gone".

**Unknown** (one entity): the Mac has never sent that key. The usual reason
is that its group is switched off in Charmling's Home Assistant pane. Two
groups are off from the start because they name things: **the app in
front** (`sensor…_app_in_front`) and **the score**. Tick them on the Mac and
the value arrives within a second.

## Presence

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `binary_sensor…_at_the_desk` | occupancy | on / off | on while there was mouse, keyboard or scroll input in the last five minutes (`CGEventSource` idle time). No camera, no motion sensor: the keyboard is the sensor. |
| `sensor…_away` | duration, min | 0 while at the desk, then minutes since the last input | the same idle timer, in minutes, once past five |
| `sensor…_idle` | duration, s | seconds since the last input | **disabled by default** (it changes every heartbeat and would fill the recorder); enable it on the entity page if you want it |
| `binary_sensor…_screen` | lock | **off = locked**, on = unlocked | the `com.apple.screenIsLocked` / `screenIsUnlocked` notifications. Lock class in Home Assistant reads "on" as unlocked, so a locked screen shows **off**; the UI says Locked / Unlocked. |

Moments: `back_at_desk` and `left_desk` fire when at-the-desk flips (see [events](events.md)).

## On air

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `binary_sensor…_on_air` | running | on / off | the default input device's CoreAudio flag `DeviceIsRunningSomewhere`: any process has the microphone open. A muted Zoom keeps it open, so a call stays on air while muted, which is the right reading for a lamp. Three-second hold on the way off so a reconnect does not blink. No permission is needed to read the flag; no audio is ever read. |
| `binary_sensor…_camera` | running | on / off | CoreMediaIO's `DeviceIsRunningSomewhere` on every camera: some app has a camera open. No frames are read. |
| `binary_sensor…_call_app_in_front` | — | on / off | the front app's bundle id is one of: Zoom, Teams, FaceTime, Webex, Google Meet, a Slack huddle. Only the id is looked at, never the window. |
| `binary_sensor…_presenting` | — | on / off | Keynote or PowerPoint is the front app, or a call app is in front full-screen |

Moments: `call_started`, `call_ended` fire on the on-air edge.

Note that on air is the microphone, not the calendar: a voice memo, a
dictation and Siri all count. That is the correct reading of "the mic is
live"; if you want "in a meeting", combine it with `call_app_in_front` or
`next_meeting_in`.

## Focus

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `binary_sensor…_focus_session` | — | on / off | a Charmling focus session is running (started from the menu, the hotkey, or `charmling.do` with `focus`) |
| `sensor…_focus_remaining` | duration, min | minutes left, 0 when none | rounded up |

Moments: `focus_started` (with `minutes`), `focus_ended` (stopped early), `break` (ran to the end), `stretch` (the stretch-break nudge).

## Screen

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `binary_sensor…_full_screen` | — | on / off | the front window covers the screen: a film, a game, a full-screen call |
| `sensor…_work_kind` | enum | coding · writing · design · reading · browsing · chat · mail · meeting · media · spreadsheets · other · idle | the front app's bundle id against a fixed table (Xcode, VS Code and terminals are coding; Pages, Word, Notes, Obsidian are writing; Figma, Sketch, Photoshop are design; browsers are browsing whatever is in them; Slack and Messages are chat; Mail and Outlook are mail; Music, TV, Spotify are media; Numbers and Excel are spreadsheets). Idle after five minutes without input. A category, never a title. |
| `sensor…_app_in_front` | text | the app's name: Safari, Xcode | **off by default on the Mac** because it names an app. Never a window title. |

## Calendar

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `sensor…_next_meeting_in` | min | minutes to the next event that is not all-day and not cancelled; **unknown** when nothing is within 8 hours or the calendar is not readable | EventKit, only if Charmling's Meeting Radar was granted calendar access. The start time is all that is read; the title never leaves the Mac. Refreshed once a minute. |
| `sensor…_meeting_density` | enum | light · normal · heavy · unknown | Day Shape's reading of how full today is (under 20 % of the day in meetings is light, under 50 % normal, above that heavy) |

## The charm

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `sensor…_charm` | text | the charm on the cord, by id: `maneki`, `fox`, `bonsai`, `dragon`… | which charm is hanging |
| `binary_sensor…_wander_mode` | — | on / off | the cord is cut and the charm roams the desktop |
| `sensor…_beads_waiting` | count | things waiting on the cord | a count, never a label |
| `sensor…_basket` | count | files in the basket | a count, never a name |
| `sensor…_notification_banners_10_min` | count | macOS notification banners seen in the last ten minutes | the dog's habituation window; a count of banners on screen, never their content |
| `sensor…_on_the_shared_cord` | count | other Macs on the shared cord | |

Moments: `ritual` (with `charm`), `bead`, `cord_pulled`.

## The dog

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `binary_sensor…_pet_out` | — | on / off | a pet is on the cord instead of a charm |
| `sensor…_dog` | text | idle · walking · sitting · napping · lying down · trick · looking · carried · dropping · standing down · away | what he is doing right now; `away` is off on a sock errand |
| `sensor…_dog_s_name` | diagnostic | his name | |
| `sensor…_leash` | diagnostic | short · medium · long · extra long | the leash reach set with the scroll wheel |
| `switch…_hushed` | switch | on / off | read and set: hushed, he keeps the sound in and delivers with a look |
| `switch…_bark_muted` | switch | on / off | read and set: the bark clip is silent |

Moments: `bark`, `woof`, `trick` (with `trick`), `nap` (with `why`: `nap`, `absence`, `focus`, `hand`), `wake`, `delivered`.

Buttons on the device page: **Call the dog** (he walks to the pointer),
**Do the trick**, **Speak** (one woof, or a beg when hushed), **Pat**,
**Focus 25 minutes**, **Stop focus**, **Nap**, **Wake**. Without a dog on
the cord, Call, Speak, Hush and Nap answer "cannot do that right now";
Trick performs the charm's ritual and Pat is a double take.

## Live Scores

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `sensor…_live_score` | text | `Arsenal 2–1 Spurs` | **off by default on the Mac**. The followed match's headline, public data, from Charmling's Live Scores if it is on. |

## The device

| Entity | Type | Values | On the Mac |
|---|---|---|---|
| `event…_moment` | event | the moments listed in [events](events.md), with their data as attributes | |
| `sensor…_last_seen` | timestamp, diagnostic | the last message from the Mac | **disabled by default**; it keeps its value after the Mac goes, which is the point of it |

The device page also shows the app's version (updated from every hello),
and the three actions under "Device actions".

## What Home Assistant does with the numbers

Counts and durations carry `state_class: measurement`, so long-term
statistics work on them (average minutes away per day, how often the
basket fills). `next_meeting_in` is unknown rather than −1 when there is no
meeting, so the statistics are not polluted by a sentinel.

Enum sensors (`work_kind`, `meeting_density`) have their options declared,
so the UI offers them in a picker and a value outside the list reads
unknown rather than breaking the entity.
