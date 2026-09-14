# Changelog

## 1.0.0

The first release.

- Discovery over Bonjour, pairing with a six-digit code, one device per Mac
- 38 entities: binary sensors, sensors, an event entity, buttons, switches
- The `say`, `water` and `do` actions
- Reauth when the Mac forgets the pairing; Reconfigure for a Mac that moved
- The Mac pushes over a webhook; ninety seconds of silence marks the device unavailable
- Diagnostics with the secret redacted
- A pairing meant for another Mac is refused without side effects (`expect_id`)
- `next_meeting_in` reads unknown, not −1, when there is no meeting
- Multi-target actions try every Mac and report the ones that failed
- Noisy diagnostics (`idle_seconds`, `last_seen`) disabled by default
- `in_a_call`: on air narrowed to call apps, from CoreAudio's per-process recording flag (macOS 14.2+)
- `display_asleep`, `do_not_disturb` and `focus_mode` (the Apple Focus kind)
- Every moment as a device trigger in the automation editor
- Icon translations; `dog` and `leash` as enums with translated states
