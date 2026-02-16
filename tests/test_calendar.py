"""Tests for the calendar platform."""

from __future__ import annotations

import datetime

import pytest
from homeassistant.core import HomeAssistant

from custom_components.hash.calendar import _build_events


class TestBuildEvents:
    """Tests for the _build_events helper."""

    def test_event_in_range(self):
        data = {
            "chore1": {
                "name": "Vacuum",
                "room": "Living Room",
                "assigned_to": "person.alice",
                "next_due": "2025-02-01",
            }
        }
        events = _build_events(
            data,
            datetime.date(2025, 1, 1),
            datetime.date(2025, 3, 1),
        )
        assert len(events) == 1
        assert events[0].summary == "Vacuum"
        assert events[0].start == datetime.date(2025, 2, 1)
        assert events[0].end == datetime.date(2025, 2, 2)

    def test_event_out_of_range(self):
        data = {
            "chore1": {
                "name": "Vacuum",
                "room": "Living Room",
                "assigned_to": "person.alice",
                "next_due": "2025-06-01",
            }
        }
        events = _build_events(
            data,
            datetime.date(2025, 1, 1),
            datetime.date(2025, 3, 1),
        )
        assert len(events) == 0

    def test_event_no_next_due(self):
        data = {
            "chore1": {
                "name": "Vacuum",
                "room": "Living Room",
                "assigned_to": None,
                "next_due": None,
            }
        }
        events = _build_events(
            data,
            datetime.date(2025, 1, 1),
            datetime.date(2025, 12, 31),
        )
        assert len(events) == 0

    def test_person_filter(self):
        data = {
            "chore1": {
                "name": "Vacuum",
                "room": "Living Room",
                "assigned_to": "person.alice",
                "next_due": "2025-02-01",
            },
            "chore2": {
                "name": "Mop",
                "room": "Kitchen",
                "assigned_to": "person.bob",
                "next_due": "2025-02-01",
            },
        }
        events = _build_events(
            data,
            datetime.date(2025, 1, 1),
            datetime.date(2025, 3, 1),
            person_filter="person.alice",
        )
        assert len(events) == 1
        assert events[0].summary == "Vacuum"

    def test_friendly_name_in_description(self):
        data = {
            "chore1": {
                "name": "Vacuum",
                "room": "Living Room",
                "assigned_to": "person.alice",
                "next_due": "2025-02-01",
            }
        }
        events = _build_events(
            data,
            datetime.date(2025, 1, 1),
            datetime.date(2025, 3, 1),
        )
        assert "Alice" in events[0].description

    def test_rotating_label_when_no_assignee(self):
        data = {
            "chore1": {
                "name": "Vacuum",
                "room": "",
                "assigned_to": None,
                "next_due": "2025-02-01",
            }
        }
        events = _build_events(
            data,
            datetime.date(2025, 1, 1),
            datetime.date(2025, 3, 1),
        )
        assert "Rotating" in events[0].description


@pytest.mark.usefixtures("bypass_store")
async def test_calendar_entities_created(
    hass: HomeAssistant, mock_config_entry_two_chores
):
    mock_config_entry_two_chores.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry_two_chores.entry_id)
    await hass.async_block_till_done()

    all_states = hass.states.async_all("calendar")
    # Should have at least the shared calendar
    hash_calendars = [s for s in all_states if "hash" in s.entity_id]
    assert len(hash_calendars) >= 1
