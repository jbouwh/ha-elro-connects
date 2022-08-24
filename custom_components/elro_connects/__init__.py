"""The Elro Connects integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .device import ElroConnectsK1

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SIREN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Elro Connects from a config entry."""

    elro_connects_api = ElroConnectsK1(hass, _LOGGER, entry)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = elro_connects_api

    await elro_connects_api.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(
        entry.add_update_listener(elro_connects_api.async_update_settings)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    elro_connects_api: ElroConnectsK1 = hass.data[DOMAIN][entry.entry_id]
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await elro_connects_api.async_disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow manual removal of a device if not in use."""
    elro_connects_api: ElroConnectsK1 = hass.data[DOMAIN][entry.entry_id]
    device_unique_id: str = device_entry.identifiers.copy().pop()[1]
    device_id_str = device_unique_id[len(elro_connects_api.connector_id) + 1 :]
    if not device_id_str:
        return False
    device_id = int(device_id_str)
    # Do not remove if the device_id is in the connector_data
    if (
        elro_connects_api.connector_data
        and device_id in elro_connects_api.connector_data
    ):
        return False
    return True
