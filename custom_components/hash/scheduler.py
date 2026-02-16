"""Schedule generation logic for HASH."""

from __future__ import annotations

import datetime


def calculate_next_due(
    last_cleaned: datetime.datetime,
    interval_days: int,
    prefer_weekends: bool = True,
) -> datetime.date:
    """Calculate the next due date for a chore.

    If prefer_weekends is True and the raw due date falls on a weekday,
    shift to the nearest upcoming Saturday — but only if the shift is <= 2 days.
    """
    raw_due = (last_cleaned + datetime.timedelta(days=interval_days)).date()

    if not prefer_weekends:
        return raw_due

    # If already overdue, keep original date
    today = datetime.date.today()
    if raw_due <= today:
        return raw_due

    weekday = raw_due.weekday()  # 0=Monday ... 6=Sunday
    if weekday < 5:  # Mon-Fri
        # Days until Saturday (5)
        days_to_saturday = 5 - weekday
        if days_to_saturday <= 2:
            return raw_due + datetime.timedelta(days=days_to_saturday)

    return raw_due


def get_effective_assignee(
    chore_config: dict,
    runtime_data: dict,
    persons: list[str],
    vacation_list: list[str],
) -> str | None:
    """Determine the effective assignee for a chore.

    Args:
        chore_config: Chore configuration dict with optional assigned_person.
        runtime_data: Runtime data dict with rotation_index.
        persons: List of all person entity_ids.
        vacation_list: List of person entity_ids currently on vacation.

    Returns:
        The entity_id of the assigned person, or None if no one is available.

    """
    active_persons = [p for p in persons if p not in vacation_list]
    if not active_persons:
        return None

    assigned = chore_config.get("assigned_person")

    if assigned:
        # Pinned assignment
        if assigned not in vacation_list:
            return assigned
        # Pinned person is on vacation — redistribute via round-robin
        rotation_index = runtime_data.get("rotation_index", 0)
        return active_persons[rotation_index % len(active_persons)]

    # Rotating assignment
    if not active_persons:
        return None
    rotation_index = runtime_data.get("rotation_index", 0)
    return active_persons[rotation_index % len(active_persons)]
