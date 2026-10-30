"""Base entity for the Elro Connects integration."""

from elro.device import (
    ALARM_CO,
    ALARM_FIRE,
    ALARM_HEAT,
    ALARM_SMOKE,
    ALARM_WATER,
    ATTR_DEVICE_TYPE,
)
from homeassistant.const import ATTR_NAME
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ElroConnectsCoordinator

DEVICE_MODELS = {
    ALARM_CO: "CO alarm",
    ALARM_FIRE: "Fire alarm",
    ALARM_HEAT: "Heat alarm",
    ALARM_SMOKE: "Smoke alarm",
    ALARM_WATER: "Water alarm",
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

        self.data: dict = coordinator.connector_data[device_id]

        self._connector_id = coordinator.connector_id
        self._device_id = device_id
        self._attr_unique_id = f"{self._connector_id}-{device_id}-{description.key}"
        self.entity_description = description

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fetch state from the device."""
        self.data = self.coordinator.data[self._device_id]
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Return info for device registry."""
        # connector
        device_registry = dr.async_get(self.hass)
        mac_address = format_mac(self._connector_id[3:])
        k1_device = device_registry.async_get_or_create(
            model="K1 (SF40GA)",
            config_entry_id=self.coordinator.config_entry.entry_id,
            identifiers={
                (dr.CONNECTION_NETWORK_MAC, mac_address),
            },
            manufacturer="Elro",
            name=f"Elro Connects K1 {self._connector_id}",
        )
        # sub device
        device_type = self.data[ATTR_DEVICE_TYPE]
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._connector_id}_{self._device_id}")},
            manufacturer="Elro",
            model=DEVICE_MODELS.get(device_type, device_type),
            name=self.data.get(ATTR_NAME, None),
            # Link to K1 connector
            via_device_id=k1_device.id,
        )
