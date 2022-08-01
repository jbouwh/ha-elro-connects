"""Elro Connects K1 device communication."""
from __future__ import annotations

import logging

from elro.api import K1
from elro.command import GET_ALL_EQUIPMENT_STATUS, GET_DEVICE_NAMES
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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
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
        self._data: dict[int, dict] = {}
        self._connector_id = entry.data[CONF_CONNECTOR_ID]
        self._retry_count = 0

        K1.__init__(
            self,
            entry.data[CONF_HOST],
            entry.data[CONF_CONNECTOR_ID],
            entry.data[CONF_PORT],
        )

    async def async_update(self) -> None:
        """Synchronize with the K1 connector."""
        new_data: dict[int, dict] = {}
        try:
            update_status = await self.async_process_command(GET_ALL_EQUIPMENT_STATUS)
            new_data = update_status
            update_names = await self.async_process_command(GET_DEVICE_NAMES)
            update_state_data(new_data, update_names)
            self._retry_count = 0
            self._data = new_data
        except K1.K1ConnectionError as err:
            self._retry_count += 1
            if not self._data or self._retry_count >= MAX_RETRIES:
                raise K1.K1ConnectionError(err) from err

    async def async_update_settings(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Process updated settings."""
        await self.async_configure(
            entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data.get(CONF_API_KEY)
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
        k1_device = device_registry.async_get_or_create(
            model="K1 (SF40GA)",
            config_entry_id=self._entry.entry_id,
            identifiers={(DOMAIN, self._connector_id)},
            manufacturer="Elro",
            name="Elro Connects K1 connector",
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
            via_device=(DOMAIN, k1_device.id),
        )
        return device_info
