"""The Elro Connects binary sensor platform."""

from dataclasses import dataclass

from elro.device import (
    ALARM_CO,
    ALARM_FIRE,
    ALARM_HEAT,
    ALARM_SMOKE,
    ALARM_WATER,
    ATTR_DEVICE_STATE,
    DOOR_WINDOW_SENSOR,
    STATE_ALARM,
    STATE_CLOSED,
    STATE_FAULT,
    STATE_FIRE_ALARM,
    STATE_LOW_BATTERY,
    STATE_OPEN,
    STATE_TEMPERATURE_ALARM,
    STATE_UNKNOWN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ALARM_GAS
from .coordinator import ElroConnectsConfigEntry
from .entity import ElroConnectsEntity
from .helpers import async_set_up_discovery_helper

PARALLEL_UPDATES = 0

# A test alarm is not an alarm, so it does not trigger alarm automations
ALARM_STATES = (STATE_ALARM, STATE_FIRE_ALARM, STATE_TEMPERATURE_ALARM)


@dataclass(frozen=True, kw_only=True)
class ElroBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes Elro Connects binary sensor entities."""

    on_states: tuple[str, ...]
    # If set, the state is unknown if the device state is not an on or off state
    off_states: tuple[str, ...] | None = None


PROBLEM = ElroBinarySensorEntityDescription(
    key="problem",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
    on_states=(STATE_FAULT,),
)
LOW_BATTERY = ElroBinarySensorEntityDescription(
    key="low_battery",
    device_class=BinarySensorDeviceClass.BATTERY,
    entity_category=EntityCategory.DIAGNOSTIC,
    on_states=(STATE_LOW_BATTERY,),
)


def _alarm(
    device_class: BinarySensorDeviceClass,
) -> tuple[ElroBinarySensorEntityDescription, ...]:
    """Return the descriptions for an alarm device."""
    return (
        ElroBinarySensorEntityDescription(
            key="alarm", device_class=device_class, on_states=ALARM_STATES
        ),
        PROBLEM,
        LOW_BATTERY,
    )


BINARY_SENSOR_DEVICE_TYPES = {
    ALARM_CO: _alarm(BinarySensorDeviceClass.CO),
    ALARM_FIRE: _alarm(BinarySensorDeviceClass.SMOKE),
    ALARM_GAS: _alarm(BinarySensorDeviceClass.GAS),
    ALARM_HEAT: _alarm(BinarySensorDeviceClass.HEAT),
    ALARM_SMOKE: _alarm(BinarySensorDeviceClass.SMOKE),
    ALARM_WATER: _alarm(BinarySensorDeviceClass.MOISTURE),
    DOOR_WINDOW_SENSOR: (
        ElroBinarySensorEntityDescription(
            key="opening",
            device_class=BinarySensorDeviceClass.OPENING,
            # The sensor reports ALARM when it is opened
            on_states=(STATE_OPEN, STATE_ALARM),
            off_states=(STATE_CLOSED,),
        ),
        PROBLEM,
        LOW_BATTERY,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ElroConnectsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    async_set_up_discovery_helper(
        hass,
        ElroConnectsBinarySensor,
        config_entry,
        BINARY_SENSOR_DEVICE_TYPES,
        async_add_entities,
    )


class ElroConnectsBinarySensor(ElroConnectsEntity, BinarySensorEntity):
    """Elro Connects binary sensor entity."""

    entity_description: ElroBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the device state is an on state."""
        device_state = self.data[ATTR_DEVICE_STATE]
        if device_state == STATE_UNKNOWN:
            return None
        if device_state in self.entity_description.on_states:
            return True
        off_states = self.entity_description.off_states
        if off_states is not None and device_state not in off_states:
            return None
        return False
