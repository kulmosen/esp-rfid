"""Sensors for ESP-RFID V3."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import parse_datetime

from .const import DOMAIN
from .coordinator import EspRfidV3Coordinator
from .entity import EspRfidV3DoorCoordinatorEntity
from .models import DoorNodeConfig, EspRfidV3RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    runtime: EspRfidV3RuntimeData = entry.runtime_data
    entities: list[SensorEntity] = [
        EspRfidV3ConfiguredDoorsSensor(runtime.coordinator, runtime.site_name)
    ]

    for door in runtime.coordinator.doors.values():
        entities.extend(
            [
                EspRfidV3SnapshotVersionSensor(runtime.coordinator, door),
                EspRfidV3EventQueueDepthSensor(runtime.coordinator, door),
                EspRfidV3LastSyncSensor(runtime.coordinator, door),
            ]
        )

    async_add_entities(entities)


class EspRfidV3ConfiguredDoorsSensor(CoordinatorEntity[EspRfidV3Coordinator], SensorEntity):
    """Expose how many doors are configured in HA."""

    _attr_has_entity_name = True
    _attr_name = "Configured Doors"
    _attr_unique_id = f"{DOMAIN}_configured_doors"
    _attr_icon = "mdi:door"

    def __init__(self, coordinator: EspRfidV3Coordinator, site_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._site_name = site_name

    @property
    def native_value(self) -> int:
        """Return the number of configured doors."""
        return len(self.coordinator.doors)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return site metadata."""
        return {"site_name": self._site_name}


class EspRfidV3SnapshotVersionSensor(EspRfidV3DoorCoordinatorEntity, SensorEntity):
    """Expose the latest snapshot version seen by a door node."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Snapshot Version"

    def __init__(self, coordinator: EspRfidV3Coordinator, door: DoorNodeConfig) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_snapshot_version"

    @property
    def native_value(self) -> str | None:
        """Return the snapshot version."""
        return self.coordinator.get_status(self._door.device_id).snapshot_version


class EspRfidV3EventQueueDepthSensor(EspRfidV3DoorCoordinatorEntity, SensorEntity):
    """Expose queued event count on a door node."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Event Queue Depth"
    _attr_native_unit_of_measurement = "events"
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: EspRfidV3Coordinator, door: DoorNodeConfig) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_event_queue_depth"

    @property
    def native_value(self) -> int:
        """Return queue depth."""
        return self.coordinator.get_status(self._door.device_id).event_queue_depth


class EspRfidV3LastSyncSensor(EspRfidV3DoorCoordinatorEntity, SensorEntity):
    """Expose the last sync timestamp."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_name = "Last Sync"

    def __init__(self, coordinator: EspRfidV3Coordinator, door: DoorNodeConfig) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_last_sync"

    @property
    def native_value(self) -> datetime | None:
        """Return the parsed last sync timestamp."""
        last_sync = self.coordinator.get_status(self._door.device_id).last_sync_at
        if last_sync is None:
            return None

        return parse_datetime(last_sync)
