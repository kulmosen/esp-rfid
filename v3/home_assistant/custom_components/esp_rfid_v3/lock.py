"""Lock platform for ESP-RFID V3."""

from __future__ import annotations

from homeassistant.components.lock import (
    LockEntity,
    LockEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import LOCK_STATE_HOLD_ACTIVE, LOCK_STATE_PULSE_ACTIVE
from .entity import EspRfidV3DoorCoordinatorEntity
from .models import DoorNodeConfig, EspRfidV3RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lock entities from a config entry."""
    runtime: EspRfidV3RuntimeData = entry.runtime_data
    entities = [EspRfidV3DoorLock(runtime.coordinator, door) for door in runtime.coordinator.doors.values()]
    async_add_entities(entities)


class EspRfidV3DoorLock(EspRfidV3DoorCoordinatorEntity, LockEntity):
    """Represent a door in Home Assistant."""

    _attr_name = None
    _attr_has_entity_name = True
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(self, coordinator, door: DoorNodeConfig) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_lock"

    @property
    def is_locked(self) -> bool | None:
        """Return lock state."""
        status = self.coordinator.get_status(self._door.device_id)
        if not status.available:
            return None
        return status.lock_state not in (LOCK_STATE_PULSE_ACTIVE, LOCK_STATE_HOLD_ACTIVE)

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self.coordinator.get_status(self._door.device_id).available

    async def async_unlock(self, **kwargs) -> None:
        """Pulse the unlock output."""
        await self.coordinator.async_send_command(self._door.device_id, "pulse_unlock")

    async def async_open(self, **kwargs) -> None:
        """Open the door momentarily."""
        await self.coordinator.async_send_command(self._door.device_id, "pulse_unlock")

    async def async_lock(self, **kwargs) -> None:
        """Cancel hold-open if active."""
        await self.coordinator.async_send_command(self._door.device_id, "cancel_hold")
