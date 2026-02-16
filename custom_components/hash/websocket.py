"""WebSocket API for HASH dashboard."""

from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_ID,
    CONF_CHORE_NAME,
    CONF_CHORES,
    CONF_GLOBAL_PAUSE,
    CONF_INTERVAL,
    CONF_ROOM,
    CONF_VACATION_PERSONS,
    DOMAIN,
)
from .coordinator import HashCoordinator


def _get_coordinator(hass: HomeAssistant) -> HashCoordinator | None:
    """Get the first available coordinator."""
    entries = hass.data.get(DOMAIN, {})
    for coordinator in entries.values():
        if isinstance(coordinator, HashCoordinator):
            return coordinator
    return None


def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket commands for HASH."""
    websocket_api.async_register_command(hass, ws_handle_dashboard)
    websocket_api.async_register_command(hass, ws_handle_complete_chore)
    websocket_api.async_register_command(hass, ws_handle_add_chore)
    websocket_api.async_register_command(hass, ws_handle_edit_chore)
    websocket_api.async_register_command(hass, ws_handle_delete_chore)


@callback
@websocket_api.websocket_command({vol.Required("type"): "hash/dashboard"})
def ws_handle_dashboard(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle hash/dashboard command."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No HASH coordinator found")
        return

    options = coordinator.config_entry.options
    chores = coordinator.data or {}

    connection.send_result(
        msg["id"],
        {
            "chores": chores,
            "vacation_persons": options.get(CONF_VACATION_PERSONS, []),
            "global_pause": options.get(CONF_GLOBAL_PAUSE, False),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hash/complete_chore",
        vol.Required("chore_id"): str,
    }
)
@websocket_api.async_response
async def ws_handle_complete_chore(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle hash/complete_chore command."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No HASH coordinator found")
        return

    chore_id = msg["chore_id"]
    await coordinator.async_complete_chore(chore_id)
    connection.send_result(msg["id"], {"success": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hash/add_chore",
        vol.Required("name"): str,
        vol.Optional("room", default=""): str,
        vol.Required("interval"): int,
        vol.Optional("assigned_person", default=""): str,
    }
)
@websocket_api.async_response
async def ws_handle_add_chore(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle hash/add_chore command (admin only)."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No HASH coordinator found")
        return

    entry = coordinator.config_entry
    current_options = dict(entry.options)
    chores = list(current_options.get(CONF_CHORES, []))

    new_chore = {
        CONF_CHORE_ID: str(uuid.uuid4()),
        CONF_CHORE_NAME: msg["name"],
        CONF_ROOM: msg["room"],
        CONF_INTERVAL: msg["interval"],
        CONF_ASSIGNED_PERSON: msg["assigned_person"],
    }
    chores.append(new_chore)
    current_options[CONF_CHORES] = chores

    hass.config_entries.async_update_entry(entry, options=current_options)
    await coordinator.async_request_refresh()

    connection.send_result(
        msg["id"], {"success": True, "chore_id": new_chore[CONF_CHORE_ID]}
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hash/edit_chore",
        vol.Required("chore_id"): str,
        vol.Optional("name"): str,
        vol.Optional("room"): str,
        vol.Optional("interval"): int,
        vol.Optional("assigned_person"): str,
    }
)
@websocket_api.async_response
async def ws_handle_edit_chore(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle hash/edit_chore command (admin only)."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No HASH coordinator found")
        return

    chore_id = msg["chore_id"]
    entry = coordinator.config_entry
    current_options = dict(entry.options)
    chores = list(current_options.get(CONF_CHORES, []))

    found = False
    for chore in chores:
        if chore.get(CONF_CHORE_ID) == chore_id:
            if "name" in msg:
                chore[CONF_CHORE_NAME] = msg["name"]
            if "room" in msg:
                chore[CONF_ROOM] = msg["room"]
            if "interval" in msg:
                chore[CONF_INTERVAL] = msg["interval"]
            if "assigned_person" in msg:
                chore[CONF_ASSIGNED_PERSON] = msg["assigned_person"]
            found = True
            break

    if not found:
        connection.send_error(msg["id"], "not_found", "Chore not found")
        return

    current_options[CONF_CHORES] = chores
    hass.config_entries.async_update_entry(entry, options=current_options)
    await coordinator.async_request_refresh()

    connection.send_result(msg["id"], {"success": True})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hash/delete_chore",
        vol.Required("chore_id"): str,
    }
)
@websocket_api.async_response
async def ws_handle_delete_chore(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle hash/delete_chore command (admin only)."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No HASH coordinator found")
        return

    chore_id = msg["chore_id"]
    entry = coordinator.config_entry
    current_options = dict(entry.options)
    chores = list(current_options.get(CONF_CHORES, []))

    new_chores = [c for c in chores if c.get(CONF_CHORE_ID) != chore_id]
    if len(new_chores) == len(chores):
        connection.send_error(msg["id"], "not_found", "Chore not found")
        return

    current_options[CONF_CHORES] = new_chores
    hass.config_entries.async_update_entry(entry, options=current_options)
    await coordinator.async_request_refresh()

    connection.send_result(msg["id"], {"success": True})
