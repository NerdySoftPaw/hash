"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.hash.const import (
    CONF_CHORE_ID,
    CONF_CHORE_NAME,
    CONF_CHORES,
    CONF_GLOBAL_PAUSE,
    CONF_INTERVAL,
    CONF_INTERVAL_PRESET,
    CONF_ROOM,
    CONF_VACATION_PERSONS,
    DOMAIN,
)


async def test_config_flow_creates_entry(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HASH"
    assert result["options"][CONF_CHORES] == []
    assert result["options"][CONF_VACATION_PERSONS] == []
    assert result["options"][CONF_GLOBAL_PAUSE] is False


async def test_options_flow_add_chore(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.hash.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # Select "add_chore"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"action": "add_chore"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_chore"

    # Fill in chore details (omit assigned_person to leave empty/rotating)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CHORE_NAME: "Dust Shelves",
            CONF_ROOM: "study",
            CONF_INTERVAL_PRESET: "1_week",
        },
    )
    # Should go back to init
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_add_chore_custom_interval(
    hass: HomeAssistant, mock_config_entry
):
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.hash.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"action": "add_chore"}
    )

    # Select custom interval (omit assigned_person to leave empty/rotating)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_CHORE_NAME: "Special Task",
            CONF_ROOM: "garage",
            CONF_INTERVAL_PRESET: "custom",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "add_chore_custom_interval"

    # Enter custom days
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_INTERVAL: 45},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_remove_chore(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.hash.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"action": "remove_chore"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_chore_remove"

    # Get the chore id from the existing options
    chore_id = mock_config_entry.options[CONF_CHORES][0][CONF_CHORE_ID]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CHORE_ID: chore_id},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_manage_vacation(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.hash.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"action": "manage_vacation"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manage_vacation"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_VACATION_PERSONS: ["person.alice"],
            CONF_GLOBAL_PAUSE: True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_done_saves(hass: HomeAssistant, mock_config_entry):
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.hash.async_setup_entry", return_value=True):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"action": "done"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
