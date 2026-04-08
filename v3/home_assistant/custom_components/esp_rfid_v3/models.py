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
    credential_count: int = 0
    snapshot_generated_at: str | None = None
    last_error: str | None = None


@dataclass(slots=True)
class AccessUser:
    """A centrally managed access user."""

    user_id: str
    name: str
    door_ids: list[str] = field(default_factory=list)
    active: bool = True
    tag_digest: str | None = None
    pin_hash: str | None = None
    pin_salt: str | None = None
    pin_iterations: int | None = None
    valid_from: str | None = None
    valid_until: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the user to storage format."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "door_ids": list(self.door_ids),
            "active": self.active,
            "tag_digest": self.tag_digest,
            "pin_hash": self.pin_hash,
            "pin_salt": self.pin_salt,
            "pin_iterations": self.pin_iterations,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccessUser":
        """Create a user from storage data."""
        return cls(
            user_id=str(data["user_id"]),
            name=str(data["name"]),
            door_ids=[str(door_id) for door_id in data.get("door_ids", [])],
            active=bool(data.get("active", True)),
            tag_digest=(
                str(data["tag_digest"]) if data.get("tag_digest") is not None else None
            ),
            pin_hash=str(data["pin_hash"]) if data.get("pin_hash") is not None else None,
            pin_salt=str(data["pin_salt"]) if data.get("pin_salt") is not None else None,
            pin_iterations=(
                int(data["pin_iterations"])
                if data.get("pin_iterations") is not None
                else None
            ),
            valid_from=(
                str(data["valid_from"]) if data.get("valid_from") is not None else None
            ),
            valid_until=(
                str(data["valid_until"]) if data.get("valid_until") is not None else None
            ),
        )


@dataclass(slots=True)
class DoorSnapshotUser:
    """A user record stored in a door snapshot."""

    user_id: str
    name: str
    tag_digest: str | None = None
    pin_hash: str | None = None
    pin_salt: str | None = None
    pin_iterations: int | None = None
    valid_from: str | None = None
    valid_until: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the snapshot user to a serializable dict."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "tag_digest": self.tag_digest,
            "pin_hash": self.pin_hash,
            "pin_salt": self.pin_salt,
            "pin_iterations": self.pin_iterations,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
        }


@dataclass(slots=True)
class DoorSnapshot:
    """A per-door access snapshot."""

    site_name: str
    device_id: str
    door_name: str
    generated_at: str
    version: str
    allow_hold_open: bool
    users: list[DoorSnapshotUser] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the snapshot to a serializable dict."""
        return {
            "site_name": self.site_name,
            "device_id": self.device_id,
            "door_name": self.door_name,
            "generated_at": self.generated_at,
            "version": self.version,
            "allow_hold_open": self.allow_hold_open,
            "users": [user.to_dict() for user in self.users],
        }


@dataclass(slots=True)
class EspRfidV3StorageData:
    """Persistent integration data."""

    site_secret: str = ""
    doors: dict[str, DoorNodeConfig] = field(default_factory=dict)
    users: dict[str, AccessUser] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the storage model to a dict."""
        return {
            "site_secret": self.site_secret,
            "doors": {device_id: door.to_dict() for device_id, door in self.doors.items()},
            "users": {user_id: user.to_dict() for user_id, user in self.users.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EspRfidV3StorageData":
        """Build the storage model from a dict."""
        if not data:
            return cls()

        raw_doors = data.get("doors", {})
        raw_users = data.get("users", {})
        doors = {
            str(device_id): DoorNodeConfig.from_dict(door_data)
            for device_id, door_data in raw_doors.items()
        }
        users = {
            str(user_id): AccessUser.from_dict(user_data)
            for user_id, user_data in raw_users.items()
        }
        return cls(
            site_secret=str(data.get("site_secret", "")),
            doors=doors,
            users=users,
        )


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
