"""Data models for ESP-RFID V3."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any


@dataclass(slots=True)
class DoorNodeConfig:
    """A configured door node."""

    device_id: str
    name: str
    base_url: str
    api_token: str
    allow_hold_open: bool = True
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert the config to storage format."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "base_url": self.base_url.rstrip("/"),
            "api_token": self.api_token,
            "allow_hold_open": self.allow_hold_open,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DoorNodeConfig":
        """Create a node config from storage data."""
        return cls(
            device_id=str(data["device_id"]),
            name=str(data["name"]),
            base_url=str(data["base_url"]).rstrip("/"),
            api_token=str(data["api_token"]),
            allow_hold_open=bool(data.get("allow_hold_open", True)),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass(slots=True)
class DoorNodeStatus:
    """Live runtime state for a door node."""

    available: bool = False
    health_state: str = "offline"
    lock_state: str = "unknown"
    snapshot_version: str | None = None
    event_queue_depth: int = 0
    last_sync_at: str | None = None
    firmware_version: str | None = None
    relay_active: bool = False
    hold_supported: bool = True
    last_error: str | None = None


@dataclass(slots=True)
class EspRfidV3StorageData:
    """Persistent integration data."""

    doors: dict[str, DoorNodeConfig] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the storage model to a dict."""
        return {
            "doors": {device_id: door.to_dict() for device_id, door in self.doors.items()}
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EspRfidV3StorageData":
        """Build the storage model from a dict."""
        if not data:
            return cls()

        raw_doors = data.get("doors", {})
        doors = {
            str(device_id): DoorNodeConfig.from_dict(door_data)
            for device_id, door_data in raw_doors.items()
        }
        return cls(doors=doors)


@dataclass(slots=True)
class EspRfidV3RuntimeData:
    """Runtime data attached to the config entry."""

    entry_id: str
    site_name: str
    store: "EspRfidV3Store"
    coordinator: "EspRfidV3Coordinator"

if TYPE_CHECKING:
    from .coordinator import EspRfidV3Coordinator
    from .storage import EspRfidV3Store
