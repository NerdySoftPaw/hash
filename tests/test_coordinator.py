"""Tests for the coordinator module."""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.hash.const import CONF_GLOBAL_PAUSE
from custom_components.hash.coordinator import (
    HashCoordinator,
    calculate_cleanliness,
    get_interval_display,
    get_status,
)

from .conftest import MOCK_CHORE_ID


class TestCalculateCleanliness:
    """Tests for calculate_cleanliness."""

    def test_just_cleaned(self):
        now = datetime.datetime(2025, 1, 15, 12, 0, 0, tzinfo=datetime.UTC)
        with patch(
            "custom_components.hash.coordinator.dt_util.utcnow", return_value=now
        ):
            result = calculate_cleanliness(now, 14)
        assert result == 100.0

    def test_half_elapsed(self):
        now = datetime.datetime(2025, 1, 15, 12, 0, 0, tzinfo=datetime.UTC)
        last = now - datetime.timedelta(days=7)
        with patch(
            "custom_components.hash.coordinator.dt_util.utcnow", return_value=now
        ):
            result = calculate_cleanliness(last, 14)
        assert result == 50.0

    def test_fully_elapsed(self):
        now = datetime.datetime(2025, 1, 15, 12, 0, 0, tzinfo=datetime.UTC)
        last = now - datetime.timedelta(days=14)
        with patch(
            "custom_components.hash.coordinator.dt_util.utcnow", return_value=now
        ):
            result = calculate_cleanliness(last, 14)
        assert result == 0.0

    def test_over_elapsed_clamps_to_zero(self):
        now = datetime.datetime(2025, 1, 15, 12, 0, 0, tzinfo=datetime.UTC)
        last = now - datetime.timedelta(days=30)
        with patch(
            "custom_components.hash.coordinator.dt_util.utcnow", return_value=now
        ):
            result = calculate_cleanliness(last, 14)
        assert result == 0.0


class TestGetStatus:
    """Tests for get_status."""

    def test_great(self):
        assert get_status(100.0) == "Great"
        assert get_status(75.0) == "Great"

    def test_fine(self):
        assert get_status(74.9) == "Fine"
        assert get_status(50.0) == "Fine"

    def test_dirty(self):
        assert get_status(49.9) == "Dirty"
        assert get_status(25.0) == "Dirty"

    def test_urgent(self):
        assert get_status(24.9) == "Urgent"
        assert get_status(0.0) == "Urgent"


class TestGetIntervalDisplay:
    """Tests for get_interval_display."""

    def test_known_intervals(self):
        assert get_interval_display(7) == "every 1 week"
        assert get_interval_display(14) == "every 2 weeks"
        assert get_interval_display(90) == "every 3 months"
        assert get_interval_display(365) == "every 1 year"

    def test_custom_interval(self):
        assert get_interval_display(10) == "every 10 days"
        assert get_interval_display(45) == "every 45 days"


class TestCoordinator:
    """Tests for HashCoordinator."""

    @pytest.mark.usefixtures("bypass_store")
    async def test_update_data_returns_chore_data(
        self, hass: HomeAssistant, mock_config_entry
    ):
        mock_config_entry.add_to_hass(hass)
        coordinator = HashCoordinator(hass, mock_config_entry)
        await coordinator.async_load_store()
        data = await coordinator._async_update_data()

        assert MOCK_CHORE_ID in data
        chore = data[MOCK_CHORE_ID]
        assert chore["name"] == "Vacuum Living Room"
        assert chore["room"] == "Living Room"
        assert chore["interval_days"] == 14
        assert 0.0 <= chore["cleanliness"] <= 100.0
        assert chore["status"] in ("Great", "Fine", "Dirty", "Urgent")

    @pytest.mark.usefixtures("bypass_store")
    async def test_complete_chore_resets_cleanliness(
        self, hass: HomeAssistant, mock_config_entry
    ):
        mock_config_entry.add_to_hass(hass)
        coordinator = HashCoordinator(hass, mock_config_entry)
        await coordinator.async_load_store()

        # Manually age the chore
        runtime = coordinator._ensure_runtime(MOCK_CHORE_ID)
        old_time = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=10)
        runtime["last_cleaned"] = old_time.isoformat()

        data = await coordinator._async_update_data()
        assert data[MOCK_CHORE_ID]["cleanliness"] < 50

        # Complete it
        await coordinator.async_complete_chore(MOCK_CHORE_ID)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        data = await coordinator._async_update_data()
        assert data[MOCK_CHORE_ID]["cleanliness"] > 99

    @pytest.mark.usefixtures("bypass_store")
    async def test_complete_chore_advances_rotation(
        self, hass: HomeAssistant, mock_config_entry
    ):
        mock_config_entry.add_to_hass(hass)
        coordinator = HashCoordinator(hass, mock_config_entry)
        await coordinator.async_load_store()

        runtime = coordinator._ensure_runtime(MOCK_CHORE_ID)
        assert runtime["rotation_index"] == 0

        await coordinator.async_complete_chore(MOCK_CHORE_ID)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert runtime["rotation_index"] == 1

    @pytest.mark.usefixtures("bypass_store")
    async def test_reset_chore_does_not_advance_rotation(
        self, hass: HomeAssistant, mock_config_entry
    ):
        mock_config_entry.add_to_hass(hass)
        coordinator = HashCoordinator(hass, mock_config_entry)
        await coordinator.async_load_store()

        runtime = coordinator._ensure_runtime(MOCK_CHORE_ID)
        assert runtime["rotation_index"] == 0

        await coordinator.async_reset_chore(MOCK_CHORE_ID)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert runtime["rotation_index"] == 0

    @pytest.mark.usefixtures("bypass_store")
    async def test_global_pause_hides_next_due(
        self, hass: HomeAssistant, mock_config_entry
    ):
        mock_config_entry.add_to_hass(hass)
        # Enable global pause
        hass.config_entries.async_update_entry(
            mock_config_entry,
            options={**mock_config_entry.options, CONF_GLOBAL_PAUSE: True},
        )
        coordinator = HashCoordinator(hass, mock_config_entry)
        await coordinator.async_load_store()

        data = await coordinator._async_update_data()
        assert data[MOCK_CHORE_ID]["next_due"] is None
        # Cleanliness still runs
        assert data[MOCK_CHORE_ID]["cleanliness"] is not None

    @pytest.mark.usefixtures("bypass_store")
    async def test_cleanup_removed_chores(self, hass: HomeAssistant, mock_config_entry):
        mock_config_entry.add_to_hass(hass)
        coordinator = HashCoordinator(hass, mock_config_entry)
        await coordinator.async_load_store()

        # Add orphan runtime data
        coordinator._runtime_data["orphan-chore"] = {
            "last_cleaned": "2025-01-01T00:00:00",
            "rotation_index": 0,
            "completed_by_history": [],
        }

        await coordinator.async_cleanup_removed_chores()
        assert "orphan-chore" not in coordinator._runtime_data
