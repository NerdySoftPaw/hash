"""Sensor platform for HASH — one cleanliness sensor per chore."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ICON_DIRTY,
    ICON_FINE,
    ICON_GREAT,
    ICON_URGENT,
    STATUS_DIRTY,
    STATUS_FINE,
    STATUS_GREAT,
)
from .coordinator import HashCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HASH sensors from a config entry."""
    coordinator: HashCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        HashChoreSensor(coordinator, chore_id, entry) for chore_id in coordinator.data
    ]
    async_add_entities(entities)


class HashChoreSensor(CoordinatorEntity[HashCoordinator], SensorEntity):
    """Sensor representing the cleanliness of a single chore."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: HashCoordinator,
        chore_id: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._chore_id = chore_id
        self._attr_unique_id = f"{entry.entry_id}_{chore_id}"
        chore_data = coordinator.data.get(chore_id, {})
        self._attr_translation_key = "chore_cleanliness"
        self._attr_name = chore_data.get("name", chore_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="HASH Cleaning Hub",
            manufacturer="HASH",
            model="Sweeping Hub",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator data has this chore."""
        return super().available and self._chore_id in self.coordinator.data

    @property
    def native_value(self) -> float | None:
        """Return cleanliness percentage."""
        data = self.coordinator.data.get(self._chore_id)
        if data is None:
            return None
        return data["cleanliness"]

    @property
    def icon(self) -> str:
        """Return icon based on status."""
        data = self.coordinator.data.get(self._chore_id)
        if data is None:
            return ICON_GREAT
        status = data["status"]
        if status == STATUS_GREAT:
            return ICON_GREAT
        if status == STATUS_FINE:
            return ICON_FINE
        if status == STATUS_DIRTY:
            return ICON_DIRTY
        return ICON_URGENT

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        data = self.coordinator.data.get(self._chore_id)
        if data is None:
            return {}
        return {
            "chore_id": data["chore_id"],
            "last_cleaned": data["last_cleaned"],
            "days_since_cleaning": data["days_since"],
            "status": data["status"],
            "room": data["room"],
            "interval_days": data["interval_days"],
            "interval_display": data["interval_display"],
            "assigned_to": data["assigned_to"],
            "next_due": data["next_due"],
        }
