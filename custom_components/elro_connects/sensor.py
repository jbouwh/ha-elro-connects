"""The Elro Connects sensor platform."""

from dataclasses import dataclass
import logging

from elro.device import ATTR_BATTERY_LEVEL, ATTR_DEVICE_STATE, ATTR_SIGNAL
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfRatio
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from homeassistant.util.percentage import ranged_value_to_percentage

from .coordinator import ElroConnectsConfigEntry
from .entity import ElroConnectsEntity
from .helpers import async_set_up_discovery_helper

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


@dataclass
class ElroSensorDescription(SensorEntityDescription):
    """Class that holds senspr specific sensor info."""

    maximum_value: int | None = None


SENSOR_TYPES = {
    ATTR_BATTERY_LEVEL: (
        ElroSensorDescription(
            key=ATTR_BATTERY_LEVEL,
            translation_key="battery",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            maximum_value=100,
        ),
    ),
    ATTR_SIGNAL: (
        ElroSensorDescription(
            key=ATTR_SIGNAL,
            translation_key="signal",
            device_class=SensorDeviceClass.POWER_FACTOR,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            icon="mdi:signal",
            maximum_value=4,
            entity_registry_enabled_default=False,
        ),
    ),
    ATTR_DEVICE_STATE: (
        ElroSensorDescription(
            key=ATTR_DEVICE_STATE,
            translation_key="device_state",
            device_class=SensorDeviceClass.ENUM,
            icon="mdi:state-machine",
            maximum_value=None,
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
        ElroConnectsSensor,
        config_entry,
        SENSOR_TYPES,
        async_add_entities,
    )


class ElroConnectsSensor(ElroConnectsEntity, SensorEntity):
    """Elro Connects Fire Alarm Entity."""

    entity_description: ElroSensorDescription

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the sensor."""
        raw_value = self.data[self.entity_description.key]
        if max_value := self.entity_description.maximum_value:
            value = ranged_value_to_percentage((1, max_value), raw_value)
        else:
            value = slugify(raw_value)
        return value if max_value is None or raw_value <= max_value else None
