"""ESP-RFID V3 integration."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EspRfidV3ApiClientFactory
from .const import (
    ATTR_ALLOW_HOLD_OPEN,
    ATTR_ACTIVE,
    ATTR_API_TOKEN,
    ATTR_BASE_URL,
    ATTR_DEVICE_ID,
    ATTR_DOOR_IDS,
    ATTR_ENABLED,
    ATTR_NAME,
    ATTR_PIN,
    ATTR_REASON,
    ATTR_RFID_UID,
    ATTR_USER_ID,
    ATTR_VALID_FROM,
    ATTR_VALID_UNTIL,
    CONF_SITE_NAME,
    DEFAULT_SITE_NAME,
    DOMAIN,
    PLATFORMS,
    SERVICE_CANCEL_HOLD,
    SERVICE_HOLD_UNLOCK,
    SERVICE_PULSE_UNLOCK,
    SERVICE_PUSH_ALL_SNAPSHOTS,
    SERVICE_PUSH_SNAPSHOT,
    SERVICE_REBOOT_DOOR,
    SERVICE_REGISTER_DOOR,
    SERVICE_REGISTER_USER,
    SERVICE_REMOVE_DOOR,
    SERVICE_REMOVE_USER,
    SERVICE_RESYNC_DOOR,
    SERVICE_SYNC_ALL,
)
from .coordinator import EspRfidV3Coordinator
from .models import AccessUser, DoorNodeConfig, EspRfidV3RuntimeData
from .security import derive_pin_material, derive_tag_digest, normalize_user_id
from .snapshot import build_door_snapshot
from .storage import EspRfidV3Store


def _get_runtime(hass: HomeAssistant) -> EspRfidV3RuntimeData:
    """Return the current runtime data."""
    runtime_map: dict[str, EspRfidV3RuntimeData] = hass.data.get(DOMAIN, {})
    if not runtime_map:
        raise HomeAssistantError("ESP-RFID V3 is not configured")

    return next(iter(runtime_map.values()))


def _normalize_base_url(base_url: str) -> str:
    """Normalize and validate a door base URL."""
    normalized = base_url.strip().rstrip("/")
    parsed = urlparse(normalized)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HomeAssistantError(
            "Door base URL must be a full http:// or https:// address"
        )

    hostname = parsed.hostname or ""
    is_loopback = hostname.lower() == "localhost"
    if hostname:
        try:
            is_loopback = is_loopback or ip_address(hostname).is_loopback
        except ValueError:
            pass

    if is_loopback:
        raise HomeAssistantError(
            "Door base URL cannot use localhost or 127.0.0.1 from Home Assistant. "
            "Use the door node's real network address. In the local dev stack, use "
            "http://esp_rfid_v3_frontdoor:18101 or http://esp_rfid_v3_backdoor:18102."
        )

    return normalized


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})

    if hass.services.has_service(DOMAIN, SERVICE_REGISTER_DOOR):
        return True

    async def async_push_snapshot_for_door(
        runtime: EspRfidV3RuntimeData,
        device_id: str,
    ) -> None:
        users = await runtime.store.async_get_users()
        door = runtime.coordinator.get_door(device_id)
        snapshot = build_door_snapshot(
            site_name=runtime.site_name,
            door=door,
            users=users,
        )
        await runtime.coordinator.async_push_snapshot(device_id, snapshot.to_dict())

    async def async_handle_register_door(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        door = DoorNodeConfig(
            device_id=call.data[ATTR_DEVICE_ID],
            name=call.data[ATTR_NAME],
            base_url=_normalize_base_url(call.data[ATTR_BASE_URL]),
            api_token=call.data[ATTR_API_TOKEN],
            allow_hold_open=call.data[ATTR_ALLOW_HOLD_OPEN],
            enabled=call.data[ATTR_ENABLED],
        )
        await runtime.store.async_upsert_door(door)
        await hass.config_entries.async_reload(runtime.entry_id)

    async def async_handle_remove_door(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        await runtime.store.async_remove_door(call.data[ATTR_DEVICE_ID])
        await hass.config_entries.async_reload(runtime.entry_id)

    async def async_handle_register_user(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        site_secret = await runtime.store.async_get_site_secret()
        user_id = normalize_user_id(call.data[ATTR_USER_ID])
        if not user_id:
            raise HomeAssistantError("User id must contain at least one valid character")

        if not call.data.get(ATTR_RFID_UID) and not call.data.get(ATTR_PIN):
            raise HomeAssistantError("A user must have at least one credential: RFID UID or PIN")

        tag_digest = None
        if ATTR_RFID_UID in call.data and call.data[ATTR_RFID_UID]:
            tag_digest = derive_tag_digest(site_secret, call.data[ATTR_RFID_UID])

        pin_hash = None
        pin_salt = None
        pin_iterations = None
        if ATTR_PIN in call.data and call.data[ATTR_PIN]:
            pin_hash, pin_salt, pin_iterations = derive_pin_material(call.data[ATTR_PIN])

        known_doors = set(runtime.coordinator.doors)
        door_ids = sorted({str(door_id) for door_id in call.data[ATTR_DOOR_IDS]})
        if not door_ids:
            raise HomeAssistantError("A user must be assigned to at least one door")
        unknown_doors = sorted(set(door_ids) - known_doors)
        if unknown_doors:
            raise HomeAssistantError(
                f"Unknown door ids: {', '.join(unknown_doors)}"
            )

        user = AccessUser(
            user_id=user_id,
            name=call.data[ATTR_NAME],
            door_ids=door_ids,
            active=call.data[ATTR_ACTIVE],
            tag_digest=tag_digest,
            pin_hash=pin_hash,
            pin_salt=pin_salt,
            pin_iterations=pin_iterations,
            valid_from=call.data.get(ATTR_VALID_FROM),
            valid_until=call.data.get(ATTR_VALID_UNTIL),
        )
        await runtime.store.async_upsert_user(user)
        await runtime.coordinator.async_request_refresh()

    async def async_handle_remove_user(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        user_id = normalize_user_id(call.data[ATTR_USER_ID])
        await runtime.store.async_remove_user(user_id)
        await runtime.coordinator.async_request_refresh()

    async def async_handle_push_snapshot(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        await async_push_snapshot_for_door(runtime, call.data[ATTR_DEVICE_ID])

    async def async_handle_push_all_snapshots(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        for device_id in runtime.coordinator.doors:
            await async_push_snapshot_for_door(runtime, device_id)

    async def async_handle_command(call: ServiceCall, command: str) -> None:
        runtime = _get_runtime(hass)
        payload: dict[str, Any] = {}
        if ATTR_REASON in call.data:
            payload[ATTR_REASON] = call.data[ATTR_REASON]
        await runtime.coordinator.async_send_command(call.data[ATTR_DEVICE_ID], command, payload)

    async def async_handle_sync_all(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        await runtime.coordinator.async_sync_all()

    async def async_handle_pulse_unlock(call: ServiceCall) -> None:
        await async_handle_command(call, "pulse_unlock")

    async def async_handle_hold_unlock(call: ServiceCall) -> None:
        await async_handle_command(call, "hold_unlock")

    async def async_handle_cancel_hold(call: ServiceCall) -> None:
        await async_handle_command(call, "cancel_hold")

    async def async_handle_resync(call: ServiceCall) -> None:
        await async_handle_command(call, "resync")

    async def async_handle_reboot(call: ServiceCall) -> None:
        await async_handle_command(call, "reboot")

    hass.services.async_register(
        DOMAIN,
        SERVICE_REGISTER_DOOR,
        async_handle_register_door,
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE_ID): str,
                vol.Required(ATTR_NAME): str,
                vol.Required(ATTR_BASE_URL): str,
                vol.Required(ATTR_API_TOKEN): str,
                vol.Optional(ATTR_ALLOW_HOLD_OPEN, default=True): bool,
                vol.Optional(ATTR_ENABLED, default=True): bool,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_DOOR,
        async_handle_remove_door,
        schema=vol.Schema({vol.Required(ATTR_DEVICE_ID): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REGISTER_USER,
        async_handle_register_user,
        schema=vol.Schema(
            {
                vol.Required(ATTR_USER_ID): str,
                vol.Required(ATTR_NAME): str,
                vol.Required(ATTR_DOOR_IDS): [str],
                vol.Optional(ATTR_RFID_UID): str,
                vol.Optional(ATTR_PIN): str,
                vol.Optional(ATTR_ACTIVE, default=True): bool,
                vol.Optional(ATTR_VALID_FROM): str,
                vol.Optional(ATTR_VALID_UNTIL): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_USER,
        async_handle_remove_user,
        schema=vol.Schema({vol.Required(ATTR_USER_ID): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PULSE_UNLOCK,
        async_handle_pulse_unlock,
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE_ID): str,
                vol.Optional(ATTR_REASON, default="home_assistant"): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_HOLD_UNLOCK,
        async_handle_hold_unlock,
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE_ID): str,
                vol.Optional(ATTR_REASON, default="home_assistant"): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_HOLD,
        async_handle_cancel_hold,
        schema=vol.Schema(
            {
                vol.Required(ATTR_DEVICE_ID): str,
                vol.Optional(ATTR_REASON, default="home_assistant"): str,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESYNC_DOOR,
        async_handle_resync,
        schema=vol.Schema({vol.Required(ATTR_DEVICE_ID): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REBOOT_DOOR,
        async_handle_reboot,
        schema=vol.Schema({vol.Required(ATTR_DEVICE_ID): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PUSH_SNAPSHOT,
        async_handle_push_snapshot,
        schema=vol.Schema({vol.Required(ATTR_DEVICE_ID): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_PUSH_ALL_SNAPSHOTS,
        async_handle_push_all_snapshots,
        schema=vol.Schema({}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_ALL,
        async_handle_sync_all,
        schema=vol.Schema({}),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ESP-RFID V3 from a config entry."""
    store = EspRfidV3Store(hass)
    api_factory = EspRfidV3ApiClientFactory(async_get_clientsession(hass))
    coordinator = EspRfidV3Coordinator(hass, entry, store, api_factory)
    await coordinator.async_config_entry_first_refresh()

    runtime = EspRfidV3RuntimeData(
        entry_id=entry.entry_id,
        site_name=str(entry.data.get(CONF_SITE_NAME, DEFAULT_SITE_NAME)),
        store=store,
        coordinator=coordinator,
    )
    entry.runtime_data = runtime
    hass.data[DOMAIN][entry.entry_id] = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
