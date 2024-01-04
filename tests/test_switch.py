"""Test the Elro Connects switch platform."""
from __future__ import annotations

from unittest.mock import AsyncMock

from elro.command import Command
import pytest

from custom_components.elro_connects.const import DOMAIN
from homeassistant.components import switch
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .test_common import MOCK_DEVICE_STATUS_DATA


@pytest.mark.parametrize(
    "entity_id,name,state,device_class",
    [
        (
            "switch.wall_switch_off_socket",
            "Wall switch off Socket",
            STATE_OFF,
            "outlet",
        ),
        (
            "switch.wall_switch_on_socket",
            "Wall switch on Socket",
            STATE_ON,
            "outlet",
        ),
    ],
)
async def test_setup_integration_with_siren_platform(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
    entity_id: str,
    name: str,
    state: str,
    device_class: str,
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
    assert attributes["device_class"] == device_class


async def test_socket_testing(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test we turn on a socket."""
    entity_id = "switch.wall_switch_off_socket"
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entity = hass.states.get(entity_id)
    assert entity.state == STATE_OFF

    # Turn siren on with test signal
    mock_k1_connector["result"].reset_mock()
    await hass.services.async_call(
        switch.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
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
        == "01010000"
    )
    assert mock_k1_connector["result"].call_args[1] == {"device_ID": 7}

    # Turn the socket off
    mock_k1_connector["result"].reset_mock()
    await hass.services.async_call(
        switch.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
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
        == "01000000"
    )
    assert mock_k1_connector["result"].call_args[1] == {"device_ID": 7}
