"""Tests for integration setup and services."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.hash.const import (
    CONF_CHORE_ID,
    CONF_GLOBAL_PAUSE,
    CONF_VACATION_PERSONS,
    DOMAIN,
    SERVICE_COMPLETE_CHORE,
    SERVICE_RESET_CHORE,
    SERVICE_SET_GLOBAL_PAUSE,
    SERVICE_SET_VACATION,
)
from custom_components.hash.coordinator import HashCoordinator

from .conftest import MOCK_CHORE_ID


@pytest.mark.usefixtures("bypass_store")
async def test_setup_and_unload(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.usefixtures("bypass_store")
async def test_services_registered(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, SERVICE_COMPLETE_CHORE)
    assert hass.services.has_service(DOMAIN, SERVICE_RESET_CHORE)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_VACATION)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_GLOBAL_PAUSE)


@pytest.mark.usefixtures("bypass_store")
async def test_service_complete_chore(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: HashCoordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    runtime = coordinator._ensure_runtime(MOCK_CHORE_ID)
    assert runtime["rotation_index"] == 0

    await hass.services.async_call(
        DOMAIN,
        SERVICE_COMPLETE_CHORE,
        {CONF_CHORE_ID: MOCK_CHORE_ID},
        blocking=True,
    )

    assert runtime["rotation_index"] == 1


@pytest.mark.usefixtures("bypass_store")
async def test_service_reset_chore(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator: HashCoordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    runtime = coordinator._ensure_runtime(MOCK_CHORE_ID)
    assert runtime["rotation_index"] == 0

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RESET_CHORE,
        {CONF_CHORE_ID: MOCK_CHORE_ID},
        blocking=True,
    )

    # Rotation should NOT advance
    assert runtime["rotation_index"] == 0


@pytest.mark.usefixtures("bypass_store")
async def test_service_set_vacation(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_VACATION,
        {"person_entity_id": "person.alice", "vacation": True},
        blocking=True,
    )

    assert "person.alice" in mock_config_entry.options[CONF_VACATION_PERSONS]

    # Remove vacation
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_VACATION,
        {"person_entity_id": "person.alice", "vacation": False},
        blocking=True,
    )

    assert "person.alice" not in mock_config_entry.options[CONF_VACATION_PERSONS]


@pytest.mark.usefixtures("bypass_store")
async def test_service_set_global_pause(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_GLOBAL_PAUSE,
        {"paused": True},
        blocking=True,
    )

    assert mock_config_entry.options[CONF_GLOBAL_PAUSE] is True
