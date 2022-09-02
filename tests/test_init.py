"""Test the Elro Connects setup."""

import copy
from datetime import timedelta
from unittest.mock import AsyncMock

from elro.api import K1
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.elro_connects import async_remove_config_entry_device
from custom_components.elro_connects.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import format_mac
from homeassistant.setup import async_setup_component
from homeassistant.util import dt

from .test_common import MOCK_DEVICE_STATUS_DATA


async def help_remove_device(hass, ws_client, device_id, config_entry_id):
    """Remove config entry from a device."""
    await ws_client.send_json(
        {
            "id": 5,
            "type": "config/device_registry/remove_config_entry",
            "config_entry_id": config_entry_id,
            "device_id": device_id,
        }
    )
    response = await ws_client.receive_json()
    assert response["success"]


async def test_setup_integration_no_data(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test we can setup an empty integration."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


async def test_setup_integration_update_fail(
    hass: HomeAssistant,
    caplog,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test if an update can fail with warnings."""
    mock_k1_connector["result"].side_effect = K1.K1ConnectionError
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert (
        "elro_connects integration not ready yet: K1 connection error; Retrying in background"
        in caplog.text
    )


async def test_setup_integration_exception(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test if an unknown backend error throws."""
    mock_k1_connector["result"].side_effect = Exception
    with pytest.raises(Exception):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        assert (
            "elro_connects integration not ready yet: K1 connection error; Retrying in background"
            in caplog.text
        )


async def test_setup_integration_with_data(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test we can setup the integration with some data."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()


async def test_configure_platforms_dynamically(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test we can setup and tear down platforms dynamically."""
    # Updated status holds device info for device [1,2,4]
    updated_status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    # Initial status holds device info for device [1,2]
    initial_status_data = copy.deepcopy(updated_status_data)
    initial_status_data.pop(4)

    # setup integration with 2 siren entities
    mock_k1_connector["result"].return_value = initial_status_data
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert hass.states.get("siren.beganegrond") is not None
    assert hass.states.get("siren.eerste_etage") is not None
    assert hass.states.get("siren.zolder") is None

    # Simulate a dynamic discovery update resulting in 3 siren entities
    mock_k1_connector["result"].return_value = updated_status_data
    time = dt.now() + timedelta(seconds=30)
    async_fire_time_changed(hass, time)
    # await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("siren.beganegrond") is not None
    assert hass.states.get("siren.eerste_etage") is not None
    assert hass.states.get("siren.zolder") is not None

    # Remove device 1 from api data, entity should appear offline with an unknown state
    updated_status_data.pop(1)

    mock_k1_connector["result"].return_value = updated_status_data
    time = time + timedelta(seconds=30)
    async_fire_time_changed(hass, time)
    await hass.async_block_till_done()

    assert hass.states.get("siren.beganegrond").state == "off"
    assert hass.states.get("siren.eerste_etage") is not None
    assert hass.states.get("siren.zolder") is not None


async def test_remove_device_from_config_entry(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test the removing a device would work."""
    # Initial status holds device info for device [1,2,4]
    initial_status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    # Updated status holds device info for device [1,2]
    updated_status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    updated_status_data.pop(4)

    # setup integration with 3 siren entities
    mock_k1_connector["result"].return_value = initial_status_data
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    # Simulate deactivation of siren 4
    mock_k1_connector["result"].return_value = updated_status_data
    time = dt.now() + timedelta(seconds=30)
    async_fire_time_changed(hass, time)
    # Wait for the update to be processed
    await hass.async_block_till_done()
    await hass.async_block_till_done()

    connector_id = hass.data[DOMAIN][mock_entry.entry_id].connector_id
    device_registry = dr.async_get(hass)
    # Test removing the device for siren 4 will work
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{connector_id}_4")}
    )
    assert device_entry
    assert await async_remove_config_entry_device(hass, mock_entry, device_entry)

    # Test removing the device for siren 2 will not work because it is in use
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{connector_id}_2")}
    )
    assert device_entry
    assert not await async_remove_config_entry_device(hass, mock_entry, device_entry)

    # Test removing the the K1 connector device will not work
    mac_address = format_mac(connector_id[3:])
    device_entry = device_registry.async_get_device(
        identifiers={(dr.CONNECTION_NETWORK_MAC, mac_address)}
    )
    assert device_entry
    assert not await async_remove_config_entry_device(hass, mock_entry, device_entry)


async def test_unloading_config_entry(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test unloading the config entry."""
    # Initial status holds device info for device [1,2,4]
    initial_status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    # setup integration with 3 siren entities
    mock_k1_connector["result"].return_value = initial_status_data
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert hass.states.get("siren.beganegrond") is not None
    assert hass.states.get("siren.eerste_etage") is not None
    assert hass.states.get("siren.zolder") is not None
    assert hass.states.get("siren.beganegrond").state == "off"
    assert hass.states.get("siren.eerste_etage").state == "on"
    assert hass.states.get("siren.zolder").state == "off"
    # Test unload
    assert await mock_entry.async_unload(hass)
    assert hass.states.get("siren.beganegrond").state == "unavailable"
    assert hass.states.get("siren.eerste_etage").state == "unavailable"
    assert hass.states.get("siren.zolder").state == "unavailable"


async def test_update_device_name(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test updating the name of the device through the K1 connector."""

    # Initial status holds device info for device [1,2,4]
    initial_status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    mock_k1_connector["result"].return_value = initial_status_data
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    connector_id = hass.data[DOMAIN][mock_entry.entry_id].connector_id
    device_registry = dr.async_get(hass)
    # Test updating the device name for siren 4 will work
    device_entry = device_registry.async_get_device(
        identifiers={(DOMAIN, f"{connector_id}_4")}
    )
    assert device_entry

    # update the name
    mock_k1_connector["result"].reset_mock()
    device_registry.async_update_device(
        device_id=device_entry.id, name_by_user="Some long new name"
    )
    await hass.async_block_till_done()

    # Check the new name was set (max length 15)
    assert mock_k1_connector["result"].call_count == 1
    assert mock_k1_connector["result"].mock_calls[0][2] == {
        "device_ID": 4,
        "device_name": "Some long new n",
    }

    # Check the name was not set if the device is not in the coordinator
    updated_status_data = copy.deepcopy(MOCK_DEVICE_STATUS_DATA)
    updated_status_data.pop(4)
    mock_k1_connector["result"].return_value = updated_status_data
    time = dt.now() + timedelta(seconds=30)
    async_fire_time_changed(hass, time)
    # Wait for the update to be processed
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    mock_k1_connector["result"].reset_mock()
    device_registry.async_update_device(
        device_id=device_entry.id, name_by_user="Name update for non existent device"
    )
    await hass.async_block_till_done()
    assert mock_k1_connector["result"].call_count == 0

    # update the K1 connector name
    device_entry = device_registry.async_get_device(
        identifiers={(dr.CONNECTION_NETWORK_MAC, f"{format_mac(connector_id[3:])}")}
    )
    assert device_entry
    mock_k1_connector["result"].reset_mock()
    device_registry.async_update_device(
        device_id=device_entry.id, name_by_user="Some long new name"
    )
    await hass.async_block_till_done()

    assert mock_k1_connector["result"].call_count == 0
