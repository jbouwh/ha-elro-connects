"""The Elro Connects sensor platform."""

from dataclasses import dataclass
import logging

from elro.device import ATTR_BATTERY_LEVEL, ATTR_DEVICE_STATE, ATTR_SIGNAL, DEVICE_STATE
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfRatio
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify
from homeassistant.util.percentage import ranged_value_to_percentage

from .coordinator import ElroConnectsConfigEntry
from .entity import ElroConnectsEntity
from .helpers import async_set_up_discovery_helper

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

DEVICE_STATE_OPTIONS = sorted({slugify(state) for state in DEVICE_STATE.values()})

# Unknown device states that were already logged
_reported_device_states: set[str] = set()


@dataclass
class ElroSensorDescription(SensorEntityDescription):
    """Class that holds sensor specific sensor info."""

    maximum_value: int | None = None


SENSOR_TYPES = {
    ATTR_BATTERY_LEVEL: (
        ElroSensorDescription(
            key=ATTR_BATTERY_LEVEL,
            translation_key="battery",
            device_class=SensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            maximum_value=100,
        ),
    ),
    ATTR_SIGNAL: (
        ElroSensorDescription(
            key=ATTR_SIGNAL,
            translation_key="signal",
            entity_category=EntityCategory.DIAGNOSTIC,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfRatio.PERCENTAGE,
            maximum_value=4,
            entity_registry_enabled_default=False,
        ),
    ),
    ATTR_DEVICE_STATE: (
        ElroSensorDescription(
            key=ATTR_DEVICE_STATE,
            translation_key="device_state",
            device_class=SensorDeviceClass.ENUM,
            options=DEVICE_STATE_OPTIONS,
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
    def native_value(self) -> int | float | str | None:
        """Return the state of the sensor."""
        raw_value = self.data[self.entity_description.key]
        if max_value := self.entity_description.maximum_value:
            value = ranged_value_to_percentage((1, max_value), raw_value)
            return value if raw_value <= max_value else None
        value = slugify(raw_value)
        if value not in DEVICE_STATE_OPTIONS:
            if raw_value not in _reported_device_states:
                _reported_device_states.add(raw_value)
                _LOGGER.warning(
                    "Unknown device state %s reported by %s, please open an issue at "
                    "https://github.com/jbouwh/lib-elro-connects/issues",
                    raw_value,
                    self.entity_id,
                )
            return None
        return value
