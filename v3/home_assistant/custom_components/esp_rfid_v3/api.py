"""HTTP client for ESP-RFID V3 door nodes."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    LOCK_STATE_UNKNOWN,
)
from .models import DoorNodeConfig, DoorNodeStatus


class EspRfidV3ApiError(Exception):
    """Raised when a device API call fails."""


class EspRfidV3ApiClient:
    """Thin client for a single ESP-RFID V3 door node."""

    def __init__(self, session: ClientSession, door: DoorNodeConfig) -> None:
        """Initialize the client."""
        self._session = session
        self._door = door

    @property
    def device_id(self) -> str:
        """Return the configured device id."""
        return self._door.device_id

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {self._door.api_token}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        """Build a full URL."""
        return f"{self._door.base_url.rstrip('/')}{path}"

    async def async_get_status(self) -> DoorNodeStatus:
        """Fetch live status from the node."""
        try:
            async with self._session.get(
                self._url("/v1/status"),
                headers=self._headers(),
            ) as response:
                if response.status != 200:
                    raise EspRfidV3ApiError(
                        f"{self._door.name} returned HTTP {response.status} for /v1/status"
                    )

                payload: dict[str, Any] = await response.json()
        except (ClientError, ValueError) as err:
            raise EspRfidV3ApiError(f"Status fetch failed for {self._door.name}: {err}") from err

        return DoorNodeStatus(
            available=True,
            health_state=str(payload.get("health_state", "online")),
            lock_state=str(payload.get("lock_state", LOCK_STATE_UNKNOWN)),
            snapshot_version=(
                str(payload["snapshot_version"])
                if payload.get("snapshot_version") is not None
                else None
            ),
            event_queue_depth=int(payload.get("event_queue_depth", 0)),
            last_sync_at=(
                str(payload["last_sync_at"])
                if payload.get("last_sync_at") is not None
                else None
            ),
            firmware_version=(
                str(payload["firmware_version"])
                if payload.get("firmware_version") is not None
                else None
            ),
            relay_active=bool(payload.get("relay_active", False)),
            hold_supported=bool(payload.get("hold_supported", self._door.allow_hold_open)),
        )

    async def async_post_command(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Send a command to the node."""
        try:
            async with self._session.post(
                self._url(f"/v1/command/{command}"),
                headers=self._headers(),
                json=payload or {},
            ) as response:
                if response.status not in (200, 202, 204):
                    body = await response.text()
                    raise EspRfidV3ApiError(
                        f"{self._door.name} rejected command {command} with HTTP {response.status}: {body}"
                    )
        except ClientError as err:
            raise EspRfidV3ApiError(
                f"Command {command} failed for {self._door.name}: {err}"
            ) from err


class EspRfidV3ApiClientFactory:
    """Factory for door API clients."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the factory."""
        self._session = session

    def create(self, door: DoorNodeConfig) -> EspRfidV3ApiClient:
        """Create a client for a door node."""
        return EspRfidV3ApiClient(self._session, door)
