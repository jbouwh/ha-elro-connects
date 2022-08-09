"""Elro Connects K1 device communication."""
from __future__ import annotations

import asyncio
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
    ATTR_DEVICE_TYPE,
)
from elro.utils import update_state_data

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import EVENT_DEVICE_REGISTRY_UPDATED
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import CONF_CONNECTOR_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3

DEVICE_MODELS = {
    ALARM_CO: "CO alarm",
    ALARM_FIRE: "Fire alarm",
    ALARM_HEAT: "Heat alarm",
    ALARM_SMOKE: "Smoke alarm",
    ALARM_WATER: "Water alarm",
}


class ElroConnectsK1(K1):
    """Communicate with the Elro Connects K1 adapter."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the K1 connector."""
        self._coordinator = coordinator
        self.hass = coordinator.hass
        self._entry = entry

        self._data: dict[int, dict] = {}
        self._api_lock = asyncio.Lock()
        self._connector_id = entry.data[CONF_CONNECTOR_ID]
        self._retry_count = 0

        self._device_registry_updated = coordinator.hass.bus.async_listen(
            EVENT_DEVICE_REGISTRY_UPDATED, self._async_device_updated
        )

        K1.__init__(
            self,
            entry.data[CONF_HOST],
            entry.data[CONF_CONNECTOR_ID],
            entry.data[CONF_PORT],
            entry.data.get(CONF_API_KEY),
        )

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
        device_id_str = device_unique_id[len(self.connector_id) + 1 :]
        if self._entry.entry_id not in device_entry.config_entries or not device_id_str:
            # Not a valid device name or not a related entry
            return
        device_id = int(device_id_str)
        if device_id not in self.data:
            # the device is not in the coordinator data hence we cannot update it
            return False

        if device_entry.name != device_entry.name_by_user:
            await self.async_command(
                SET_DEVICE_NAME,
                device_ID=device_id,
                device_name=device_entry.name_by_user[:15]
                if len(device_entry.name_by_user) > 15
                else device_entry.name_by_user,
            )

    async def async_update(self) -> None:
        """Synchronize with the K1 connector."""

        async def _async_update() -> None:
            new_data: dict[int, dict] = {}
            update_status = await self.async_process_command(GET_ALL_EQUIPMENT_STATUS)
            new_data = update_status
            update_names = await self.async_process_command(GET_DEVICE_NAMES)
            update_state_data(new_data, update_names)
            self._retry_count = 0
            self._data = new_data

        try:
            async with self._api_lock:
                await self.hass.async_add_job(_async_update())
        except K1.K1ConnectionError as err:
            self._retry_count += 1
            if not self._data or self._retry_count >= MAX_RETRIES:
                raise K1.K1ConnectionError(err) from err

    async def async_command(
        self,
        command: CommandAttributes,
        **argv: int | str,
    ) -> dict[int, dict[str, Any]] | None:
        """Execute a synchronized command through the K1 connector."""
        async with self._api_lock:
            return self.hass.async_add_job(self.async_process_command(command, **argv))

    async def async_update_settings(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Process updated settings."""
        async with self._api_lock:
            hass.async_create_task(
                self.async_configure(
                    entry.data[CONF_HOST],
                    entry.data[CONF_PORT],
                    entry.data.get(CONF_API_KEY),
                )
            )

    @property
    def data(self) -> dict[int, dict]:
        """Return the synced state."""
        return self._data

    @property
    def connector_id(self) -> str:
        """Return the K1 connector ID."""
        return self._connector_id

    @property
    def coordinator(self) -> DataUpdateCoordinator:
        """Return the data update coordinator."""
        return self._coordinator


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
        super().__init__(elro_connects_api.coordinator)

        self.data: dict = elro_connects_api.coordinator.data[device_id]

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
        device_registry.async_get_or_create(
            model="K1 (SF40GA)",
            config_entry_id=self._entry.entry_id,
            identifiers={(DOMAIN, self._connector_id)},
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
            via_device=(DOMAIN, self._connector_id),
        )
        return device_info
