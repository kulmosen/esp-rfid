"""Persistent storage helpers for ESP-RFID V3."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import DoorNodeConfig, EspRfidV3StorageData


class EspRfidV3Store:
    """Wrapper around Home Assistant storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self._store = Store[dict](hass, STORAGE_VERSION, STORAGE_KEY)
        self._cache: EspRfidV3StorageData | None = None

    async def async_load(self) -> EspRfidV3StorageData:
        """Load storage data."""
        if self._cache is not None:
            return self._cache

        raw = await self._store.async_load()
        self._cache = EspRfidV3StorageData.from_dict(raw)
        return self._cache

    async def async_save(self, data: EspRfidV3StorageData) -> None:
        """Persist storage data."""
        self._cache = data
        await self._store.async_save(data.to_dict())

    async def async_get_doors(self) -> dict[str, DoorNodeConfig]:
        """Return all configured doors."""
        data = await self.async_load()
        return dict(data.doors)

    async def async_upsert_door(self, door: DoorNodeConfig) -> None:
        """Create or update a door."""
        data = await self.async_load()
        data.doors[door.device_id] = door
        await self.async_save(data)

    async def async_remove_door(self, device_id: str) -> bool:
        """Remove a configured door."""
        data = await self.async_load()
        if device_id not in data.doors:
            return False

        del data.doors[device_id]
        await self.async_save(data)
        return True
