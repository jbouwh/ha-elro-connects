"""The Elro Connects integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import (
    EVENT_DEVICE_REGISTRY_UPDATED,
    DeviceEntry,
)

from .coordinator import ElroConnectsConfigEntry, ElroConnectsCoordinator

_PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SIREN,
    Platform.SWITCH,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ElroConnectsConfigEntry
) -> bool:
    """Set up Elro Connects from a config entry."""
    coordinator = ElroConnectsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # The K1 connector is the hub the devices are linked to
    device_registry = dr.async_get(hass)
    mac_connection = (dr.CONNECTION_NETWORK_MAC, coordinator.mac_address)
    if hub := device_registry.async_get_device(identifiers={mac_connection}):
        # Migrate the hub that used the MAC address as identifier
        device_registry.async_update_device(
            hub.id, new_identifiers={coordinator.hub_identifier}
        )
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={coordinator.hub_identifier},
        connections={mac_connection},
        manufacturer="Elro",
        model="K1 (SF40GA)",
        name=f"Elro Connects K1 {coordinator.connector_id}",
    )

    entry.async_on_unload(
        hass.bus.async_listen(
            EVENT_DEVICE_REGISTRY_UPDATED, coordinator.async_device_updated
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_migrate_entry(
    hass: HomeAssistant, entry: ElroConnectsConfigEntry
) -> bool:
    """Migrate an old config entry."""
    if entry.minor_version < 2:
        # The options duplicated the data, the options flow was replaced by a
        # reconfigure flow
        hass.config_entries.async_update_entry(entry, options={}, minor_version=2)
    return True


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
    if coordinator.hub_identifier in device_entry.identifiers:
        return False
    device_unique_id: str = device_entry.identifiers.copy().pop()[1]
    device_id_str = device_unique_id[len(coordinator.connector_id) + 1 :]
    device_id = int(device_id_str)
    # Do not remove if the device_id is in the connector_data
    return not (coordinator.connector_data and device_id in coordinator.connector_data)
