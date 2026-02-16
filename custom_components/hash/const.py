"""Constants for the HASH integration."""

from __future__ import annotations

DOMAIN = "hash"
STORAGE_KEY = "hash.chore_data"
STORAGE_VERSION = 1

PLATFORMS = ["sensor", "calendar"]

# Decay thresholds
THRESHOLD_GREAT = 75
THRESHOLD_FINE = 50
THRESHOLD_DIRTY = 25

STATUS_GREAT = "Great"
STATUS_FINE = "Fine"
STATUS_DIRTY = "Dirty"
STATUS_URGENT = "Urgent"

# Interval presets: label -> days
INTERVAL_PRESETS: dict[str, int] = {
    "1_week": 7,
    "2_weeks": 14,
    "3_weeks": 21,
    "4_weeks": 28,
    "3_months": 90,
    "6_months": 180,
    "1_year": 365,
}

INTERVAL_LABELS: dict[str, str] = {
    "1_week": "1 Week",
    "2_weeks": "2 Weeks",
    "3_weeks": "3 Weeks",
    "4_weeks": "4 Weeks",
    "3_months": "3 Months",
    "6_months": "6 Months",
    "1_year": "1 Year",
    "custom": "Custom",
}

# Display labels for interval days
INTERVAL_DISPLAY: dict[int, str] = {
    7: "every 1 week",
    14: "every 2 weeks",
    21: "every 3 weeks",
    28: "every 4 weeks",
    90: "every 3 months",
    180: "every 6 months",
    365: "every 1 year",
}

# Config keys
CONF_CHORES = "chores"
CONF_CHORE_ID = "chore_id"
CONF_CHORE_NAME = "name"
CONF_ROOM = "room"
CONF_INTERVAL = "interval"
CONF_INTERVAL_PRESET = "interval_preset"
CONF_ASSIGNED_PERSON = "assigned_person"
CONF_VACATION_PERSONS = "vacation_persons"
CONF_GLOBAL_PAUSE = "global_pause"

# Service names
SERVICE_COMPLETE_CHORE = "complete_chore"
SERVICE_RESET_CHORE = "reset_chore"
SERVICE_SET_VACATION = "set_vacation"
SERVICE_SET_GLOBAL_PAUSE = "set_global_pause"

# Coordinator
UPDATE_INTERVAL_MINUTES = 15

# Icons by status
ICON_GREAT = "mdi:check-circle"
ICON_FINE = "mdi:progress-check"
ICON_DIRTY = "mdi:alert-circle"
ICON_URGENT = "mdi:alert-octagon"
