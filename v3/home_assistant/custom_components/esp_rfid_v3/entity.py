"""Entity helpers for ESP-RFID V3."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EspRfidV3Coordinator
from .models import DoorNodeConfig


class EspRfidV3DoorCoordinatorEntity(CoordinatorEntity[EspRfidV3Coordinator]):
    """Base class for door entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EspRfidV3Coordinator, door: DoorNodeConfig) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._door = door

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._door.device_id)},
            name=self._door.name,
            manufacturer="esp-rfid",
            model="ESP-RFID V3 Door Node",
            configuration_url=self._door.base_url,
        )
