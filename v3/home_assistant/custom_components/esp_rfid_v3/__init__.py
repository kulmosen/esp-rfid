"""ESP-RFID V3 integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EspRfidV3ApiClientFactory
from .const import (
    ATTR_ALLOW_HOLD_OPEN,
    ATTR_API_TOKEN,
    ATTR_BASE_URL,
    ATTR_DEVICE_ID,
    ATTR_ENABLED,
    ATTR_NAME,
    ATTR_REASON,
    CONF_SITE_NAME,
    DEFAULT_SITE_NAME,
    DOMAIN,
    PLATFORMS,
    SERVICE_CANCEL_HOLD,
    SERVICE_HOLD_UNLOCK,
    SERVICE_PULSE_UNLOCK,
    SERVICE_REBOOT_DOOR,
    SERVICE_REGISTER_DOOR,
    SERVICE_REMOVE_DOOR,
    SERVICE_RESYNC_DOOR,
    SERVICE_SYNC_ALL,
)
from .coordinator import EspRfidV3Coordinator
from .models import DoorNodeConfig, EspRfidV3RuntimeData
from .storage import EspRfidV3Store


def _get_runtime(hass: HomeAssistant) -> EspRfidV3RuntimeData:
    """Return the current runtime data."""
    runtime_map: dict[str, EspRfidV3RuntimeData] = hass.data.get(DOMAIN, {})
    if not runtime_map:
        raise HomeAssistantError("ESP-RFID V3 is not configured")

    return next(iter(runtime_map.values()))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})

    if hass.services.has_service(DOMAIN, SERVICE_REGISTER_DOOR):
        return True

    async def async_handle_register_door(call: ServiceCall) -> None:
        runtime = _get_runtime(hass)
        door = DoorNodeConfig(
            device_id=call.data[ATTR_DEVICE_ID],
            name=call.data[ATTR_NAME],
            base_url=call.data[ATTR_BASE_URL],
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
