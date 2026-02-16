"""Config flow for HASH integration."""

from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ASSIGNED_PERSON,
    CONF_CHORE_ID,
    CONF_CHORE_NAME,
    CONF_CHORES,
    CONF_GLOBAL_PAUSE,
    CONF_INTERVAL,
    CONF_INTERVAL_PRESET,
    CONF_ROOM,
    CONF_VACATION_PERSONS,
    DOMAIN,
    INTERVAL_LABELS,
    INTERVAL_PRESETS,
)


class HashConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HASH."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — just confirm to create the entry."""
        if user_input is not None:
            return self.async_create_entry(
                title="HASH",
                data={},
                options={
                    CONF_CHORES: [],
                    CONF_VACATION_PERSONS: [],
                    CONF_GLOBAL_PAUSE: False,
                },
            )

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> HashOptionsFlow:
        """Get the options flow handler."""
        return HashOptionsFlow()


class HashOptionsFlow(OptionsFlow):
    """Handle HASH options."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._chores: list[dict[str, Any]] = []
        self._vacation_persons: list[str] = []
        self._global_pause: bool = False
        self._selected_chore_id: str | None = None
        # Temp storage for add_chore when custom interval is needed
        self._pending_chore: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show main menu for options."""
        self._chores = list(self.config_entry.options.get(CONF_CHORES, []))
        self._vacation_persons = list(
            self.config_entry.options.get(CONF_VACATION_PERSONS, [])
        )
        self._global_pause = self.config_entry.options.get(CONF_GLOBAL_PAUSE, False)

        if user_input is not None:
            action = user_input.get("action")
            if action == "add_chore":
                return await self.async_step_add_chore()
            if action == "edit_chore":
                return await self.async_step_select_chore_edit()
            if action == "remove_chore":
                return await self.async_step_select_chore_remove()
            if action == "manage_vacation":
                return await self.async_step_manage_vacation()
            if action == "done":
                return self.async_create_entry(
                    title="HASH",
                    data={
                        CONF_CHORES: self._chores,
                        CONF_VACATION_PERSONS: self._vacation_persons,
                        CONF_GLOBAL_PAUSE: self._global_pause,
                    },
                )

        actions = [
            selector.SelectOptionDict(value="add_chore", label="Add Chore"),
        ]
        if self._chores:
            actions.append(
                selector.SelectOptionDict(value="edit_chore", label="Edit Chore")
            )
            actions.append(
                selector.SelectOptionDict(value="remove_chore", label="Remove Chore")
            )
        actions.append(
            selector.SelectOptionDict(
                value="manage_vacation", label="Manage Vacation & Pause"
            )
        )
        actions.append(selector.SelectOptionDict(value="done", label="Done"))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=actions,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    async def async_step_add_chore(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new chore."""
        if user_input is not None:
            preset = user_input[CONF_INTERVAL_PRESET]
            if preset == "custom":
                # Store partial chore and ask for custom interval
                self._pending_chore = {
                    CONF_CHORE_NAME: user_input[CONF_CHORE_NAME],
                    CONF_ROOM: user_input.get(CONF_ROOM, ""),
                    CONF_ASSIGNED_PERSON: user_input.get(CONF_ASSIGNED_PERSON, ""),
                }
                return await self.async_step_add_chore_custom_interval()

            interval_days = INTERVAL_PRESETS[preset]
            chore = {
                CONF_CHORE_ID: str(uuid.uuid4()),
                CONF_CHORE_NAME: user_input[CONF_CHORE_NAME],
                CONF_ROOM: user_input.get(CONF_ROOM, ""),
                CONF_INTERVAL: interval_days,
                CONF_ASSIGNED_PERSON: user_input.get(CONF_ASSIGNED_PERSON, ""),
            }
            self._chores.append(chore)
            return await self.async_step_init()

        preset_options = [
            selector.SelectOptionDict(value=key, label=label)
            for key, label in INTERVAL_LABELS.items()
        ]

        return self.async_show_form(
            step_id="add_chore",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHORE_NAME): selector.TextSelector(),
                    vol.Optional(CONF_ROOM, default=""): selector.TextSelector(),
                    vol.Required(
                        CONF_INTERVAL_PRESET, default="2_weeks"
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=preset_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_ASSIGNED_PERSON,
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="person")
                    ),
                }
            ),
        )

    async def async_step_add_chore_custom_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for custom interval in days."""
        if user_input is not None and self._pending_chore is not None:
            chore = {
                CONF_CHORE_ID: str(uuid.uuid4()),
                CONF_CHORE_NAME: self._pending_chore[CONF_CHORE_NAME],
                CONF_ROOM: self._pending_chore.get(CONF_ROOM, ""),
                CONF_INTERVAL: int(user_input[CONF_INTERVAL]),
                CONF_ASSIGNED_PERSON: self._pending_chore.get(CONF_ASSIGNED_PERSON, ""),
            }
            self._chores.append(chore)
            self._pending_chore = None
            return await self.async_step_init()

        return self.async_show_form(
            step_id="add_chore_custom_interval",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INTERVAL): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=730,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="days",
                        )
                    ),
                }
            ),
        )

    async def async_step_select_chore_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a chore to edit."""
        if user_input is not None:
            self._selected_chore_id = user_input[CONF_CHORE_ID]
            return await self.async_step_edit_chore()

        chore_options = [
            selector.SelectOptionDict(
                value=c[CONF_CHORE_ID],
                label=f"{c[CONF_CHORE_NAME]} ({c.get(CONF_ROOM, '')})",
            )
            for c in self._chores
        ]

        return self.async_show_form(
            step_id="select_chore_edit",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHORE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=chore_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_edit_chore(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit an existing chore."""
        chore = next(
            (c for c in self._chores if c[CONF_CHORE_ID] == self._selected_chore_id),
            None,
        )
        if chore is None:
            return await self.async_step_init()

        if user_input is not None:
            preset = user_input[CONF_INTERVAL_PRESET]
            if preset == "custom":
                self._pending_chore = {
                    CONF_CHORE_ID: chore[CONF_CHORE_ID],
                    CONF_CHORE_NAME: user_input[CONF_CHORE_NAME],
                    CONF_ROOM: user_input.get(CONF_ROOM, ""),
                    CONF_ASSIGNED_PERSON: user_input.get(CONF_ASSIGNED_PERSON, ""),
                }
                return await self.async_step_edit_chore_custom_interval()

            chore[CONF_CHORE_NAME] = user_input[CONF_CHORE_NAME]
            chore[CONF_ROOM] = user_input.get(CONF_ROOM, "")
            chore[CONF_INTERVAL] = INTERVAL_PRESETS[preset]
            chore[CONF_ASSIGNED_PERSON] = user_input.get(CONF_ASSIGNED_PERSON, "")
            return await self.async_step_init()

        # Determine current preset
        current_interval = chore.get(CONF_INTERVAL, 14)
        current_preset = "custom"
        for key, days in INTERVAL_PRESETS.items():
            if days == current_interval:
                current_preset = key
                break

        preset_options = [
            selector.SelectOptionDict(value=key, label=label)
            for key, label in INTERVAL_LABELS.items()
        ]

        return self.async_show_form(
            step_id="edit_chore",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CHORE_NAME,
                        default=chore.get(CONF_CHORE_NAME, ""),
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_ROOM, default=chore.get(CONF_ROOM, "")
                    ): selector.TextSelector(),
                    vol.Required(
                        CONF_INTERVAL_PRESET, default=current_preset
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=preset_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_ASSIGNED_PERSON,
                        description={
                            "suggested_value": chore.get(CONF_ASSIGNED_PERSON) or None
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="person")
                    ),
                }
            ),
        )

    async def async_step_edit_chore_custom_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle custom interval input for editing a chore."""
        if user_input is not None and self._pending_chore is not None:
            chore_id = self._pending_chore[CONF_CHORE_ID]
            chore = next(
                (c for c in self._chores if c[CONF_CHORE_ID] == chore_id),
                None,
            )
            if chore is not None:
                chore[CONF_CHORE_NAME] = self._pending_chore[CONF_CHORE_NAME]
                chore[CONF_ROOM] = self._pending_chore.get(CONF_ROOM, "")
                chore[CONF_INTERVAL] = int(user_input[CONF_INTERVAL])
                chore[CONF_ASSIGNED_PERSON] = self._pending_chore.get(
                    CONF_ASSIGNED_PERSON, ""
                )
            self._pending_chore = None
            return await self.async_step_init()

        return self.async_show_form(
            step_id="edit_chore_custom_interval",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_INTERVAL): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1,
                            max=730,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="days",
                        )
                    ),
                }
            ),
        )

    async def async_step_select_chore_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a chore to remove."""
        if user_input is not None:
            chore_id = user_input[CONF_CHORE_ID]
            self._chores = [c for c in self._chores if c[CONF_CHORE_ID] != chore_id]
            return await self.async_step_init()

        chore_options = [
            selector.SelectOptionDict(
                value=c[CONF_CHORE_ID],
                label=f"{c[CONF_CHORE_NAME]} ({c.get(CONF_ROOM, '')})",
            )
            for c in self._chores
        ]

        return self.async_show_form(
            step_id="select_chore_remove",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHORE_ID): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=chore_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_manage_vacation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage vacation persons and global pause."""
        if user_input is not None:
            self._vacation_persons = user_input.get(CONF_VACATION_PERSONS, [])
            self._global_pause = user_input.get(CONF_GLOBAL_PAUSE, False)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="manage_vacation",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_VACATION_PERSONS,
                        default=self._vacation_persons,
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="person", multiple=True)
                    ),
                    vol.Optional(
                        CONF_GLOBAL_PAUSE,
                        default=self._global_pause,
                    ): selector.BooleanSelector(),
                }
            ),
        )
