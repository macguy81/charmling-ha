# Privacy

State leaves the Mac; content never does.

## What Home Assistant receives

On/off values, small numbers, and short words from fixed lists: whether
the microphone is open, whether you are at the desk, a category of work
("coding"), a count of beads, what the dog is doing. The full list is in
[entities](entities.md); every key is listed in [the protocol](protocol.md).

## What it never receives

A window title. A line of text from the screen. A meeting's title,
attendees or location (only the minutes until it starts). A file name
(only the count in the basket). A bead's label (only the count). A
notification's content (only how many banners). Audio (the microphone
flag is a CoreAudio property; no samples are read). Video (the camera flag
is a CoreMediaIO property; no frames are read). Anything from Day Memory.

Two values name things and are therefore **off by default** on the Mac:
the app in front (its name, "Safari", never its window) and the Live
Scores headline (public data). Each group can be switched off in
Charmling's Home Assistant pane; a switched-off group's entities read
unknown.

## Where it goes

To your Home Assistant, on your network, and nowhere else. The Mac pushes
to the webhook URL Home Assistant gave it at pairing; Home Assistant calls
the Mac's port for the three actions. No cloud, no third party, no
Charmling server. Nothing in this integration talks to the internet.

## How it is guarded

Pairing needs the six-digit code the Mac shows, good for ten minutes and
ten tries. It produces a 256-bit random secret; every message from the
Mac carries it in a header, every request from Home Assistant carries it
as a bearer token, and Home Assistant compares it in constant time. The
Mac keeps the secret and the webhook URL in its Keychain (this device
only); Home Assistant keeps them in the config entry, redacted from
diagnostics.

A pairing that names a different Mac is refused, so a re-pair aimed at
the wrong address cannot take over another Mac. Ten wrong codes burn the
code.

## What Home Assistant stores

The states, in its recorder, like any other sensor: on air at 10:02, at
the desk until 12:40, the dog napping at 15:10. That is the point of it,
and it is your database on your machine. Two values that would fill it
fastest (`idle_seconds`, `last_seen`) are disabled unless you enable them.

## Turning it off

Untick **Connect to Home Assistant** in the pane: the listener stops, the
Bonjour advert stops, nothing is pushed. Press **Unpair** to forget the
pairing. Delete the device in Home Assistant and the Mac is told to forget
it too. Nothing lingers.
