"""Test the Elro Connects helpers."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.setup import async_setup_component

from custom_components.elro_connects.const import DOMAIN
from custom_components.elro_connects.helpers import async_set_up_discovery_helper

from .test_common import MOCK_DEVICE_STATUS_DATA


async def test_discovery_helper_multiple_descriptions(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test all descriptions for a device type or attribute are added."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    alarm = EntityDescription(key="alarm")
    problem = EntityDescription(key="problem")
    battery = EntityDescription(key="battery")
    battery_low = EntityDescription(key="battery_low")
    descriptions = {
        "FIRE_ALARM": (alarm, problem),
        "battery": (battery, battery_low),
    }
    entity_class = MagicMock(side_effect=lambda _, device_id, desc: (device_id, desc))
    async_add_entities = MagicMock()

    async_set_up_discovery_helper(
        hass, entity_class, mock_entry, descriptions, async_add_entities
    )

    added = async_add_entities.call_args[0][0]
    # The fire alarms only get the device type descriptions
    assert (1, alarm) in added
    assert (1, problem) in added
    assert (1, battery) not in added
    # Other devices with a battery get all battery descriptions
    assert (5, battery) in added
    assert (5, battery_low) in added
    assert (5, alarm) not in added
