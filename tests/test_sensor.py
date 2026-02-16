"""Tests for the sensor platform."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.hash.const import DOMAIN
from custom_components.hash.coordinator import HashCoordinator

from .conftest import MOCK_CHORE_ID


@pytest.mark.usefixtures("bypass_store")
async def test_sensor_setup(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Search for hash sensors (exact entity_id depends on HA slugification)
    all_states = hass.states.async_all("sensor")
    hash_sensors = [
        s
        for s in all_states
        if DOMAIN in s.entity_id or "vacuum" in s.entity_id.lower()
    ]

    assert len(hash_sensors) >= 1
    sensor = hash_sensors[0]
    assert float(sensor.state) > 0
    assert sensor.attributes.get("area_id") == "living_room"
    assert sensor.attributes.get("room") == "living_room"
    assert sensor.attributes.get("interval_days") == 14
    assert sensor.attributes.get("status") in ("Great", "Fine", "Dirty", "Urgent")
    assert sensor.attributes.get("chore_id") == MOCK_CHORE_ID


@pytest.mark.usefixtures("bypass_store")
async def test_sensor_attributes_after_complete(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: HashCoordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

    # Complete the chore
    await coordinator.async_complete_chore(MOCK_CHORE_ID)
    await hass.async_block_till_done()

    all_states = hass.states.async_all("sensor")
    hash_sensors = [
        s
        for s in all_states
        if DOMAIN in s.entity_id or "vacuum" in s.entity_id.lower()
    ]
    assert len(hash_sensors) >= 1
    sensor = hash_sensors[0]
    # After completion, cleanliness should be very high
    assert float(sensor.state) > 99
