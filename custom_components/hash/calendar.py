"""Calendar platform for HASH — shared + per-person calendars."""

from __future__ import annotations

import datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ASSIGNED_PERSON, CONF_CHORES, DOMAIN
from .coordinator import HashCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HASH calendar entities from a config entry."""
    coordinator: HashCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[CalendarEntity] = []

    # Shared calendar
    entities.append(HashCalendarEntity(coordinator, entry))

    # Per-person calendars — one for each unique person in chore configs
    persons_seen: set[str] = set()
    for chore in entry.options.get(CONF_CHORES, []):
        person = chore.get(CONF_ASSIGNED_PERSON, "")
        if person:
            persons_seen.add(person)
    # Also include persons that show up as effective assignees
    for chore_data in coordinator.data.values():
        assigned = chore_data.get("assigned_to")
        if assigned:
            persons_seen.add(assigned)

    for person_id in sorted(persons_seen):
        entities.append(HashPersonCalendarEntity(coordinator, entry, person_id))

    async_add_entities(entities)


def _build_events(
    coordinator_data: dict[str, Any],
    start_date: datetime.date,
    end_date: datetime.date,
    person_filter: str | None = None,
) -> list[CalendarEvent]:
    """Build calendar events from coordinator data."""
    events: list[CalendarEvent] = []

    for _chore_id, data in coordinator_data.items():
        next_due_str = data.get("next_due")
        if not next_due_str:
            continue

        next_due = datetime.date.fromisoformat(next_due_str)
        if next_due < start_date or next_due >= end_date:
            continue

        if person_filter and data.get("assigned_to") != person_filter:
            continue

        assignee_display = data.get("assigned_to", "Rotating") or "Rotating"
        # Use friendly name if it looks like an entity_id
        if assignee_display.startswith("person."):
            assignee_display = (
                assignee_display.replace("person.", "").replace("_", " ").title()
            )

        room = data.get("room", "")
        description_parts = []
        if room:
            description_parts.append(f"Room: {room}")
        description_parts.append(f"Assigned: {assignee_display}")

        events.append(
            CalendarEvent(
                summary=data["name"],
                start=next_due,
                end=next_due + datetime.timedelta(days=1),
                description="\n".join(description_parts),
            )
        )

    return events


class HashCalendarEntity(CoordinatorEntity[HashCoordinator], CalendarEntity):
    """Shared calendar showing all chores."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HashCoordinator, entry: ConfigEntry) -> None:
        """Initialize the shared calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_name = "HASH Cleaning Schedule"
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="HASH Cleaning Hub",
            manufacturer="HASH",
            model="Sweeping Hub",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        today = datetime.date.today()
        far_future = today + datetime.timedelta(days=365)
        events = _build_events(self.coordinator.data, today, far_future)
        if not events:
            return None
        events.sort(key=lambda e: e.start)
        return events[0]

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return events in a date range."""
        return _build_events(
            self.coordinator.data,
            start_date.date(),
            end_date.date(),
        )


class HashPersonCalendarEntity(CoordinatorEntity[HashCoordinator], CalendarEntity):
    """Per-person calendar showing only their assigned chores."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HashCoordinator,
        entry: ConfigEntry,
        person_entity_id: str,
    ) -> None:
        """Initialize a per-person calendar."""
        super().__init__(coordinator)
        self._person_entity_id = person_entity_id
        safe_id = person_entity_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_calendar_{safe_id}"
        # Friendly name from entity_id
        friendly = person_entity_id.replace("person.", "").replace("_", " ").title()
        self._attr_name = f"HASH - {friendly}"
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="HASH Cleaning Hub",
            manufacturer="HASH",
            model="Sweeping Hub",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event for this person."""
        today = datetime.date.today()
        far_future = today + datetime.timedelta(days=365)
        events = _build_events(
            self.coordinator.data,
            today,
            far_future,
            person_filter=self._person_entity_id,
        )
        if not events:
            return None
        events.sort(key=lambda e: e.start)
        return events[0]

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return events in a date range for this person."""
        return _build_events(
            self.coordinator.data,
            start_date.date(),
            end_date.date(),
            person_filter=self._person_entity_id,
        )
