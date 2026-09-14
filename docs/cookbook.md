# The cookbook

Everything the Mac tells the house, and everything the house can do with
it, as automations you can paste. Entity ids are for a Mac called "Abi's
MacBook Pro"; change the prefix to yours. All of these use the current
automation syntax (`triggers` / `conditions` / `actions`); Home Assistant
accepts the older `trigger:` spelling too.

The Mac's side of each is explained in [entities](entities.md),
[events](events.md) and [actions](actions.md).

---

## Calls

### The on-air lamp

The one everyone builds first. A lamp outside the office goes red within a
second of the microphone opening, whatever window is in front, and stays
red while a muted Zoom keeps the mic open.

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
      brightness_pct: "{{ 100 if trigger.to_state.state == 'on' else 30 }}"
```

Off entirely when nobody is at the desk:

```yaml
alias: Office door lamp, off when the office is empty
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_at_the_desk
    to: "off"
    for: "00:10:00"
actions:
  - action: light.turn_off
    target: {entity_id: light.office_door}
```

### Camera on: the sign, and the blinds

A camera is stronger than a mic: people can see the room. Close the blinds
behind you and light the sign.

```yaml
alias: Camera on
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_camera
    to: "on"
actions:
  - action: cover.close_cover
    target: {entity_id: cover.office_blinds}
  - action: switch.turn_on
    target: {entity_id: switch.on_air_sign}
```

### Everyone else's phones on silent during a call

```yaml
alias: Household quiet during calls
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_on_air
    to: "on"
actions:
  - action: media_player.volume_set
    target: {entity_id: media_player.kitchen}
    data: {volume_level: 0.15}
  - action: notify.family
    data: {message: "Abi is on a call"}
```

### The doorbell during a call goes to the dog, not the speaker

While on air the house should not chime; the dog carries it instead.

```yaml
alias: Doorbell
triggers:
  - trigger: state
    entity_id: binary_sensor.front_door_button
    to: "on"
actions:
  - if:
      - condition: state
        entity_id: binary_sensor.abi_s_macbook_pro_on_air
        state: "on"
    then:
      - action: charmling.say
        data: {message: "🔔 door", category: alert, sound: false}
    else:
      - action: media_player.play_media
        target: {entity_id: media_player.hall}
        data: {media_content_id: chime.mp3, media_content_type: music}
```

### Presenting: everything else stays dark

```yaml
alias: Presenting
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_presenting
actions:
  - action: "{{ 'switch.turn_off' if trigger.to_state.state == 'on' else 'switch.turn_on' }}"
    target: {entity_id: switch.robot_vacuum_schedule}
```

### Count the calls

A history stats sensor of `on_air` gives hours on calls per day, for the
dashboard that tells you why the week felt long.

```yaml
sensor:
  - platform: history_stats
    name: Hours on calls today
    entity_id: binary_sensor.abi_s_macbook_pro_on_air
    state: "on"
    type: time
    start: "{{ today_at('00:00') }}"
    end: "{{ now() }}"
```

---

## Focus

### The focus scene

Focus started: the room dims, the playlist starts, the phone goes quiet.
The break brings it all back.

```yaml
alias: Focus scene
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: focus_started}
actions:
  - action: scene.turn_on
    target: {entity_id: scene.office_focus}
  - action: media_player.play_media
    target: {entity_id: media_player.office}
    data: {media_content_id: "spotify:playlist:lofi", media_content_type: playlist}
  - action: notify.mobile_app_abis_iphone
    data:
      message: "command_dnd"
      data: {command: "on"}
---
alias: Break
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: break}
  - trigger: event
    event_type: charmling_event
    event_data: {type: focus_ended}
actions:
  - action: scene.turn_on
    target: {entity_id: scene.office_day}
  - action: media_player.media_pause
    target: {entity_id: media_player.office}
```

### Start a focus from the house

A button by the door, a voice assistant, or a schedule:

```yaml
alias: Deep work at nine
triggers:
  - trigger: time
    at: "09:00:00"
conditions:
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_at_the_desk
    state: "on"
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_on_air
    state: "off"
actions:
  - action: charmling.do
    data: {action: focus, minutes: 50}
```

### The last five minutes

A lamp fades up as the session ends, so the end is not a jolt.

```yaml
alias: Focus, last five
triggers:
  - trigger: numeric_state
    entity_id: sensor.abi_s_macbook_pro_focus_remaining
    below: 6
conditions:
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_focus_session
    state: "on"
actions:
  - action: light.turn_on
    target: {entity_id: light.desk_lamp}
    data: {brightness_pct: 100, transition: 300}
```

### The stretch nudge, in the room

The Mac says stretch; the standing desk agrees.

```yaml
alias: Stretch
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: stretch}
actions:
  - action: cover.open_cover          # a standing desk on a cover entity
    target: {entity_id: cover.standing_desk}
```

---

## Presence

### The office knows you are working

`at_the_desk` is a motion sensor that only counts real work: input, not
a cat walking past. Use it where you would use occupancy.

```yaml
alias: Office lights follow the desk
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_at_the_desk
actions:
  - action: "{{ 'light.turn_on' if trigger.to_state.state == 'on' else 'light.turn_off' }}"
    target: {entity_id: light.office}
```

### Away long enough: heating down, monitor off

```yaml
alias: Left the desk for a while
triggers:
  - trigger: numeric_state
    entity_id: sensor.abi_s_macbook_pro_away
    above: 30
actions:
  - action: climate.set_temperature
    target: {entity_id: climate.office}
    data: {temperature: 18}
  - action: switch.turn_off
    target: {entity_id: switch.monitor_plug}
```

Bring it back on `back_at_desk`:

```yaml
alias: Back
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: back_at_desk}
actions:
  - action: climate.set_temperature
    target: {entity_id: climate.office}
    data: {temperature: 21}
  - action: switch.turn_on
    target: {entity_id: switch.monitor_plug}
```

### The screen is locked: the room is not yours right now

Lock class: **off is locked**.

```yaml
alias: Screen locked, lamp off
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_screen
    to: "off"
    for: "00:02:00"
actions:
  - action: light.turn_off
    target: {entity_id: light.desk_lamp}
```

### The Mac is gone: the office is empty

The whole device goes unavailable when the Mac sleeps or the app quits,
within ninety seconds at worst. That is a fine "nobody is here" signal.

```yaml
alias: Office empty
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_at_the_desk
    to: "unavailable"
    for: "00:05:00"
actions:
  - action: scene.turn_on
    target: {entity_id: scene.office_off}
```

### A presence entity for the whole house

Combine the Mac with the phone in a template binary sensor so "Abi is
home and working" is one entity everything else can use.

```yaml
template:
  - binary_sensor:
      - name: Abi working
        state: >
          {{ is_state('person.abi', 'home')
             and is_state('binary_sensor.abi_s_macbook_pro_at_the_desk', 'on') }}
```

---

## Screen

### Cinema

Something full-screen in front, in the evening: lights down.

```yaml
alias: Cinema
triggers:
  - trigger: state
    entity_id: binary_sensor.abi_s_macbook_pro_full_screen
    to: "on"
    for: "00:00:30"
conditions:
  - condition: sun
    after: sunset
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_on_air
    state: "off"
actions:
  - action: light.turn_on
    target: {entity_id: light.living_room}
    data: {brightness_pct: 10, transition: 5}
```

### The kind of work sets the light

Reading warm and low, design bright and neutral, coding whatever you
like. A category, never a title.

```yaml
alias: Light follows the work
triggers:
  - trigger: state
    entity_id: sensor.abi_s_macbook_pro_work_kind
actions:
  - choose:
      - conditions: "{{ trigger.to_state.state == 'reading' }}"
        sequence:
          - action: light.turn_on
            target: {entity_id: light.desk_lamp}
            data: {kelvin: 2700, brightness_pct: 40}
      - conditions: "{{ trigger.to_state.state in ['design', 'coding'] }}"
        sequence:
          - action: light.turn_on
            target: {entity_id: light.desk_lamp}
            data: {kelvin: 4500, brightness_pct: 90}
      - conditions: "{{ trigger.to_state.state == 'media' }}"
        sequence:
          - action: light.turn_on
            target: {entity_id: light.desk_lamp}
            data: {brightness_pct: 15}
```

### Too long in mail

A gentle one: forty minutes of mail in a row, and the dog asks for a walk.

```yaml
alias: Mail is a swamp
triggers:
  - trigger: state
    entity_id: sensor.abi_s_macbook_pro_work_kind
    to: mail
    for: "00:40:00"
actions:
  - action: charmling.say
    data: {message: "forty minutes of mail. walk?", category: done}
```

---

## Calendar

### Five minutes to the meeting

The Mac knows the minutes, never the title. The room gets ready.

```yaml
alias: Meeting soon
triggers:
  - trigger: numeric_state
    entity_id: sensor.abi_s_macbook_pro_next_meeting_in
    below: 6
conditions:
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_at_the_desk
    state: "on"
actions:
  - action: light.turn_on
    target: {entity_id: light.office}
    data: {brightness_pct: 100, kelvin: 4000}
  - action: media_player.media_pause
    target: {entity_id: media_player.office}
```

### A heavy day

Meeting density is light, normal or heavy. On a heavy day the coffee
machine warms up earlier and the office stays warmer.

```yaml
alias: Heavy day
triggers:
  - trigger: time
    at: "07:30:00"
conditions:
  - condition: state
    entity_id: sensor.abi_s_macbook_pro_meeting_density
    state: heavy
actions:
  - action: switch.turn_on
    target: {entity_id: switch.coffee_machine}
```

---

## The house, said by the cord

### Arrivals

Someone comes home: the charm does its ritual, or the dog walks over.

```yaml
alias: Sam is home
triggers:
  - trigger: state
    entity_id: person.sam
    to: home
actions:
  - action: charmling.say
    data: {message: "🐾 Sam's home", category: arrival}
```

### The washing is done

```yaml
alias: Washing done
triggers:
  - trigger: numeric_state
    entity_id: sensor.washer_power
    below: 5
    for: "00:02:00"
actions:
  - action: charmling.say
    data: {message: "🧺 washing's done", category: done}
```

### Ambient: things to find later

A bead on the cord, nothing else. Clicking the bead opens Home Assistant.

```yaml
alias: Open a window
triggers:
  - trigger: numeric_state
    entity_id: sensor.office_co2
    above: 1000
actions:
  - action: charmling.say
    data: {message: "CO₂ is high, open a window", category: ambient}
```

### The parcel

```yaml
alias: Parcel
triggers:
  - trigger: state
    entity_id: binary_sensor.porch_parcel
    to: "on"
actions:
  - action: charmling.say
    data: {message: "📦 parcel on the porch", category: done}
```

### Emergencies cut through everything

Smoke, water, the freezer. The dog barks whether hushed or not, a system
notification appears, the sound plays.

```yaml
alias: Smoke
triggers:
  - trigger: state
    entity_id: binary_sensor.smoke_alarm
    to: "on"
actions:
  - action: charmling.say
    data: {message: "🔥 smoke in the kitchen", category: emergency}
---
alias: Water leak
triggers:
  - trigger: state
    entity_id: binary_sensor.water_leak_basement
    to: "on"
actions:
  - action: charmling.say
    data: {message: "💧 water in the basement", category: emergency}
---
alias: Freezer warm
triggers:
  - trigger: numeric_state
    entity_id: sensor.freezer_temperature
    above: -10
    for: "00:30:00"
actions:
  - action: charmling.say
    data: {message: "🧊 freezer is warming up", category: emergency}
```

### Quiet hours for the house's lines

Nothing but emergencies while on a call:

```yaml
alias: Bin day
triggers:
  - trigger: time
    at: "19:00:00"
conditions:
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_on_air
    state: "off"
actions:
  - action: charmling.say
    data: {message: "🗑️ bins out tonight", category: done}
```

---

## The Garden and the real plants

### The real bonsai waters the one on the cord

```yaml
alias: Bonsai watered
triggers:
  - trigger: numeric_state
    entity_id: sensor.bonsai_moisture
    above: 40
actions:
  - action: charmling.water
    data: {plant: bonsai}
```

### And the other way: the Garden reminds you

If the real sensor has been dry for two days, the charm says so.

```yaml
alias: Bonsai is thirsty
triggers:
  - trigger: numeric_state
    entity_id: sensor.bonsai_moisture
    below: 20
    for: "48:00:00"
actions:
  - action: charmling.say
    data: {message: "🌱 the bonsai is thirsty", category: ambient}
```

---

## The dog and the house

### The woof, on a bulb

```yaml
alias: Woof
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: woof}
actions:
  - action: light.turn_on
    target: {entity_id: light.desk_lamp}
    data: {flash: short}
```

### The nap dims the lamp; waking brings it back

```yaml
alias: Dog naps
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: nap}
actions:
  - action: light.turn_on
    target: {entity_id: light.desk_lamp}
    data: {brightness_pct: 30, transition: 10}
---
alias: Dog wakes
triggers:
  - trigger: event
    event_type: charmling_event
    event_data: {type: wake}
actions:
  - action: light.turn_on
    target: {entity_id: light.desk_lamp}
    data: {brightness_pct: 80, transition: 3}
```

### Hush him when the baby sleeps

```yaml
alias: Baby asleep, dog hushed
triggers:
  - trigger: state
    entity_id: binary_sensor.nursery_sleeping
actions:
  - action: "{{ 'switch.turn_on' if trigger.to_state.state == 'on' else 'switch.turn_off' }}"
    target: {entity_id: switch.abi_s_macbook_pro_hushed}
```

### The evening trick

At six the dog does his trick, and that is your cue.

```yaml
alias: Six o'clock trick
triggers:
  - trigger: time
    at: "18:00:00"
conditions:
  - condition: state
    entity_id: binary_sensor.abi_s_macbook_pro_at_the_desk
    state: "on"
actions:
  - action: charmling.do
    data: {action: trick}
```

### Everyone gets a pat

A button on the wall, or a voice command:

```yaml
alias: Pat the dog
triggers:
  - trigger: state
    entity_id: event.hall_button
actions:
  - action: charmling.do
    data: {action: pat}
```

### Let him out when you leave

Leaving the house: unclip the leash; he roams the desktop while you are
gone, and comes home when you are back.

```yaml
alias: Dog out while away
triggers:
  - trigger: state
    entity_id: person.abi
    from: home
actions:
  - action: charmling.do
    data: {action: unclip}
---
alias: Dog home
triggers:
  - trigger: state
    entity_id: person.abi
    to: home
actions:
  - action: charmling.do
    data: {action: clip}
```

---

## Notifications, without the notification

### Too many banners

The Mac counts notification banners in the last ten minutes (never their
content). Past a dozen, hush the house's own lines for a while.

```yaml
alias: Banner storm
triggers:
  - trigger: numeric_state
    entity_id: sensor.abi_s_macbook_pro_notification_banners_10_min
    above: 12
actions:
  - action: input_boolean.turn_on
    target: {entity_id: input_boolean.quiet_mode}
```

### The basket has files

Something was fetched into the basket: a light on the shelf.

```yaml
alias: Basket
triggers:
  - trigger: numeric_state
    entity_id: sensor.abi_s_macbook_pro_basket
    above: 0
actions:
  - action: light.turn_on
    target: {entity_id: light.shelf}
    data: {color_name: amber}
```

---

## Dashboards

A card that is the whole story of the desk:

```yaml
type: entities
title: Abi's desk
entities:
  - binary_sensor.abi_s_macbook_pro_at_the_desk
  - binary_sensor.abi_s_macbook_pro_on_air
  - binary_sensor.abi_s_macbook_pro_camera
  - binary_sensor.abi_s_macbook_pro_focus_session
  - sensor.abi_s_macbook_pro_focus_remaining
  - sensor.abi_s_macbook_pro_work_kind
  - sensor.abi_s_macbook_pro_next_meeting_in
  - sensor.abi_s_macbook_pro_meeting_density
  - sensor.abi_s_macbook_pro_dog
  - event.abi_s_macbook_pro_moment
```

A conditional card that only shows while on air:

```yaml
type: conditional
conditions:
  - condition: state
    entity: binary_sensor.abi_s_macbook_pro_on_air
    state: "on"
card:
  type: markdown
  content: "🔴 **On air** — Abi is on a call"
```

Long-term statistics on the counts and durations (`away`, `focus_remaining`,
`beads_waiting`, `basket`, `notification_banners_10_min`) work with the
statistics graph card out of the box.

---

## Several Macs

Each Mac is its own device; every entity id carries the Mac's name, and
events carry `device_id`. Target actions with `target: device_id`, and
filter event triggers with it:

```yaml
triggers:
  - trigger: event
    event_type: charmling_event
    event_data:
      type: call_started
      device_id: 1c9a2b3d…
```

A template for "anyone in the house is on a call":

```yaml
template:
  - binary_sensor:
      - name: Someone on a call
        state: >
          {{ states.binary_sensor
             | selectattr('entity_id', 'search', '_on_air$')
             | selectattr('state', 'eq', 'on') | list | count > 0 }}
```
