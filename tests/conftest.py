"""Shared fixtures for HASH tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hash.const import (
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


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    return


@pytest.fixture(autouse=True)
def bypass_panel() -> Generator[None]:
    """Mock panel registration so tests don't need frontend/panel_custom."""
    with (
        patch(
            "custom_components.hash.async_register_panel",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.hash.async_unregister_panel",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.hash.register_websocket_commands",
        ),
    ):
        yield


MOCK_CHORE_ID = "test-chore-001"
MOCK_CHORE_ID_2 = "test-chore-002"


def make_chore(
    chore_id: str = MOCK_CHORE_ID,
    name: str = "Vacuum Living Room",
    room: str = "living_room",
    interval: int = 14,
    assigned_person: str = "",
) -> dict:
    return {
        CONF_CHORE_ID: chore_id,
        CONF_CHORE_NAME: name,
        CONF_ROOM: room,
        CONF_INTERVAL: interval,
        CONF_ASSIGNED_PERSON: assigned_person,
    }


@pytest.fixture
def mock_chore() -> dict:
    return make_chore()


@pytest.fixture
def mock_options() -> dict:
    return {
        CONF_CHORES: [make_chore()],
        CONF_VACATION_PERSONS: [],
        CONF_GLOBAL_PAUSE: False,
    }


@pytest.fixture
def mock_options_two_chores() -> dict:
    return {
        CONF_CHORES: [
            make_chore(),
            make_chore(
                chore_id=MOCK_CHORE_ID_2,
                name="Mop Kitchen",
                room="kitchen",
                interval=7,
                assigned_person="person.alice",
            ),
        ],
        CONF_VACATION_PERSONS: [],
        CONF_GLOBAL_PAUSE: False,
    }


@pytest.fixture
def mock_config_entry(mock_options: dict) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="HASH",
        data={},
        options=mock_options,
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_config_entry_two_chores(mock_options_two_chores: dict) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="HASH",
        data={},
        options=mock_options_two_chores,
        entry_id="test_entry_id_2",
    )


@pytest.fixture
def bypass_store() -> Generator[AsyncMock]:
    with (
        patch(
            "custom_components.hash.coordinator.Store",
        ) as mock_store_cls,
    ):
        instance = mock_store_cls.return_value
        instance.async_load = AsyncMock(return_value=None)
        instance.async_save = AsyncMock(return_value=None)
        instance.async_remove = AsyncMock(return_value=None)
        yield instance
