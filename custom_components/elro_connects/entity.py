"""Base entity for the Elro Connects integration."""

from elro.device import (
    ALARM_CO,
    ALARM_FIRE,
    ALARM_HEAT,
    ALARM_SMOKE,
    ALARM_WATER,
    ATTR_DEVICE_STATE,
    ATTR_DEVICE_TYPE,
    DOOR_WINDOW_SENSOR,
    STATES_OFFLINE,
)
from homeassistant.const import ATTR_NAME
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ALARM_GAS, DOMAIN, TEMPERATURE_SENSOR
from .coordinator import DeviceData, ElroConnectsCoordinator

DEVICE_MODELS = {
    ALARM_CO: "CO alarm",
    ALARM_FIRE: "Fire alarm",
    ALARM_HEAT: "Heat alarm",
    ALARM_SMOKE: "Smoke alarm",
    ALARM_WATER: "Water alarm",
    ALARM_GAS: "Gas alarm",
    DOOR_WINDOW_SENSOR: "Door/window sensor",
    TEMPERATURE_SENSOR: "Temperature sensor",
}


class ElroConnectsEntity(CoordinatorEntity[ElroConnectsCoordinator]):
    """Defines a base entity for Elro Connects devices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElroConnectsCoordinator,
        device_id: int,
        description: EntityDescription,
    ) -> None:
        """Initialize the Elro connects entity."""
        super().__init__(coordinator)

        self.data: DeviceData = coordinator.connector_data[device_id]

        self._connector_id = coordinator.connector_id
        self._device_id = device_id
        self._attr_unique_id = f"{self._connector_id}-{device_id}-{description.key}"
        self.entity_description = description

    @property
    def available(self) -> bool:
        """Return if the connector can be reached and the device is online."""
        return (
            super().available
            and bool(self.data)
            and self.data[ATTR_DEVICE_STATE] not in STATES_OFFLINE
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch state from the device."""
        self.data = self.coordinator.data[self._device_id]
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return info for device registry."""
        device_type = self.data[ATTR_DEVICE_TYPE]
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._connector_id}_{self._device_id}")},
            manufacturer="Elro",
            model=DEVICE_MODELS.get(device_type, device_type),
            name=self.data.get(ATTR_NAME, None),
            # Link to K1 connector
            via_device=self.coordinator.hub_identifier,
        )
