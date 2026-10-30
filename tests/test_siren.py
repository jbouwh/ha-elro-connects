"""Test the Elro Connects siren platform."""

from unittest.mock import AsyncMock

from elro.api import K1
from elro.command import Command
from homeassistant.components import siren
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
import pytest

from custom_components.elro_connects.const import DOMAIN

from .test_common import MOCK_DEVICE_STATUS_DATA


@pytest.mark.parametrize(
    ("entity_id", "name", "state"),
    [
        (
            "siren.beganegrond_fire_alarm",
            "Beganegrond Fire Alarm",
            STATE_OFF,
        ),
        (
            "siren.eerste_etage_fire_alarm",
            "Eerste etage Fire Alarm",
            STATE_ON,
        ),
        (
            "siren.zolder_fire_alarm",
            "Zolder Fire Alarm",
            STATE_OFF,
        ),
        (
            "siren.corner_carbon_monoxide_alarm",
            "Corner Carbon Monoxide Alarm",
            STATE_UNAVAILABLE,
        ),
    ],
)
async def test_setup_integration_with_siren_platform(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
    entity_id: str,
    name: str,
    state: str,
) -> None:
    """Test we can setup the integration with the siren platform."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    await hass.config_entries.async_setup(mock_entry.entry_id)
    await hass.async_block_till_done()

    # Check entity setup from connector data
    entity = hass.states.get(entity_id)
    attributes = entity.attributes

    assert entity.state == state
    assert attributes["friendly_name"] == name
    # The siren is a tool to test and silence the alarm
    assert (
        entity_registry.async_get(entity_id).entity_category
        is EntityCategory.DIAGNOSTIC
    )


async def test_alarm_testing(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test we can start a test alarm and silence it."""
    entity_id = "siren.beganegrond_fire_alarm"
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entity = hass.states.get(entity_id)
    assert entity.state == STATE_OFF

    # Turn siren on with test signal
    mock_k1_connector["result"].reset_mock()
    await hass.services.async_call(
        siren.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    entity = hass.states.get(entity_id)
    assert entity.state == STATE_ON
    assert (
        mock_k1_connector["result"].call_args[0][0]["cmd_id"]
        == Command.EQUIPMENT_CONTROL
    )
    assert (
        mock_k1_connector["result"].call_args[0][0]["additional_attributes"][
            "device_status"
        ]
        == "17000000"
    )
    assert mock_k1_connector["result"].call_args[1] == {"device_ID": 1}

    # Turn siren off with silence command
    mock_k1_connector["result"].reset_mock()
    await hass.services.async_call(
        siren.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    entity = hass.states.get(entity_id)
    assert entity.state == STATE_OFF
    assert (
        mock_k1_connector["result"].call_args[0][0]["cmd_id"]
        == Command.EQUIPMENT_CONTROL
    )
    assert (
        mock_k1_connector["result"].call_args[0][0]["additional_attributes"][
            "device_status"
        ]
        == "00000000"
    )
    assert mock_k1_connector["result"].call_args[1] == {"device_ID": 1}


@pytest.mark.parametrize("service", [SERVICE_TURN_ON, SERVICE_TURN_OFF])
async def test_siren_command_fails(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
    service: str,
) -> None:
    """Test a failing command raises a translated error and keeps the state."""
    entity_id = "siren.beganegrond_fire_alarm"
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    state = hass.states.get(entity_id).state

    mock_k1_connector["result"].side_effect = K1.K1ConnectionError("timeout")
    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            siren.DOMAIN, service, {ATTR_ENTITY_ID: entity_id}, blocking=True
        )
    assert exc_info.value.translation_key == "command_failed"
    assert (
        str(exc_info.value) == "Could not send the command to the K1 connector: timeout"
    )
    assert hass.states.get(entity_id).state == state
