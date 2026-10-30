"""Elro Connects K1 data update coordinator."""

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
from elro.device import ATTR_DEVICE_STATE, STATE_UNKNOWN
from elro.utils import update_state_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_CONNECTOR_ID, DEFAULT_INTERVAL, DOMAIN, ELRO_CONNECTS_NEW_DEVICE

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3

type ElroConnectsConfigEntry = ConfigEntry[ElroConnectsCoordinator]


class ElroConnectsCoordinator(DataUpdateCoordinator[dict[int, dict]]):
    """Communicate with the Elro Connects K1 adapter and update the coordinator."""

    config_entry: ElroConnectsConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ElroConnectsConfigEntry) -> None:
        """Initialize the K1 connector."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.data[CONF_CONNECTOR_ID],
            update_interval=timedelta(seconds=DEFAULT_INTERVAL),
        )
        self._connector_data: dict[int, dict] = {}
        self._api_lock = asyncio.Lock()
        self._connector_id: str = entry.data[CONF_CONNECTOR_ID]
        self.hub_identifier = (DOMAIN, self._connector_id)
        self.mac_address = format_mac(self._connector_id[3:])
        self._retry_count = 0
        self.api = K1(
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
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        if new_devices:
            async_dispatcher_send(
                self.hass, ELRO_CONNECTS_NEW_DEVICE.format(self.config_entry.entry_id)
            )
        return coordinator_update

    async def async_device_updated(self, event: Event) -> None:
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
        if (
            self.hub_identifier in device_entry.identifiers
            or self.config_entry.entry_id not in device_entry.config_entries
        ):
            # Not a valid device name or not a related entry
            return
        device_id_str = device_unique_id[len(self.connector_id) + 1 :]
        device_id = int(device_id_str)
        if not self.connector_data or device_id not in self.connector_data:
            # the device is not in the connector data hence we cannot update it
            return

        if device_entry.name != device_entry.name_by_user:
            await self.async_command(
                SET_DEVICE_NAME,
                device_ID=device_id,
                device_name=(
                    device_entry.name_by_user[:15]
                    if len(device_entry.name_by_user) > 15
                    else device_entry.name_by_user
                ),
            )

    async def _async_fetch_connector_data(self) -> None:
        """Fetch new update from the K1 connector."""

        try:
            async with self._api_lock:
                new_data: dict[int, dict] = await self.api.async_process_command(
                    GET_ALL_EQUIPMENT_STATUS
                )
                update_names = await self.api.async_process_command(GET_DEVICE_NAMES)
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
            try:
                return await self.api.async_process_command(command, **argv)
            except K1.K1ConnectionError as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="command_failed",
                    translation_placeholders={"error": str(err)},
                ) from err

    async def async_disconnect(self) -> None:
        """Disconnect from the K1 connector."""
        async with self._api_lock:
            await self.api.async_disconnect()

    @property
    def connector_data(self) -> dict[int, dict]:
        """Return the synced state."""
        return self._connector_data

    @property
    def connector_id(self) -> str:
        """Return the K1 connector ID."""
        return self._connector_id
