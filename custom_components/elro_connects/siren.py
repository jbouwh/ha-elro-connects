"""The Elro Connects siren platform."""

from dataclasses import dataclass
import logging

from elro.command import SILENCE_ALARM, TEST_ALARM, TEST_ALARM_ALT, CommandAttributes
from elro.device import (
    ALARM_CO,
    ALARM_FIRE,
    ALARM_HEAT,
    ALARM_SMOKE,
    ALARM_WATER,
    ATTR_DEVICE_STATE,
    STATE_SILENCE,
    STATE_TEST_ALARM,
    STATES_ON,
)
from homeassistant.components.siren import (
    SirenEntity,
    SirenEntityDescription,
    SirenEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ElroConnectsConfigEntry
from .entity import ElroConnectsEntity
from .helpers import async_set_up_discovery_helper


@dataclass
class ElroSirenEntityDescription(SirenEntityDescription):
    """A class that describes elro siren entities."""

    test_alarm: CommandAttributes | None = None
    silence_alarm: CommandAttributes | None = None


_LOGGER = logging.getLogger(__name__)

SIREN_DEVICE_TYPES = {
    ALARM_CO: (
        ElroSirenEntityDescription(
            key=ALARM_CO,
            translation_key="alarm_co",
            icon="mdi:molecule-co",
            test_alarm=TEST_ALARM_ALT,
            silence_alarm=SILENCE_ALARM,
        ),
    ),
    ALARM_FIRE: (
        ElroSirenEntityDescription(
            key=ALARM_FIRE,
            translation_key="alarm_fire",
            icon="mdi:fire-alert",
            test_alarm=TEST_ALARM,
            silence_alarm=SILENCE_ALARM,
        ),
    ),
    ALARM_HEAT: (
        ElroSirenEntityDescription(
            key=ALARM_HEAT,
            translation_key="alarm_heat",
            icon="mdi:fire-alert",
            test_alarm=TEST_ALARM_ALT,
            silence_alarm=SILENCE_ALARM,
        ),
    ),
    ALARM_SMOKE: (
        ElroSirenEntityDescription(
            key=ALARM_SMOKE,
            translation_key="alarm_smoke",
            icon="mdi:smoke",
            test_alarm=TEST_ALARM,
            silence_alarm=SILENCE_ALARM,
        ),
    ),
    ALARM_WATER: (
        ElroSirenEntityDescription(
            key=ALARM_WATER,
            translation_key="alarm_water",
            icon="mdi:water-alert",
            test_alarm=TEST_ALARM_ALT,
            silence_alarm=SILENCE_ALARM,
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
        ElroConnectsSiren,
        config_entry,
        SIREN_DEVICE_TYPES,
        async_add_entities,
    )


class ElroConnectsSiren(ElroConnectsEntity, SirenEntity):
    """Elro Connects Fire Alarm Entity."""

    entity_description: ElroSirenEntityDescription
    _attr_supported_features = SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF

    @property
    def is_on(self) -> bool:
        """Return true if the alarm is active."""
        return self.data[ATTR_DEVICE_STATE] in STATES_ON

    async def async_turn_on(self, **kwargs) -> None:
        """Send a test alarm request."""
        _LOGGER.debug("Sending test alarm request for entity %s", self.entity_id)
        await self.coordinator.async_command(
            self.entity_description.test_alarm, device_ID=self._device_id
        )

        self.data[ATTR_DEVICE_STATE] = STATE_TEST_ALARM
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Send a silence alarm request."""
        _LOGGER.debug("Sending silence alarm request for entity %s", self.entity_id)
        await self.coordinator.async_command(
            self.entity_description.silence_alarm, device_ID=self._device_id
        )

        self.data[ATTR_DEVICE_STATE] = STATE_SILENCE
        self.async_write_ha_state()
