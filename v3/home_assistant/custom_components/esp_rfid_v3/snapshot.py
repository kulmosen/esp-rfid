"""Snapshot generation for ESP-RFID V3."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import AccessUser, DoorNodeConfig, DoorSnapshot, DoorSnapshotUser


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_door_snapshot(
    *,
    site_name: str,
    door: DoorNodeConfig,
    users: dict[str, AccessUser],
) -> DoorSnapshot:
    """Generate a per-door snapshot from central storage."""
    snapshot_users: list[DoorSnapshotUser] = []

    for user in users.values():
        if not user.active or door.device_id not in user.door_ids:
            continue

        snapshot_users.append(
            DoorSnapshotUser(
                user_id=user.user_id,
                name=user.name,
                tag_digest=user.tag_digest,
                pin_hash=user.pin_hash,
                pin_salt=user.pin_salt,
                pin_iterations=user.pin_iterations,
                valid_from=user.valid_from,
                valid_until=user.valid_until,
            )
        )

    return DoorSnapshot(
        site_name=site_name,
        device_id=door.device_id,
        door_name=door.name,
        generated_at=_utc_now(),
        version=f"{door.device_id}-{int(datetime.now(timezone.utc).timestamp())}",
        allow_hold_open=door.allow_hold_open,
        users=snapshot_users,
    )
