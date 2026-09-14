# Why this, and what the community taught us

Home Assistant people have been wiring their desks into the house for
years: on-air lights, "in a meeting" sensors, desk presence. Reading the
threads before building this was the best hour spent on it. What they
wanted, what kept going wrong, and what that changed here.

## "Why not just the companion app?"

The official Home Assistant companion app for macOS already reports
whether the camera and microphone are in use, the frontmost app, an Apple
Focus, and whether the Mac is active. If that is all you want, use it; it
is free and it is official. Run both, even: they do not fight.

Charmling adds four things the companion app does not do.

**Meaning, not raw signals.** The companion app tells you the microphone
is in use. Charmling tells you that, and also that a *call app* holds it
(`in_a_call`, so a voice memo is not a meeting), that you are presenting,
what kind of work is in front (a category, never a title), how many
minutes to the next meeting, how heavy the day is, and whether you are
at the desk by the only signal that cannot lie: your hands on the keys.

**Push, in a second.** The Mac sends every change the moment it happens
on one ordered connection, with a heartbeat and a goodbye, so the device
goes unavailable when the Mac sleeps instead of freezing on "at the desk".

**The house talks back, in character.** A doorbell delivered by a dog who
walks to your pointer and woofs is not a notification. The `say`, `water`
and `do` actions, the buttons and the switches are the part people show
their friends.

**Nothing to install on the Home Assistant side but this integration, and
nothing to configure.** Discovery, a six-digit code, done. No tokens, no
MQTT broker, no YAML.

## What the threads kept saying

**"It lit up when I was only listening."** The most common complaint about
busy lights: a conference app open, camera off, muted, and the lamp still
red. The honest answer is that no tool can read an app's mute button.
What can be done is to separate the signals, so people compose their own
rule: `on_air` (any recording), `in_a_call` (a call app recording),
`camera` (a camera open). "On air AND camera" is the strict version;
"in a call" is the sensible default.

**"It says the mic is on and it is not."** A known false positive with
audio interfaces: a device that both records and plays reads as "running"
while music plays. On macOS 14.2 and later Charmling asks CoreAudio which
*process* is recording, the same fact the orange dot in the menu bar
uses, so this cannot happen. Before 14.2 it only looks at input-only
devices, which sidesteps the interface case.

**"The update took minutes."** Sensors that report on a schedule make a
lamp that is late. Everything here is pushed on the change, and the tests
hold it to within a second.

**"It stayed on after the laptop went to sleep."** Presence that never
goes stale is worse than none. The Mac says goodbye on sleep, and ninety
seconds of silence marks the device unavailable regardless.

**"Corporate IT won't let me install agents."** Charmling is an ordinary
menu-bar app with no admin rights, no kernel extension, no Teams API to
enable and no Graph permissions to beg for; it reads system facts macOS
exposes to any app.

**"I don't want it phoning home about my screen."** Neither do we. State
leaves the Mac; content never does, and the [privacy page](privacy.md)
lists exactly what that means.

**"I had to type event data by hand."** Every moment is a device trigger,
so the automation editor lists them as sentences. The bus event and the
event entity are still there for YAML people.

**"It spammed my recorder."** The two values that change every heartbeat
are disabled by default.

**"The entities got renamed and my automations broke."** Entity ids
follow the Mac's name only at creation; the unique ids are a random id
the app made once, so renaming the Mac renames the device and nothing
else. Enums (`work_kind`, `dog`, `focus_mode`, `meeting_density`,
`leash`) have declared options, so a value outside the list reads
unknown rather than breaking anything.

**"The integration broke on the next HA release."** hassfest, the HACS
check and a 51-test suite run on every push, against the current Home
Assistant.

## What it deliberately does not do

Read your Teams or Zoom status from their APIs (they change, they need
admin consent, and the microphone is the truth anyway). Tell whether you
are muted. Send a title, a name or a line of text. Poll.

## Sources

The threads and pages that shaped this: the community's
[On Air light for work from home](https://community.home-assistant.io/t/on-air-light-for-work-from-home/244333)
and [Teams meeting status](https://community.home-assistant.io/t/teams-meeting-status/523649)
threads, the [companion app's macOS sensor list](https://github.com/home-assistant/companion.home-assistant/blob/master/docs/core/sensors.md),
a [false-positive report](https://community.home-assistant.io/t/macos-active-audio-input-incorrect/893624)
on audio interfaces, and the [integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist).
