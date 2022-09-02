"""Elro Connects K1 device communication."""
from __future__ import annotations

import asyncio
import copy
from datetime import timedelta
import logging
from typing import Any

from elro.api import K1
from elro.command import (
    GET_ALL_EQUIPMENT_STATUS,
    GET_DEVICE_NAMES,
    SET_DEVICE_NAME,
    CommandAttributes,
)
from elro.device import (
    ALARM_CO,
    ALARM_FIRE,
    ALARM_HEAT,
    ALARM_SMOKE,
    ALARM_WATER,
    ATTR_DEVICE_STATE,
    ATTR_DEVICE_TYPE,
    STATE_UNKNOWN,
)
from elro.utils import update_state_data

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import (
    EVENT_DEVICE_REGISTRY_UPDATED,
    format_mac,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import CONF_CONNECTOR_ID, DEFAULT_INTERVAL, DOMAIN, ELRO_CONNECTS_NEW_DEVICE

MAX_RETRIES = 3

DEVICE_MODELS = {
    ALARM_CO: "CO alarm",
    ALARM_FIRE: "Fire alarm",
    ALARM_HEAT: "Heat alarm",
    ALARM_SMOKE: "Smoke alarm",
    ALARM_WATER: "Water alarm",
}


class ElroConnectsK1(DataUpdateCoordinator, K1):
    """Communicate with the Elro Connects K1 adapter and update the coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the K1 connector."""
        self.hass = hass
        self._entry = entry
        self._logger = logger

        self._connector_data: dict[int, dict] = {}
        self._api_lock = asyncio.Lock()
        self._connector_id = entry.data[CONF_CONNECTOR_ID]
        self._retry_count = 0

        self._device_registry_updated = hass.bus.async_listen(
            EVENT_DEVICE_REGISTRY_UPDATED, self._async_device_updated
        )

        DataUpdateCoordinator.__init__(
            self,
            hass,
            logger,
            name=self._connector_id,
            update_method=self._async_update_data,
            update_interval=timedelta(seconds=DEFAULT_INTERVAL),
        )
        K1.__init__(
            self,
            entry.data[CONF_HOST],
            entry.data[CONF_CONNECTOR_ID],
            entry.data[CONF_PORT],
            entry.data.get(CONF_API_KEY),
        )

    async def _async_update_data(self) -> dict[int, dict]:
        """Update coordinator data via API."""
        # get state from coordinator cash in case the current state is unknown
        coordinator_update: dict[int, dict] = copy.deepcopy(self.data or {})
        new_devices = False
        try:
            await self._async_fetch_connector_data()
            device_update = copy.deepcopy(self._connector_data)
            for device_id, device_data in device_update.items():
                if ATTR_DEVICE_STATE not in device_data:
                    # No valid device state, do not update
                    continue
                if device_id not in coordinator_update:
                    # new device discovered
                    new_devices = True
                    coordinator_update[device_id] = device_data
                elif device_data[ATTR_DEVICE_STATE] == STATE_UNKNOWN:
                    # do not process unknown state updates
                    continue
                else:
                    # full state update to coordinator device data
                    coordinator_update[device_id] = device_data

        except K1.K1ConnectionError as err:
            raise UpdateFailed(err) from err

        if new_devices:
            async_dispatcher_send(
                self.hass, ELRO_CONNECTS_NEW_DEVICE.format(self._entry.entry_id)
            )
        return coordinator_update

    async def _async_device_updated(self, event: Event) -> None:
        """Propagate name changes though the connector."""
        if (
            event.data["action"] != "update"
            or "name_by_user" not in event.data["changes"]
        ):
            # Ignore "create" action and other changes
            return

        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get(event.data["device_id"])
        device_unique_id: str = device_entry.identifiers.copy().pop()[1]
        mac_address = format_mac(self.connector_id[3:])
        if (
            (dr.CONNECTION_NETWORK_MAC, mac_address) in device_entry.identifiers
            or self._entry.entry_id not in device_entry.config_entries
        ):
            # Not a valid device name or not a related entry
            return
        device_id_str = device_unique_id[len(self.connector_id) + 1 :]
        device_id = int(device_id_str)
        if not self.connector_data or device_id not in self.connector_data:
            # the device is not in the connector data hence we cannot update it
            return False

        if device_entry.name != device_entry.name_by_user:
            await self.async_command(
                SET_DEVICE_NAME,
                device_ID=device_id,
                device_name=device_entry.name_by_user[:15]
                if len(device_entry.name_by_user) > 15
                else device_entry.name_by_user,
            )

    async def _async_fetch_connector_data(self) -> None:
        """Fetch new update from the K1 connector."""

        try:
            async with self._api_lock:
                new_data: dict[int, dict] = {}
                update_status = await self.async_process_command(
                    GET_ALL_EQUIPMENT_STATUS
                )
                new_data = update_status
                update_names = await self.async_process_command(GET_DEVICE_NAMES)
                update_state_data(new_data, update_names)
                self._retry_count = 0
                self._connector_data = new_data
        except K1.K1ConnectionError as err:
            self._retry_count += 1
            if not self._connector_data or self._retry_count >= MAX_RETRIES:
                raise K1.K1ConnectionError(err) from err

    async def async_command(
        self,
        command: CommandAttributes,
        **argv: int | str,
    ) -> dict[int, dict[str, Any]] | None:
        """Execute a synchronized command through the K1 connector."""
        async with self._api_lock:
            return await self.async_process_command(command, **argv)

    async def async_update_settings(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Process updated settings."""
        async with self._api_lock:
            await self.async_configure(
                entry.data[CONF_HOST],
                entry.data[CONF_PORT],
                entry.data.get(CONF_API_KEY),
            )

    @property
    def connector_data(self) -> dict[int, dict]:
        """Return the synced state."""
        return self._connector_data

    @property
    def connector_id(self) -> str:
        """Return the K1 connector ID."""
        return self._connector_id


class ElroConnectsEntity(CoordinatorEntity):
    """Defines a base entity for Elro Connects devices."""

    def __init__(
        self,
        elro_connects_api: ElroConnectsK1,
        entry: ConfigEntry,
        device_id: int,
        description: EntityDescription,
    ) -> None:
        """Initialize the Elro connects entity."""
        super().__init__(elro_connects_api)

        self.data: dict = elro_connects_api.connector_data[device_id]

        self._connector_id = elro_connects_api.connector_id
        self._device_id = device_id
        self._entry = entry
        self._attr_device_class = description.device_class
        self._attr_icon = description.icon
        self._attr_unique_id = f"{self._connector_id}-{device_id}-{description.key}"
        self.entity_description = description

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return (
            self.data[ATTR_NAME]
            if ATTR_NAME in self.data
            else self.entity_description.name
        )

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        self.data = self.coordinator.data[self._device_id]
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return info for device registry."""
        # connector
        device_registry = dr.async_get(self.hass)
        mac_address = format_mac(self._connector_id[3:])
        device_registry.async_get_or_create(
            model="K1 (SF40GA)",
            config_entry_id=self._entry.entry_id,
            identifiers={
                (dr.CONNECTION_NETWORK_MAC, mac_address),
            },
            manufacturer="Elro",
            name=f"Elro Connects K1 {self._connector_id}",
        )
        # sub device
        device_type = self.data[ATTR_DEVICE_TYPE]
        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._connector_id}_{self._device_id}")},
            manufacturer="Elro",
            model=DEVICE_MODELS[device_type]
            if device_type in DEVICE_MODELS
            else device_type,
            name=self.name,
            # Link to K1 connector
            via_device=(dr.CONNECTION_NETWORK_MAC, mac_address),
        )
        return device_info
