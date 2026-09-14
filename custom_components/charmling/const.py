"""Constants for the Charmling integration."""

from __future__ import annotations

DOMAIN = "charmling"
MANUFACTURER = "Charmling"
MODEL = "Mac"

CONF_NODE = "node"
CONF_SECRET = "secret"
CONF_WEBHOOK_ID = "webhook_id"
CONF_MAC_NAME = "mac_name"
CONF_VERSION = "version"

DEFAULT_PORT = 41417

EVENT_NAME = "charmling_event"
SIGNAL_UPDATE = "charmling_update_{}"

# the Mac heartbeats every 30 s; a minute and a half of silence is "gone"
STALE_AFTER = 90

# what the Mac fires as moment events; the event entity lists them
EVENT_TYPES = [
    "call_started", "call_ended",
    "focus_started", "focus_ended", "break", "stretch",
    "ritual", "bead",
    "bark", "woof", "trick", "nap", "wake", "delivered",
    "back_at_desk", "left_desk",
]

CATEGORIES = ["arrival", "alert", "done", "ambient", "emergency"]
PLANTS = ["bonsai", "dragon"]
ACTIONS = ["call", "trick", "speak", "pat", "hush", "unhush", "mute", "unmute",
           "focus", "stop_focus", "unclip", "clip", "nap", "wake"]
