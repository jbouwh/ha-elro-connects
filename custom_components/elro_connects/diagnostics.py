"""Diagnostics support for Elro Connects."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_CONNECTOR_ID
from .coordinator import ElroConnectsConfigEntry

TO_REDACT = {CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME}


def _mask_connector_id(data: dict[str, Any]) -> dict[str, Any]:
    """Mask the device specific part of the MAC address in the connector ID."""
    connector_id: str = data[CONF_CONNECTOR_ID]
    # The connector ID is ST_ followed by the MAC address, keep the vendor part
    return {**data, CONF_CONNECTOR_ID: connector_id[:9] + "*" * len(connector_id[9:])}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ElroConnectsConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": _mask_connector_id(async_redact_data(entry.data, TO_REDACT)),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception),
        },
        # The raw device data as reported by the connector
        "connector_data": coordinator.connector_data,
        # The device data used by the entities
        "data": coordinator.data,
    }
