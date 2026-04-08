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
        EspRfidV3ConfiguredDoorsSensor(runtime.coordinator, runtime.site_name),
        EspRfidV3RegistrySensor(runtime),
    ]

    for door in runtime.coordinator.doors.values():
        entities.extend(
            [
                EspRfidV3SnapshotVersionSensor(runtime.coordinator, door),
                EspRfidV3EventQueueDepthSensor(runtime.coordinator, door),
                EspRfidV3CredentialCountSensor(runtime.coordinator, door),
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


class EspRfidV3CredentialCountSensor(EspRfidV3DoorCoordinatorEntity, SensorEntity):
    """Expose how many credentials the door currently has in its snapshot."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Credential Count"
    _attr_native_unit_of_measurement = "credentials"
    _attr_icon = "mdi:key-chain"

    def __init__(self, coordinator: EspRfidV3Coordinator, door: DoorNodeConfig) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_credential_count"

    @property
    def native_value(self) -> int:
        """Return credential count."""
        return self.coordinator.get_status(self._door.device_id).credential_count


class EspRfidV3RegistrySensor(CoordinatorEntity[EspRfidV3Coordinator], SensorEntity):
    """Expose a UI-friendly registry summary for doors and users."""

    _attr_has_entity_name = True
    _attr_name = "ESP-RFID V3 Registry"
    _attr_unique_id = f"{DOMAIN}_registry"
    _attr_icon = "mdi:door-sliding-lock"

    def __init__(self, runtime: EspRfidV3RuntimeData) -> None:
        """Initialize the registry sensor."""
        super().__init__(runtime.coordinator)
        self._runtime = runtime

    @property
    def native_value(self) -> int:
        """Return the number of centrally managed users."""
        return len(self.coordinator.users)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return a registry snapshot for the admin panel."""
        doors = []
        for door in self.coordinator.doors.values():
            status = self.coordinator.get_status(door.device_id)
            doors.append(
                {
                    "device_id": door.device_id,
                    "name": door.name,
                    "base_url": door.base_url,
                    "enabled": door.enabled,
                    "allow_hold_open": door.allow_hold_open,
                    "available": status.available,
                    "health_state": status.health_state,
                    "lock_state": status.lock_state,
                    "snapshot_version": status.snapshot_version,
                    "credential_count": status.credential_count,
                    "event_queue_depth": status.event_queue_depth,
                    "last_sync_at": status.last_sync_at,
                    "last_error": status.last_error,
                }
            )

        users = []
        for user in self.coordinator.users.values():
            users.append(
                {
                    "user_id": user.user_id,
                    "name": user.name,
                    "door_ids": list(user.door_ids),
                    "active": user.active,
                    "has_tag": user.tag_digest is not None,
                    "has_pin": user.pin_hash is not None,
                    "valid_from": user.valid_from,
                    "valid_until": user.valid_until,
                }
            )

        return {
            "site_name": self._runtime.site_name,
            "door_count": len(doors),
            "user_count": len(users),
            "doors": doors,
            "users": users,
        }
