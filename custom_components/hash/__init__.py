"""HASH - Home Assistant Sweeping Hub."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CHORE_ID,
    CONF_GLOBAL_PAUSE,
    CONF_VACATION_PERSONS,
    DOMAIN,
    PLATFORMS,
    SERVICE_COMPLETE_CHORE,
    SERVICE_RESET_CHORE,
    SERVICE_SET_GLOBAL_PAUSE,
    SERVICE_SET_VACATION,
)
from .coordinator import HashCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

COMPLETE_CHORE_SCHEMA = vol.Schema({vol.Required(CONF_CHORE_ID): cv.string})

RESET_CHORE_SCHEMA = vol.Schema({vol.Required(CONF_CHORE_ID): cv.string})

SET_VACATION_SCHEMA = vol.Schema(
    {
        vol.Required("person_entity_id"): cv.entity_id,
        vol.Required("vacation"): cv.boolean,
    }
)

SET_GLOBAL_PAUSE_SCHEMA = vol.Schema({vol.Required("paused"): cv.boolean})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HASH from a config entry."""
    coordinator = HashCoordinator(hass, entry)
    await coordinator.async_load_store()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register services (only once)
    if not hass.services.has_service(DOMAIN, SERVICE_COMPLETE_CHORE):
        _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry — clean up store."""
    coordinator: HashCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator:
        await coordinator._store.async_remove()


def _register_services(hass: HomeAssistant) -> None:
    """Register HASH services."""

    async def _get_coordinator() -> HashCoordinator | None:
        """Get the first available coordinator."""
        entries = hass.data.get(DOMAIN, {})
        for coordinator in entries.values():
            if isinstance(coordinator, HashCoordinator):
                return coordinator
        return None

    async def handle_complete_chore(call: ServiceCall) -> None:
        """Handle complete_chore service call."""
        coordinator = await _get_coordinator()
        if coordinator:
            await coordinator.async_complete_chore(call.data[CONF_CHORE_ID])

    async def handle_reset_chore(call: ServiceCall) -> None:
        """Handle reset_chore service call."""
        coordinator = await _get_coordinator()
        if coordinator:
            await coordinator.async_reset_chore(call.data[CONF_CHORE_ID])

    async def handle_set_vacation(call: ServiceCall) -> None:
        """Handle set_vacation service call."""
        coordinator = await _get_coordinator()
        if not coordinator:
            return
        entry = coordinator.config_entry
        person = call.data["person_entity_id"]
        vacation = call.data["vacation"]

        current_options = dict(entry.options)
        vacation_list = list(current_options.get(CONF_VACATION_PERSONS, []))

        if vacation and person not in vacation_list:
            vacation_list.append(person)
        elif not vacation and person in vacation_list:
            vacation_list.remove(person)

        current_options[CONF_VACATION_PERSONS] = vacation_list
        hass.config_entries.async_update_entry(entry, options=current_options)
        await coordinator.async_request_refresh()

    async def handle_set_global_pause(call: ServiceCall) -> None:
        """Handle set_global_pause service call."""
        coordinator = await _get_coordinator()
        if not coordinator:
            return
        entry = coordinator.config_entry
        paused = call.data["paused"]

        current_options = dict(entry.options)
        current_options[CONF_GLOBAL_PAUSE] = paused
        hass.config_entries.async_update_entry(entry, options=current_options)
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_COMPLETE_CHORE,
        handle_complete_chore,
        schema=COMPLETE_CHORE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_CHORE,
        handle_reset_chore,
        schema=RESET_CHORE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VACATION,
        handle_set_vacation,
        schema=SET_VACATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GLOBAL_PAUSE,
        handle_set_global_pause,
        schema=SET_GLOBAL_PAUSE_SCHEMA,
    )
