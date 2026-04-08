"""Binary sensors for ESP-RFID V3."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import EspRfidV3Coordinator
from .entity import EspRfidV3DoorCoordinatorEntity
from .models import DoorNodeConfig, EspRfidV3RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    runtime: EspRfidV3RuntimeData = entry.runtime_data
    entities: list[BinarySensorEntity] = []

    for door in runtime.coordinator.doors.values():
        entities.extend(
            [
                EspRfidV3OnlineBinarySensor(runtime.coordinator, door),
                EspRfidV3DegradedBinarySensor(runtime.coordinator, door),
            ]
        )

    async_add_entities(entities)


class EspRfidV3OnlineBinarySensor(EspRfidV3DoorCoordinatorEntity, BinarySensorEntity):
    """Expose whether the door node is online."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Online"

    def __init__(self, coordinator: EspRfidV3Coordinator, door: DoorNodeConfig) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_online"

    @property
    def is_on(self) -> bool:
        """Return online state."""
        return self.coordinator.get_status(self._door.device_id).available


class EspRfidV3DegradedBinarySensor(EspRfidV3DoorCoordinatorEntity, BinarySensorEntity):
    """Expose whether the node is in a degraded state."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Degraded"

    def __init__(self, coordinator: EspRfidV3Coordinator, door: DoorNodeConfig) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_degraded"

    @property
    def is_on(self) -> bool:
        """Return degraded state."""
        return self.coordinator.get_status(self._door.device_id).health_state == "degraded"
