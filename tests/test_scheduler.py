"""Tests for the scheduler module."""

from __future__ import annotations

import datetime

from custom_components.hash.scheduler import (
    calculate_next_due,
    get_effective_assignee,
)


class TestCalculateNextDue:
    """Tests for calculate_next_due."""

    def test_basic_due_date(self):
        last_cleaned = datetime.datetime(2025, 1, 1, 12, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=False)
        assert result == datetime.date(2025, 1, 15)

    def test_weekend_shift_thursday_to_saturday(self):
        # 2027-01-07 is Thursday, +14 days = 2027-01-21 (Thursday)
        # Saturday is 2 days away → shift to 2027-01-23
        last_cleaned = datetime.datetime(2027, 1, 7, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=True)
        assert result == datetime.date(2027, 1, 23)

    def test_weekend_shift_friday_to_saturday(self):
        # 2027-01-01 is Friday, +14 days = 2027-01-15 (Friday)
        # Saturday is 1 day away → shift to 2027-01-16
        last_cleaned = datetime.datetime(2027, 1, 1, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=True)
        assert result == datetime.date(2027, 1, 16)

    def test_no_shift_when_too_far(self):
        # 2026-12-24 + 14 = 2027-01-07 (Thursday), shift = 2 → OK actually
        # Use Monday: 2027-01-04 is Monday, +14 = 2027-01-18 (Monday)
        # Saturday is 5 days away → too far, keep Monday
        last_cleaned = datetime.datetime(2027, 1, 4, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=True)
        assert result == datetime.date(2027, 1, 18)

    def test_wednesday_no_shift(self):
        # 2027-01-06 is Wednesday, +14 = 2027-01-20 (Wednesday)
        # Saturday is 3 days away → too far
        last_cleaned = datetime.datetime(2027, 1, 6, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=True)
        assert result == datetime.date(2027, 1, 20)

    def test_saturday_stays_saturday(self):
        # 2027-01-02 is Saturday, +14 = 2027-01-16 (Saturday)
        last_cleaned = datetime.datetime(2027, 1, 2, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=True)
        assert result == datetime.date(2027, 1, 16)

    def test_sunday_stays_sunday(self):
        # 2027-01-03 is Sunday, +14 = 2027-01-17 (Sunday)
        last_cleaned = datetime.datetime(2027, 1, 3, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=True)
        assert result == datetime.date(2027, 1, 17)

    def test_overdue_keeps_original_date(self):
        # Very old last_cleaned → due in the past → keep as-is
        last_cleaned = datetime.datetime(2020, 1, 1, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 7, prefer_weekends=True)
        expected = datetime.date(2020, 1, 8)
        assert result == expected

    def test_prefer_weekends_false(self):
        # 2027-01-01 + 14 = 2027-01-15 (Friday), no weekend shift
        last_cleaned = datetime.datetime(2027, 1, 1, 0, 0, 0)
        result = calculate_next_due(last_cleaned, 14, prefer_weekends=False)
        assert result == datetime.date(2027, 1, 15)


class TestGetEffectiveAssignee:
    """Tests for get_effective_assignee."""

    def test_pinned_person_not_on_vacation(self):
        chore = {"assigned_person": "person.alice"}
        runtime = {"rotation_index": 0}
        persons = ["person.alice", "person.bob"]
        vacation = []
        assert (
            get_effective_assignee(chore, runtime, persons, vacation) == "person.alice"
        )

    def test_pinned_person_on_vacation_redistributes(self):
        chore = {"assigned_person": "person.alice"}
        runtime = {"rotation_index": 0}
        persons = ["person.alice", "person.bob", "person.charlie"]
        vacation = ["person.alice"]
        # Active: bob, charlie. rotation_index 0 → bob
        assert get_effective_assignee(chore, runtime, persons, vacation) == "person.bob"

    def test_rotating_assignment(self):
        chore = {"assigned_person": ""}
        runtime = {"rotation_index": 0}
        persons = ["person.alice", "person.bob"]
        vacation = []
        assert (
            get_effective_assignee(chore, runtime, persons, vacation) == "person.alice"
        )

    def test_rotating_wraps_around(self):
        chore = {"assigned_person": ""}
        runtime = {"rotation_index": 3}
        persons = ["person.alice", "person.bob"]
        vacation = []
        # 3 % 2 = 1 → bob
        assert get_effective_assignee(chore, runtime, persons, vacation) == "person.bob"

    def test_rotating_skips_vacation(self):
        chore = {"assigned_person": ""}
        runtime = {"rotation_index": 0}
        persons = ["person.alice", "person.bob", "person.charlie"]
        vacation = ["person.alice"]
        # Active: bob, charlie. index 0 → bob
        assert get_effective_assignee(chore, runtime, persons, vacation) == "person.bob"

    def test_no_persons_returns_none(self):
        chore = {"assigned_person": ""}
        runtime = {"rotation_index": 0}
        assert get_effective_assignee(chore, runtime, [], []) is None

    def test_all_on_vacation_returns_none(self):
        chore = {"assigned_person": ""}
        runtime = {"rotation_index": 0}
        persons = ["person.alice"]
        vacation = ["person.alice"]
        assert get_effective_assignee(chore, runtime, persons, vacation) is None

    def test_no_assigned_person_key(self):
        chore = {}
        runtime = {"rotation_index": 0}
        persons = ["person.alice"]
        vacation = []
        assert (
            get_effective_assignee(chore, runtime, persons, vacation) == "person.alice"
        )
