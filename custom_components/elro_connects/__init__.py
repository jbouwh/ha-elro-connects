"""The Elro Connects integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    EVENT_DEVICE_REGISTRY_UPDATED,
    DeviceEntry,
    format_mac,
)

from .coordinator import ElroConnectsConfigEntry, ElroConnectsCoordinator

_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SIREN, Platform.SWITCH]


async def async_setup_entry(
    hass: HomeAssistant, entry: ElroConnectsConfigEntry
) -> bool:
    """Set up Elro Connects from a config entry."""
    coordinator = ElroConnectsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(
        hass.bus.async_listen(
            EVENT_DEVICE_REGISTRY_UPDATED, coordinator.async_device_updated
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ElroConnectsConfigEntry
) -> None:
    """Reload the entry when the settings are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: ElroConnectsConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, _PLATFORMS):
        await entry.runtime_data.async_disconnect()

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ElroConnectsConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow manual removal of a device if not in use."""
    coordinator = entry.runtime_data
    device_unique_id: str = device_entry.identifiers.copy().pop()[1]
    mac_address = format_mac(coordinator.connector_id[3:])
    if mac_address == device_unique_id:
        return False
    device_id_str = device_unique_id[len(coordinator.connector_id) + 1 :]
    device_id = int(device_id_str)
    # Do not remove if the device_id is in the connector_data
    return not (coordinator.connector_data and device_id in coordinator.connector_data)
