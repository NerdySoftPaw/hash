# HASH — Home Assistant Sweeping Hub

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![Validate](https://github.com/NerdySoftPaw/hash/actions/workflows/validate.yml/badge.svg)](https://github.com/NerdySoftPaw/hash/actions/workflows/validate.yml)

A custom Home Assistant integration that manages cleaning chores as real HA entities with time-based cleanliness decay, person assignment (fixed or rotating), automatic schedule generation with calendar integration, and vacation mode.

---

## Features

- **Cleanliness sensors** — each chore is a sensor (0–100%) that decays linearly over time
- **Status levels** — Great (>=75%), Fine (>=50%), Dirty (>=25%), Urgent (<25%) with dynamic icons
- **Calendar integration** — shared "HASH Cleaning Schedule" calendar plus one calendar per person
- **Weekend weighting** — due dates that fall on weekdays shift to the nearest Saturday (if <= 2 days away)
- **Person assignment** — pin a chore to a specific person, or let it rotate automatically
- **Vacation mode** — skip persons on vacation in rotation; their pinned chores get redistributed
- **Global pause** — stop generating calendar events while decay and sensors keep running
- **Persistent state** — last cleaned times and rotation indices survive HA restarts
- **Fully configurable via UI** — no YAML needed; everything is managed through the options flow
- **Multilingual** — English, German, French, Dutch

---

## Installation

### HACS (recommended)

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner, then **Custom repositories**
3. Add the repository URL and select **Integration** as the category
4. Click **Install**
5. Restart Home Assistant

### Manual

Copy the `custom_components/hash` folder into your Home Assistant `config/custom_components/` directory and restart.

---

## Setup

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **HASH** and confirm
3. Click **Configure** on the HASH integration card to add chores

---

## Configuration

All configuration happens through the UI options flow. Click **Configure** on the HASH integration card.

### Adding a chore

Select **Add Chore** and fill in:

| Field | Description |
|-------|-------------|
| **Chore Name** | Display name (e.g. "Vacuum Living Room") |
| **Room** | Optional room label for organization |
| **Cleaning Interval** | How often it should be done (preset or custom) |
| **Assigned Person** | Pin to a specific `person.*` entity, or leave empty for rotating assignment |

#### Interval presets

| Preset | Days |
|--------|------|
| 1 Week | 7 |
| 2 Weeks | 14 |
| 3 Weeks | 21 |
| 4 Weeks | 28 |
| 3 Months | 90 |
| 6 Months | 180 |
| 1 Year | 365 |
| Custom | any number of days (1–730) |

### Editing / removing chores

Select **Edit Chore** or **Remove Chore** from the options menu.

### Vacation & pause

Select **Manage Vacation & Pause**:

- **Persons on Vacation** — multi-select persons to exclude from rotation. Their pinned chores are redistributed to remaining active persons.
- **Global Pause** — stops calendar event generation. Sensors still decay and update.

---

## Entities

### Sensors

One sensor per chore: `sensor.hash_cleaning_hub_<chore_name>`

| Property | Description |
|----------|-------------|
| **State** | Cleanliness percentage (0–100%) |
| **Unit** | `%` |
| **Icon** | Changes based on status (check-circle, progress-check, alert-circle, alert-octagon) |

**Attributes:**

| Attribute | Example |
|-----------|---------|
| `chore_id` | `a1b2c3d4-...` |
| `last_cleaned` | `2025-01-15T10:30:00+00:00` |
| `days_since_cleaning` | `3.5` |
| `status` | `Great` / `Fine` / `Dirty` / `Urgent` |
| `room` | `Living Room` |
| `interval_days` | `14` |
| `interval_display` | `every 2 weeks` |
| `assigned_to` | `person.alice` |
| `next_due` | `2025-01-29` |

### Calendars

- **HASH Cleaning Schedule** — shows all chores' next due dates as all-day events
- **HASH - {Person Name}** — one per person, filtered to their assigned chores

Calendar events include the chore name as summary and room + assigned person in the description.

---

## Services

### `hash.complete_chore`

Mark a chore as completed. Resets the timer to now, advances the rotation index, and records who completed it.

```yaml
service: hash.complete_chore
data:
  chore_id: "a1b2c3d4-..."
```

### `hash.reset_chore`

Reset a chore's timer without advancing the rotation. Useful for automation triggers (e.g. robot vacuum finished).

```yaml
service: hash.reset_chore
data:
  chore_id: "a1b2c3d4-..."
```

### `hash.set_vacation`

Toggle vacation mode for a person.

```yaml
service: hash.set_vacation
data:
  person_entity_id: person.alice
  vacation: true
```

### `hash.set_global_pause`

Pause or resume schedule generation globally. Sensors continue to decay.

```yaml
service: hash.set_global_pause
data:
  paused: true
```

---

## How it works

### Decay calculation

Cleanliness decays linearly from 100% to 0% over the configured interval:

```
cleanliness = max(0, 100 - (elapsed_hours / (interval_days * 24)) * 100)
```

The coordinator recalculates every 15 minutes.

### Weekend weighting

When a chore's next due date falls on a weekday (Mon–Fri), it shifts to the nearest upcoming Saturday — but only if the shift is 2 days or less. This means:

- Thursday/Friday due dates move to Saturday
- Monday–Wednesday stay as-is (Saturday is too far)
- Overdue chores always keep their original date

### Person rotation

When no person is pinned to a chore, assignment rotates through all active (non-vacation) persons in round-robin order. The rotation index is persisted and advances on each `complete_chore` call.

When a pinned person is on vacation, their chores are temporarily redistributed to remaining active persons using the same round-robin mechanism.

---

## Automation examples

### Reset chore when robot vacuum finishes a zone

```yaml
automation:
  - alias: "Reset vacuum chore when Roborock finishes living room"
    trigger:
      - platform: state
        entity_id: vacuum.roborock
        from: "cleaning"
        to: "returning"
    action:
      - service: hash.reset_chore
        data:
          chore_id: "your-living-room-vacuum-chore-id"
```

### Send notification when a chore becomes urgent

```yaml
automation:
  - alias: "Notify when chore is urgent"
    trigger:
      - platform: numeric_state
        entity_id: sensor.hash_cleaning_hub_vacuum_living_room
        below: 25
    action:
      - service: notify.mobile_app
        data:
          title: "Cleaning needed!"
          message: >
            {{ state_attr('sensor.hash_cleaning_hub_vacuum_living_room', 'room') }}
            needs cleaning ({{ states('sensor.hash_cleaning_hub_vacuum_living_room') }}% clean)
```

### Auto-complete chore via NFC tag

```yaml
automation:
  - alias: "Complete chore via NFC tag"
    trigger:
      - platform: tag
        tag_id: "your-nfc-tag-id"
    action:
      - service: hash.complete_chore
        data:
          chore_id: "your-chore-id"
```

---

## Finding the chore ID

The `chore_id` (a UUID) is shown in each sensor's attributes. You can find it in:

1. **Developer Tools > States** — search for `sensor.hash` and expand the attributes
2. **Entity card** — the `chore_id` attribute is listed under the sensor details

---

## Development

### Prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
```

### Run tests

```bash
pytest tests/ -v
```

### Lint and format

```bash
ruff check custom_components/hash tests
ruff format custom_components/hash tests
```

### Project structure

```
custom_components/hash/
├── __init__.py          # Setup, service registration, lifecycle
├── const.py             # Constants, thresholds, interval presets
├── coordinator.py       # DataUpdateCoordinator, decay, Store persistence
├── config_flow.py       # ConfigFlow + OptionsFlow (chores, vacation)
├── scheduler.py         # Schedule generation (weekend weighting, assignee logic)
├── sensor.py            # Cleanliness sensor per chore
├── calendar.py          # Shared + per-person calendar entities
├── services.yaml        # Service definitions
├── strings.json         # UI strings (base)
├── manifest.json        # Integration metadata
├── icons.json           # Service icons
└── translations/
    ├── en.json           # English
    ├── de.json           # German
    ├── fr.json           # French
    └── nl.json           # Dutch

tests/
├── conftest.py          # Shared fixtures
├── test_scheduler.py    # Weekend weighting, assignee logic
├── test_coordinator.py  # Decay, status, completion, rotation, pause
├── test_config_flow.py  # Config + options flow steps
├── test_init.py         # Setup/unload, all 4 services
├── test_sensor.py       # Sensor creation and attributes
└── test_calendar.py     # Event building and calendar entities
```

---

## License

MIT
