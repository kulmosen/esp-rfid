"""Buttons for ESP-RFID V3."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import EspRfidV3DoorCoordinatorEntity
from .models import DoorNodeConfig, EspRfidV3RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    runtime: EspRfidV3RuntimeData = entry.runtime_data
    entities: list[ButtonEntity] = [EspRfidV3SyncAllButton(runtime)]

    for door in runtime.coordinator.doors.values():
        entities.extend(
            [
                EspRfidV3ResyncDoorButton(runtime.coordinator, door),
                EspRfidV3CancelHoldButton(runtime.coordinator, door),
                EspRfidV3RebootDoorButton(runtime.coordinator, door),
            ]
        )

    async_add_entities(entities)


class EspRfidV3SyncAllButton(ButtonEntity):
    """Button to trigger a full refresh."""

    _attr_has_entity_name = True
    _attr_name = "Sync All Doors"
    _attr_unique_id = "esp_rfid_v3_sync_all"
    _attr_icon = "mdi:sync"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, runtime: EspRfidV3RuntimeData) -> None:
        """Initialize the button."""
        self._runtime = runtime

    async def async_press(self) -> None:
        """Trigger a refresh."""
        await self._runtime.coordinator.async_sync_all()


class EspRfidV3ResyncDoorButton(EspRfidV3DoorCoordinatorEntity, ButtonEntity):
    """Request a snapshot resync for a door."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Resync Door"
    _attr_icon = "mdi:sync"

    def __init__(self, coordinator, door: DoorNodeConfig) -> None:
        """Initialize the button."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_resync"

    async def async_press(self) -> None:
        """Request a resync."""
        await self.coordinator.async_send_command(self._door.device_id, "resync")


class EspRfidV3CancelHoldButton(EspRfidV3DoorCoordinatorEntity, ButtonEntity):
    """Cancel hold-open for a door."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Cancel Hold Open"
    _attr_icon = "mdi:lock"

    def __init__(self, coordinator, door: DoorNodeConfig) -> None:
        """Initialize the button."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_cancel_hold"

    async def async_press(self) -> None:
        """Cancel hold-open."""
        await self.coordinator.async_send_command(self._door.device_id, "cancel_hold")


class EspRfidV3RebootDoorButton(EspRfidV3DoorCoordinatorEntity, ButtonEntity):
    """Reboot a door node."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Reboot Door"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator, door: DoorNodeConfig) -> None:
        """Initialize the button."""
        super().__init__(coordinator, door)
        self._attr_unique_id = f"{door.device_id}_reboot"

    async def async_press(self) -> None:
        """Reboot the door."""
        await self.coordinator.async_send_command(self._door.device_id, "reboot")
