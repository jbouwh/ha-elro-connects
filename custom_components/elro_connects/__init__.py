"""The Elro Connects integration."""
from __future__ import annotations

import copy
from datetime import timedelta
import logging

from elro.api import K1
from elro.device import ATTR_DEVICE_STATE, STATE_UNKNOWN

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_RELOAD, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_INTERVAL, DOMAIN
from .device import ElroConnectsK1

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SIREN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Elro Connects from a config entry."""

    current_device_set: set | None = None

    async def _async_update_data() -> dict[int, dict]:
        """Update data via API."""
        nonlocal current_device_set
        # get state from coordinator cash in case the current state is unknown
        coordinator_update: dict[int, dict] = copy.deepcopy(coordinator.data or {})
        # set initial state to unknown
        for device_id, state_base in coordinator_update.items():
            state_base[ATTR_DEVICE_STATE] = STATE_UNKNOWN
        try:
            await elro_connects_api.async_update()
            device_update = copy.deepcopy(elro_connects_api.data)
            for device_id, device_data in device_update.items():
                if ATTR_DEVICE_STATE not in device_data:
                    # Unlink entry without device state
                    continue
                if device_id not in coordinator_update:
                    # new device, or known state
                    coordinator_update[device_id] = device_data
                elif device_data[ATTR_DEVICE_STATE] == STATE_UNKNOWN:
                    # do not process unknown state updates
                    continue
                else:
                    # update full state
                    coordinator_update[device_id] = device_data

        except K1.K1ConnectionError as err:
            raise UpdateFailed(err) from err
        new_set = set(elro_connects_api.data.keys())
        if current_device_set is None:
            current_device_set = new_set
        if new_set - current_device_set:
            current_device_set = new_set
            # New devices discovered, trigger a reload
            await hass.services.async_call(
                DOMAIN,
                SERVICE_RELOAD,
                {},
                blocking=False,
            )
        return coordinator_update

    async def async_reload(call: ServiceCall) -> None:
        """Reload the integration."""
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN.title(),
        update_method=_async_update_data,
        update_interval=timedelta(seconds=DEFAULT_INTERVAL),
    )
    elro_connects_api = ElroConnectsK1(
        coordinator,
        entry,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = elro_connects_api

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    entry.async_on_unload(
        entry.add_update_listener(elro_connects_api.async_update_settings)
    )
    hass.helpers.service.async_register_admin_service(
        DOMAIN, SERVICE_RELOAD, async_reload
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
    if device_id in elro_connects_api.data:
        return False
    return True
