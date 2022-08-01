"""Config flow for Elro Connects integration."""
from __future__ import annotations

import logging
from typing import Any

from elro.api import K1
from elro.auth import ElroConnectsConnector, ElroConnectsSession
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import CONF_CONNECTOR_ID, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

ELRO_CONNECTS_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_CONNECTOR_ID): str,
        vol.Optional(CONF_API_KEY): str,
    }
)

TITLE = "Elro Connects K1 Connector"


class K1ConnectionTest:
    """Elro Connects K1 connection test."""

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def async_try_connection(
        self, connector_id: str, port: int, api_key: str | None = None
    ) -> bool:
        """Test if we can authenticate with the host."""
        connector = K1(self.host, connector_id, port, api_key)
        try:
            await connector.async_connect()
        except K1.K1ConnectionError:
            return False
        finally:
            await connector.async_disconnect()
        return True


async def async_validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    connectors: list[ElroConnectsConnector] = []
    info = {}
    info.update(data)

    # get cloud info if username and password are given
    if info.get(CONF_USERNAME) and info.get(CONF_PASSWORD):
        try:
            session = ElroConnectsSession()
            await session.async_login(info[CONF_USERNAME], info[CONF_PASSWORD])
            connectors = await session.async_get_connectors()
        except Exception as exp:  # pylint: disable=broad-except
            raise CannotConnect from exp

    # Add api key from cloud and perform connection test
    while connectors:
        connector = connectors.pop(0)
        if CONF_CONNECTOR_ID in info:
            # Match connector ID to find the key
            if info[CONF_CONNECTOR_ID] == connector["dev_id"]:
                info[CONF_API_KEY] = connector["ctrl_key"]
        else:
            # Use first connector found
            info[CONF_API_KEY] = connector["ctrl_key"]
            info[CONF_CONNECTOR_ID] = connector["dev_id"]
            continue

    hub = K1ConnectionTest(data["host"])
    if CONF_CONNECTOR_ID not in info or not await hub.async_try_connection(
        info[CONF_CONNECTOR_ID], data[CONF_PORT], info.get(CONF_API_KEY)
    ):
        raise CannotConnect

    return info


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Elro Connects."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Handle configuring options."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=ELRO_CONNECTS_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await async_validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(info[CONF_CONNECTOR_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=TITLE, data=info)

        return self.async_show_form(
            step_id="user", data_schema=ELRO_CONNECTS_DATA_SCHEMA, errors=errors
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Manage the options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage configuration options."""
        errors = {}
        entry_data = self.config_entry.data
        if user_input is not None:
            changed_input = {}
            changed_input.update(user_input)
            try:
                info = await async_validate_input(self.hass, changed_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=info
                )
                return self.async_create_entry(title="", data=changed_input)

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry_data.get(CONF_HOST)): str,
                    vol.Required(CONF_PORT, default=entry_data.get(CONF_PORT)): cv.port,
                    vol.Optional(
                        CONF_USERNAME,
                        description={"suggested_value": entry_data.get(CONF_USERNAME)},
                    ): str,
                    vol.Optional(
                        CONF_PASSWORD,
                        description={"suggested_value": entry_data.get(CONF_PASSWORD)},
                    ): str,
                    vol.Optional(
                        CONF_CONNECTOR_ID,
                        description={
                            "suggested_value": entry_data.get(CONF_CONNECTOR_ID)
                        },
                    ): str,
                    vol.Optional(
                        CONF_API_KEY,
                        description={"suggested_value": entry_data.get(CONF_API_KEY)},
                    ): str,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
