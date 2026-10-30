"""The Elro Connects switch platform."""

from dataclasses import dataclass
import logging

from elro.command import SOCKET_OFF, SOCKET_ON, CommandAttributes
from elro.device import ATTR_DEVICE_VALUE, DEVICE_VALUE_OFF, DEVICE_VALUE_ON, SOCKET
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ElroConnectsConfigEntry
from .entity import ElroConnectsEntity
from .helpers import async_set_up_discovery_helper


@dataclass
class ElroSwitchEntityDescription(SwitchEntityDescription):
    """A class that describes elro siren entities."""

    turn_on: CommandAttributes | None = None
    turn_off: CommandAttributes | None = None


_LOGGER = logging.getLogger(__name__)

SWITCH_DEVICE_TYPES = {
    SOCKET: (
        ElroSwitchEntityDescription(
            key=SOCKET,
            translation_key="socket",
            device_class=SwitchDeviceClass.OUTLET,
            turn_on=SOCKET_ON,
            turn_off=SOCKET_OFF,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ElroConnectsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_set_up_discovery_helper(
        hass,
        ElroConnectsSwitch,
        config_entry,
        SWITCH_DEVICE_TYPES,
        async_add_entities,
    )


class ElroConnectsSwitch(ElroConnectsEntity, SwitchEntity):
    """Elro Connects Fire Alarm Entity."""

    entity_description: ElroSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the socket is on or none if the value is unknown."""
        if self.data[ATTR_DEVICE_VALUE] not in (DEVICE_VALUE_OFF, DEVICE_VALUE_ON):
            return None
        return self.data[ATTR_DEVICE_VALUE] == DEVICE_VALUE_ON

    async def async_turn_on(self, **kwargs) -> None:
        """Turn switch on."""
        _LOGGER.debug("Sending turn_on request for entity %s", self.entity_id)
        await self.coordinator.async_command(
            self.entity_description.turn_on, device_ID=self._device_id
        )

        self.data[ATTR_DEVICE_VALUE] = DEVICE_VALUE_ON
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn switch off."""
        _LOGGER.debug("Sending turn_off request for entity %s", self.entity_id)
        await self.coordinator.async_command(
            self.entity_description.turn_off, device_ID=self._device_id
        )

        self.data[ATTR_DEVICE_VALUE] = DEVICE_VALUE_OFF
        self.async_write_ha_state()
