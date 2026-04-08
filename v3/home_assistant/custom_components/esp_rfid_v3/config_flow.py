"""Config flow for ESP-RFID V3."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_POLL_INTERVAL_SECONDS,
    CONF_SITE_NAME,
    DEFAULT_POLL_INTERVAL_SECONDS,
    DEFAULT_SITE_NAME,
    DOMAIN,
)


class EspRfidV3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ESP-RFID V3."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_SITE_NAME],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_SITE_NAME, default=DEFAULT_SITE_NAME): str,
                vol.Required(
                    CONF_POLL_INTERVAL_SECONDS,
                    default=DEFAULT_POLL_INTERVAL_SECONDS,
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)
