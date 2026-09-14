# Live tests

Not unit tests: these drive a real Home Assistant with two pretend Macs.
`mock_mac.py` is the Mac's side of the protocol (the `/id`, `/pair`,
`/state`, `/say`, `/water`, `/do`, `/unpair` endpoints and the webhook
push), plus a `/_test` control endpoint the suite pokes.

```bash
# a Home Assistant with this integration in custom_components, onboarded,
# a long-lived token in HA_TOKEN
python mock_mac.py 41417 &
python mock_mac.py 41418 9e8d7c6b5a4f4e3d2c1b0a9f8e7d6c5b "Studio Mac" &
HA_TOKEN=... HA_LOG=/path/to/home-assistant.log python live_suite.py
```

The suite pairs both Macs, then: malformed and oversized webhook payloads,
wrong types, unknown keys and event types, enum and number edge cases, the
version on the device, two Macs with device-targeted services, a Mac that
forgot its pairing (the reauth flow), a pairing aimed at the wrong Mac
(refused, nothing changes), the reconfigure flow, three reload cycles, bye
and hello, deleting a Mac that is down, diagnostics redaction. Every line
prints `ok` or `FAIL`.
