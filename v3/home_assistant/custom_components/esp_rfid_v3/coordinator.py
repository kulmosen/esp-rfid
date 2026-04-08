"""Coordinator for ESP-RFID V3."""

from __future__ import annotations

import logging
from datetime import timedelta
from dataclasses import replace
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import EspRfidV3ApiClientFactory, EspRfidV3ApiError
from .const import (
    CONF_POLL_INTERVAL_SECONDS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    LOCK_STATE_DEGRADED,
    LOCK_STATE_UNKNOWN,
)
from .models import DoorNodeConfig, DoorNodeStatus
from .storage import EspRfidV3Store

LOGGER = logging.getLogger(__name__)


class EspRfidV3Coordinator(DataUpdateCoordinator[dict[str, DoorNodeStatus]]):
    """Fetch and cache live state for all configured door nodes."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: EspRfidV3Store,
        api_factory: EspRfidV3ApiClientFactory,
    ) -> None:
        """Initialize the coordinator."""
        poll_interval_seconds = int(
            entry.data.get(CONF_POLL_INTERVAL_SECONDS, DEFAULT_POLL_INTERVAL_SECONDS)
        )
        super().__init__(
            hass,
            logger=LOGGER,
            name="ESP-RFID V3",
            update_interval=timedelta(seconds=poll_interval_seconds),
        )
        self._store = store
        self._api_factory = api_factory
        self._doors: dict[str, DoorNodeConfig] = {}
        self._users: dict[str, "AccessUser"] = {}

    @property
    def doors(self) -> dict[str, DoorNodeConfig]:
        """Return configured doors."""
        return dict(self._doors)

    @property
    def users(self) -> dict[str, "AccessUser"]:
        """Return configured users."""
        return dict(self._users)

    def get_door(self, device_id: str) -> DoorNodeConfig:
        """Return a configured door."""
        return self._doors[device_id]

    def get_status(self, device_id: str) -> DoorNodeStatus:
        """Return the latest known status."""
        data = self.data or {}
        return data.get(device_id, DoorNodeStatus(lock_state=LOCK_STATE_UNKNOWN))

    async def _async_update_data(self) -> dict[str, DoorNodeStatus]:
        """Refresh all door statuses."""
        self._doors = await self._store.async_get_doors()
        self._users = await self._store.async_get_users()
        result: dict[str, DoorNodeStatus] = {}

        for device_id, door in self._doors.items():
            if not door.enabled:
                result[device_id] = DoorNodeStatus(
                    available=False,
                    health_state="disabled",
                    lock_state=LOCK_STATE_DEGRADED,
                    hold_supported=door.allow_hold_open,
                    last_error="Door is disabled in Home Assistant storage",
                )
                continue

            client = self._api_factory.create(door)
            try:
                result[device_id] = await client.async_get_status()
            except EspRfidV3ApiError as err:
                previous_data = self.data or {}
                previous = previous_data.get(device_id, DoorNodeStatus())
                result[device_id] = replace(
                    previous,
                    available=False,
                    health_state="offline",
                    lock_state=LOCK_STATE_DEGRADED,
                    hold_supported=door.allow_hold_open,
                    last_error=str(err),
                )

        return result

    async def async_send_command(
        self,
        device_id: str,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Send a command to a door node and refresh state."""
        door = self.get_door(device_id)
        client = self._api_factory.create(door)
        await client.async_post_command(command, payload)
        await self.async_request_refresh()

    async def async_sync_all(self) -> None:
        """Refresh all devices."""
        await self.async_request_refresh()

    async def async_push_snapshot(self, device_id: str, payload: dict[str, Any]) -> None:
        """Push a snapshot to a specific door and refresh state."""
        door = self.get_door(device_id)
        client = self._api_factory.create(door)
        await client.async_push_snapshot(payload)
        await self.async_request_refresh()


from .models import AccessUser  # noqa: E402
