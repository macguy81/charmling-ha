# Troubleshooting

## The Mac is not in the discovered list

Discovery is Bonjour (mDNS). It works on one network segment.

- Charmling's pane must be open once, or the feature ticked on: the Mac
  only advertises while **Connect to Home Assistant** is on.
- Home Assistant in Docker needs `network_mode: host` for mDNS; the
  Home Assistant OS and Supervised installs have it. Without host
  networking, add the Mac by hand: **Add integration → Charmling**, the
  Mac's address, and the port from the pane.
- A guest Wi-Fi, a VLAN, or "client isolation" on the router blocks
  mDNS between the Mac and Home Assistant; adding by address works as
  long as they can reach each other at all.
- macOS asked about **Local Network** once; declining it stops the Mac
  from *finding* Home Assistant (the token path) but not from being
  found. Adding by address always works.

## "That code was not accepted"

- The code is good for ten minutes from when the pane opened; reopen the
  pane for a fresh one.
- Ten wrong tries burn it; the pane shows a new one within two seconds.
- The pane shows "paired" and no code: the Mac is already paired with a
  Home Assistant. Press **Unpair** there first, or delete the device in
  the other Home Assistant.

## "Could not reach Charmling on the Mac"

Home Assistant cannot open a connection to the Mac's port.

- Is Charmling running, with the feature on? The pane says "waiting to be
  paired" or "paired with…".
- Same network? `curl http://<mac-ip>:41417/id` from anywhere on the LAN
  should print the Mac's id and name.
- The macOS firewall in stealth mode or "block all incoming" blocks the
  listener; allow Charmling in System Settings → Network → Firewall.
- The port: 41417 unless taken, in which case the pane shows the one in
  use and discovery carries it.

## Everything is "unavailable"

The Mac has not been heard from for ninety seconds. The Mac sends a
heartbeat every thirty, so: the Mac is asleep, the app quit, the network
dropped, or Home Assistant's address changed.

- The pane's status line says what the Mac sees: "paired with Home
  Assistant at 192.168.1.5" is good; "cannot reach Home Assistant at …"
  is the Mac failing to push.
- The Mac pushes to the webhook URL it was given at pairing. If Home
  Assistant moved (new IP, new port, a reverse proxy, HTTPS), pair again:
  delete the device in Home Assistant and add it; the URL is refreshed.
- HTTPS with a self-signed certificate: the Mac refuses it. Set an
  `http://` internal URL in Settings → System → Network; the webhook URL
  follows the internal URL.
- Press **Test on air (5 s)** in the pane and watch `on_air`: if it flips,
  the path is fine and the Mac was simply asleep.

## One entity is "unknown"

The Mac has never sent that key. Its group is off in the pane: the app in
front and the score are off from the start; tick them if you want them.
`next_meeting_in` is unknown when there is no meeting in eight hours or
Meeting Radar was never granted calendar access.

## "No longer accepts this pairing"

The Mac was unpaired (the pane's button), or Charmling was reinstalled
and lost its Keychain, or another Home Assistant paired with it. A
re-pair flow is waiting under Settings → Devices & services; type the new
code from the pane. The device and its entities are kept.

## The Mac moved to a new address

Discovery usually tells Home Assistant the new address by itself. If not,
open the device page → ⋮ → **Reconfigure** and type it. The pairing is
kept when the Mac still accepts it.

## The lamp is late

Nothing here polls, so a change should show in Home Assistant within a
second. If it takes longer, the Mac is in low-power mode (the tick still
runs once a second) or Wi-Fi is asleep; a wake sends everything again.

## The recorder is filling up

`idle_seconds` and `last_seen` are disabled by default for this reason.
If you enabled them, consider excluding them from the recorder instead.

## Logs

In `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.charmling: debug
```

Then Settings → System → Logs. Diagnostics (device page → ⋮ → Download
diagnostics) has the last states and the last event, with the secret
redacted; attach it to an issue.

## Reporting a bug

https://github.com/macguy81/charmling-ha/issues, with the diagnostics
file, the Home Assistant version, and what the pane's status line says.
