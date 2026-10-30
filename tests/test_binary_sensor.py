"""Test the Elro Connects binary sensor platform."""

import copy
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
import pytest

from custom_components.elro_connects.const import DOMAIN

from .test_common import MOCK_DEVICE_STATUS_DATA


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("entity_id", "name", "state", "device_class"),
    [
        ("binary_sensor.beganegrond_smoke", "Beganegrond Smoke", STATE_OFF, "smoke"),
        ("binary_sensor.eerste_etage_smoke", "Eerste etage Smoke", STATE_ON, "smoke"),
        ("binary_sensor.zolder_smoke", "Zolder Smoke", STATE_UNKNOWN, "smoke"),
        (
            "binary_sensor.corner_carbon_monoxide",
            "Corner Carbon monoxide",
            STATE_UNAVAILABLE,
            "carbon_monoxide",
        ),
        ("binary_sensor.voordeur_opening", "Voordeur Opening", STATE_ON, "opening"),
        ("binary_sensor.raam_opening", "Raam Opening", STATE_OFF, "opening"),
        (
            "binary_sensor.beganegrond_problem",
            "Beganegrond Problem",
            STATE_OFF,
            "problem",
        ),
        (
            "binary_sensor.beganegrond_battery",
            "Beganegrond Battery",
            STATE_OFF,
            "battery",
        ),
    ],
)
async def test_setup_integration_with_binary_sensor_platform(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
    entity_id: str,
    name: str,
    state: str,
    device_class: str,
) -> None:
    """Test we can setup the integration with the binary sensor platform."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entity = hass.states.get(entity_id)
    assert entity.state == state
    assert entity.attributes[ATTR_FRIENDLY_NAME] == name
    if state != STATE_UNAVAILABLE:
        assert entity.attributes[ATTR_DEVICE_CLASS] == device_class


async def test_diagnostic_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test the problem and battery sensors are disabled diagnostic entities."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entry = entity_registry.async_get("binary_sensor.beganegrond_smoke")
    assert entry.entity_category is None
    assert entry.disabled_by is None
    for entity_id in (
        "binary_sensor.beganegrond_problem",
        "binary_sensor.beganegrond_battery",
    ):
        entry = entity_registry.async_get(entity_id)
        assert entry.entity_category is EntityCategory.DIAGNOSTIC
        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get(entity_id) is None


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("device_id", "device_state", "expected"),
    [
        # Alarm: (alarm, problem, battery)
        (1, "NORMAL", (STATE_OFF, STATE_OFF, STATE_OFF)),
        (1, "ALARM", (STATE_ON, STATE_OFF, STATE_OFF)),
        (1, "FIRE ALARM", (STATE_ON, STATE_OFF, STATE_OFF)),
        (1, "TEMPERATURE ALARM", (STATE_ON, STATE_OFF, STATE_OFF)),
        # A test alarm does not trigger the alarm sensor
        (1, "TEST ALARM", (STATE_OFF, STATE_OFF, STATE_OFF)),
        (1, "SILENCE", (STATE_OFF, STATE_OFF, STATE_OFF)),
        (1, "FAULT", (STATE_OFF, STATE_ON, STATE_OFF)),
        (1, "LOW BATTERY", (STATE_OFF, STATE_OFF, STATE_ON)),
        # Door/window sensor: (opening, problem, battery)
        (10, "OPEN", (STATE_ON, STATE_OFF, STATE_OFF)),
        (10, "ALARM", (STATE_ON, STATE_OFF, STATE_OFF)),
        (10, "CLOSED", (STATE_OFF, STATE_OFF, STATE_OFF)),
        (10, "LOW BATTERY", (STATE_UNKNOWN, STATE_OFF, STATE_ON)),
    ],
)
async def test_binary_sensor_states(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
    device_id: int,
    device_state: str,
    expected: tuple[str, str, str],
) -> None:
    """Test the binary sensor states for the device states."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    status_data[device_id]["device_state"] = device_state
    mock_k1_connector["result"].return_value = status_data
    await mock_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    name = {1: "beganegrond", 10: "raam"}[device_id]
    main = {1: "smoke", 10: "opening"}[device_id]
    states = tuple(
        hass.states.get(f"binary_sensor.{name}_{key}").state
        for key in (main, "problem", "battery")
    )
    assert states == expected
