"""Persistent storage helpers for ESP-RFID V3."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import AccessUser, DoorNodeConfig, EspRfidV3StorageData
from .security import generate_site_secret


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
        if not self._cache.site_secret:
            self._cache.site_secret = generate_site_secret()
            await self._store.async_save(self._cache.to_dict())
        return self._cache

    async def async_save(self, data: EspRfidV3StorageData) -> None:
        """Persist storage data."""
        self._cache = data
        await self._store.async_save(data.to_dict())

    async def async_get_doors(self) -> dict[str, DoorNodeConfig]:
        """Return all configured doors."""
        data = await self.async_load()
        return dict(data.doors)

    async def async_get_users(self) -> dict[str, AccessUser]:
        """Return all centrally configured users."""
        data = await self.async_load()
        return dict(data.users)

    async def async_get_site_secret(self) -> str:
        """Return the current site secret."""
        data = await self.async_load()
        return data.site_secret

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
        for user in data.users.values():
            if device_id in user.door_ids:
                user.door_ids = [door_id for door_id in user.door_ids if door_id != device_id]
        await self.async_save(data)
        return True

    async def async_upsert_user(self, user: AccessUser) -> None:
        """Create or update a central user."""
        data = await self.async_load()
        data.users[user.user_id] = user
        await self.async_save(data)

    async def async_remove_user(self, user_id: str) -> bool:
        """Remove a central user."""
        data = await self.async_load()
        if user_id not in data.users:
            return False

        del data.users[user_id]
        await self.async_save(data)
        return True
