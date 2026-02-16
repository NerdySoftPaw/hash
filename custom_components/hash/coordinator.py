"""DataUpdateCoordinator for HASH."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHORE_ID,
    CONF_CHORE_NAME,
    CONF_CHORES,
    CONF_GLOBAL_PAUSE,
    CONF_INTERVAL,
    CONF_ROOM,
    CONF_VACATION_PERSONS,
    DOMAIN,
    INTERVAL_DISPLAY,
    STATUS_DIRTY,
    STATUS_FINE,
    STATUS_GREAT,
    STATUS_URGENT,
    STORAGE_KEY,
    STORAGE_VERSION,
    THRESHOLD_DIRTY,
    THRESHOLD_FINE,
    THRESHOLD_GREAT,
    UPDATE_INTERVAL_MINUTES,
)
from .scheduler import calculate_next_due, get_effective_assignee

_LOGGER = logging.getLogger(__name__)


def calculate_cleanliness(last_cleaned: datetime.datetime, interval_days: int) -> float:
    """Calculate cleanliness percentage based on elapsed time."""
    now = dt_util.utcnow()
    elapsed = now - last_cleaned
    elapsed_hours = elapsed.total_seconds() / 3600
    total_hours = interval_days * 24
    cleanliness = max(0.0, 100.0 - (elapsed_hours / total_hours) * 100.0)
    return round(cleanliness, 1)


def get_status(cleanliness: float) -> str:
    """Get status label from cleanliness percentage."""
    if cleanliness >= THRESHOLD_GREAT:
        return STATUS_GREAT
    if cleanliness >= THRESHOLD_FINE:
        return STATUS_FINE
    if cleanliness >= THRESHOLD_DIRTY:
        return STATUS_DIRTY
    return STATUS_URGENT


def get_interval_display(interval_days: int) -> str:
    """Get a human-readable display string for an interval."""
    if interval_days in INTERVAL_DISPLAY:
        return INTERVAL_DISPLAY[interval_days]
    return f"every {interval_days} days"


def _get_all_persons(hass: HomeAssistant) -> list[str]:
    """Get all person entity_ids from HA."""
    return [state.entity_id for state in hass.states.async_all("person")]


class HashCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for HASH chore data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=datetime.timedelta(minutes=UPDATE_INTERVAL_MINUTES),
            config_entry=entry,
        )
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._runtime_data: dict[str, dict[str, Any]] = {}

    async def async_load_store(self) -> None:
        """Load persisted data from store."""
        stored = await self._store.async_load()
        if stored and "chores" in stored:
            self._runtime_data = stored["chores"]
        else:
            self._runtime_data = {}

    async def _async_save_store(self) -> None:
        """Persist runtime data to store."""
        await self._store.async_save({"chores": self._runtime_data})

    def _ensure_runtime(self, chore_id: str) -> dict[str, Any]:
        """Ensure runtime data exists for a chore, initializing if needed."""
        if chore_id not in self._runtime_data:
            self._runtime_data[chore_id] = {
                "last_cleaned": dt_util.utcnow().isoformat(),
                "rotation_index": 0,
                "completed_by_history": [],
            }
        return self._runtime_data[chore_id]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and compute chore data."""
        options = self.config_entry.options
        chores = options.get(CONF_CHORES, [])
        vacation_list = options.get(CONF_VACATION_PERSONS, [])
        global_pause = options.get(CONF_GLOBAL_PAUSE, False)
        persons = _get_all_persons(self.hass)

        result: dict[str, Any] = {}

        for chore in chores:
            chore_id = chore[CONF_CHORE_ID]
            runtime = self._ensure_runtime(chore_id)

            last_cleaned_str = runtime["last_cleaned"]
            last_cleaned = datetime.datetime.fromisoformat(last_cleaned_str)
            if last_cleaned.tzinfo is None:
                last_cleaned = last_cleaned.replace(tzinfo=datetime.UTC)

            interval_days = chore[CONF_INTERVAL]
            cleanliness = calculate_cleanliness(last_cleaned, interval_days)
            status = get_status(cleanliness)

            now = dt_util.utcnow()
            days_since = (now - last_cleaned).total_seconds() / 86400

            effective_assignee = get_effective_assignee(
                chore, runtime, persons, vacation_list
            )

            if global_pause:
                next_due = None
            else:
                next_due = calculate_next_due(last_cleaned, interval_days)

            result[chore_id] = {
                "name": chore[CONF_CHORE_NAME],
                "room": chore.get(CONF_ROOM, ""),
                "interval_days": interval_days,
                "interval_display": get_interval_display(interval_days),
                "cleanliness": cleanliness,
                "status": status,
                "days_since": round(days_since, 1),
                "last_cleaned": last_cleaned.isoformat(),
                "next_due": next_due.isoformat() if next_due else None,
                "assigned_to": effective_assignee,
                "chore_id": chore_id,
            }

        return result

    async def async_complete_chore(self, chore_id: str) -> None:
        """Mark a chore as completed: reset timer, advance rotation."""
        runtime = self._ensure_runtime(chore_id)
        now = dt_util.utcnow()

        # Determine who completed it
        options = self.config_entry.options
        vacation_list = options.get(CONF_VACATION_PERSONS, [])
        persons = _get_all_persons(self.hass)
        chore_config = self._find_chore_config(chore_id)

        if chore_config:
            assignee = get_effective_assignee(
                chore_config, runtime, persons, vacation_list
            )
        else:
            assignee = None

        runtime["last_cleaned"] = now.isoformat()
        runtime["rotation_index"] = runtime.get("rotation_index", 0) + 1

        if assignee:
            history = runtime.get("completed_by_history", [])
            history.append({"person": assignee, "timestamp": now.isoformat()})
            runtime["completed_by_history"] = history

        await self._async_save_store()
        await self.async_request_refresh()

    async def async_reset_chore(self, chore_id: str) -> None:
        """Reset a chore's timer without advancing rotation."""
        runtime = self._ensure_runtime(chore_id)
        runtime["last_cleaned"] = dt_util.utcnow().isoformat()
        await self._async_save_store()
        await self.async_request_refresh()

    def _find_chore_config(self, chore_id: str) -> dict | None:
        """Find a chore config by ID."""
        chores = self.config_entry.options.get(CONF_CHORES, [])
        for chore in chores:
            if chore[CONF_CHORE_ID] == chore_id:
                return chore
        return None

    async def async_cleanup_removed_chores(self) -> None:
        """Remove runtime data for chores that no longer exist in config."""
        chores = self.config_entry.options.get(CONF_CHORES, [])
        active_ids = {c[CONF_CHORE_ID] for c in chores}
        removed = [cid for cid in self._runtime_data if cid not in active_ids]
        for cid in removed:
            del self._runtime_data[cid]
        if removed:
            await self._async_save_store()
