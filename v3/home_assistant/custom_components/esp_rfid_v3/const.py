"""Constants for the ESP-RFID V3 integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "esp_rfid_v3"

CONF_SITE_NAME = "site_name"
CONF_POLL_INTERVAL_SECONDS = "poll_interval_seconds"

DEFAULT_SITE_NAME = "ESP-RFID V3"
DEFAULT_POLL_INTERVAL_SECONDS = 15
DEFAULT_COMMAND_TIMEOUT_SECONDS = 10
DEFAULT_PIN_ITERATIONS = 12000

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.LOCK,
    Platform.SENSOR,
)

SCAN_INTERVAL = timedelta(seconds=DEFAULT_POLL_INTERVAL_SECONDS)

ATTR_DEVICE_ID = "device_id"
ATTR_NAME = "name"
ATTR_BASE_URL = "base_url"
ATTR_API_TOKEN = "api_token"
ATTR_ALLOW_HOLD_OPEN = "allow_hold_open"
ATTR_ENABLED = "enabled"
ATTR_REASON = "reason"
ATTR_USER_ID = "user_id"
ATTR_DOOR_IDS = "door_ids"
ATTR_RFID_UID = "rfid_uid"
ATTR_PIN = "pin"
ATTR_ACTIVE = "active"
ATTR_VALID_FROM = "valid_from"
ATTR_VALID_UNTIL = "valid_until"

SERVICE_REGISTER_DOOR = "register_door"
SERVICE_REMOVE_DOOR = "remove_door"
SERVICE_REGISTER_USER = "register_user"
SERVICE_REMOVE_USER = "remove_user"
SERVICE_PULSE_UNLOCK = "pulse_unlock"
SERVICE_HOLD_UNLOCK = "hold_unlock"
SERVICE_CANCEL_HOLD = "cancel_hold"
SERVICE_RESYNC_DOOR = "resync_door"
SERVICE_SYNC_ALL = "sync_all"
SERVICE_REBOOT_DOOR = "reboot_door"
SERVICE_PUSH_SNAPSHOT = "push_snapshot"
SERVICE_PUSH_ALL_SNAPSHOTS = "push_all_snapshots"

LOCK_STATE_LOCKED = "locked"
LOCK_STATE_PULSE_ACTIVE = "pulse_active"
LOCK_STATE_HOLD_ACTIVE = "hold_active"
LOCK_STATE_DEGRADED = "degraded"
LOCK_STATE_UNKNOWN = "unknown"
