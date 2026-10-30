"""Test the Elro Connects sensor platform."""

import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock

from homeassistant.components.sensor import ATTR_OPTIONS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
import pytest

from custom_components.elro_connects.const import DOMAIN
from custom_components.elro_connects.sensor import DEVICE_STATE_OPTIONS

from .test_common import MOCK_DEVICE_STATUS_DATA

STRINGS = Path(__file__).parent.parent / "custom_components" / DOMAIN / "strings.json"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("entity_id", "state", "device_class", "unit", "category"),
    [
        (
            "sensor.beganegrond_battery",
            "100",
            "battery",
            PERCENTAGE,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "sensor.beganegrond_signal",
            "75",
            None,
            PERCENTAGE,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "sensor.beganegrond_device_state",
            "normal",
            "enum",
            None,
            EntityCategory.DIAGNOSTIC,
        ),
        (
            "sensor.eerste_etage_device_state",
            "alarm",
            "enum",
            None,
            EntityCategory.DIAGNOSTIC,
        ),
    ],
)
async def test_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
    entity_id: str,
    state: str,
    device_class: str | None,
    unit: str | None,
    category: EntityCategory | None,
) -> None:
    """Test the sensor states, device classes and entity categories."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entity = hass.states.get(entity_id)
    assert entity.state == state
    assert entity.attributes.get(ATTR_DEVICE_CLASS) == device_class
    assert entity.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == unit
    assert entity_registry.async_get(entity_id).entity_category == category


async def test_device_state_options(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test the device state options match the translated states."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entity = hass.states.get("sensor.beganegrond_device_state")
    assert entity.attributes[ATTR_OPTIONS] == DEVICE_STATE_OPTIONS
    strings = json.loads(STRINGS.read_text(encoding="utf-8"))
    translated = strings["entity"]["sensor"]["device_state"]["state"]
    assert sorted(translated) == DEVICE_STATE_OPTIONS


async def test_unknown_device_state(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test an unknown device state is unknown and logged once."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    status_data[1]["device_state"] = "9C"
    mock_k1_connector["result"].return_value = status_data
    for _ in range(2):
        await mock_entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

    assert hass.states.get("sensor.beganegrond_device_state").state == STATE_UNKNOWN
    assert caplog.text.count("Unknown device state 9C") == 1
