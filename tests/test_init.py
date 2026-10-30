"""Test the Elro Connects setup."""

import copy
from datetime import timedelta
from unittest.mock import AsyncMock

from elro.api import K1
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from homeassistant.util import dt
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.elro_connects import async_remove_config_entry_device
from custom_components.elro_connects.const import CONF_CONNECTOR_ID, DOMAIN

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
        "elro_connects integration not ready yet: Could not get the device states "
        "from the K1 connector: K1 connection error; Retrying" in caplog.text
    )


async def test_setup_integration_exception(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test if an unknown backend error is logged and setup is retried."""
    mock_k1_connector["result"].side_effect = Exception
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    assert mock_entry.state is ConfigEntryState.SETUP_RETRY
    assert "Unexpected error fetching ST_deadbeef0000 data" in caplog.text


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
    assert hass.states.get("siren.beganegrond_test_alarm") is not None
    assert hass.states.get("siren.eerste_etage_test_alarm") is not None
    assert hass.states.get("siren.zolder_test_alarm") is None
    assert hass.states.get("switch.wall_switch_off_socket") is not None
    assert hass.states.get("switch.wall_switch_on_socket") is not None

    # Simulate a dynamic discovery update resulting in 3 siren entities
    mock_k1_connector["result"].return_value = updated_status_data
    time = dt.now() + timedelta(seconds=30)
    async_fire_time_changed(hass, time)
    # await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    assert hass.states.get("siren.beganegrond_test_alarm") is not None
    assert hass.states.get("siren.eerste_etage_test_alarm") is not None
    assert hass.states.get("siren.zolder_test_alarm") is not None
    assert hass.states.get("switch.wall_switch_off_socket") is not None
    assert hass.states.get("switch.wall_switch_on_socket") is not None

    # Remove device 1 from api data, entity should appear offline with an unknown state
    updated_status_data.pop(1)

    mock_k1_connector["result"].return_value = updated_status_data
    time = time + timedelta(seconds=30)
    async_fire_time_changed(hass, time)
    await hass.async_block_till_done()

    assert hass.states.get("siren.beganegrond_test_alarm").state == "off"
    assert hass.states.get("siren.eerste_etage_test_alarm") is not None
    assert hass.states.get("siren.zolder_test_alarm") is not None
    assert hass.states.get("switch.wall_switch_off_socket").state == STATE_OFF
    assert hass.states.get("switch.wall_switch_on_socket").state == STATE_ON


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

    connector_id = mock_entry.runtime_data.connector_id
    device_registry = dr.async_get(hass)
    # Test removing the device for siren 4 will work
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, f"{connector_id}_4"), mock_entry.entry_id
    )
    assert device_entry
    assert await async_remove_config_entry_device(hass, mock_entry, device_entry)

    # Test removing the device for siren 2 will not work because it is in use
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, f"{connector_id}_2"), mock_entry.entry_id
    )
    assert device_entry
    assert not await async_remove_config_entry_device(hass, mock_entry, device_entry)

    # Test removing the the K1 connector device will not work
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, connector_id), mock_entry.entry_id
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
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("siren.beganegrond_test_alarm") is not None
    assert hass.states.get("siren.eerste_etage_test_alarm") is not None
    assert hass.states.get("siren.zolder_test_alarm") is not None
    assert hass.states.get("siren.beganegrond_test_alarm").state == "off"
    assert hass.states.get("siren.eerste_etage_test_alarm").state == "on"
    assert hass.states.get("siren.zolder_test_alarm").state == "off"
    # Test unload
    assert await hass.config_entries.async_unload(mock_entry.entry_id)
    config_entry_state = mock_entry.state
    assert config_entry_state is ConfigEntryState.NOT_LOADED
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get("siren.beganegrond_test_alarm").state == "unavailable"
    assert hass.states.get("siren.eerste_etage_test_alarm").state == "unavailable"
    assert hass.states.get("siren.zolder_test_alarm").state == "unavailable"
    mock_k1_connector["disconnect"].assert_awaited_once()

    # The device registry listener is removed, name changes are not synced anymore
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, "ST_deadbeef0000_4"), mock_entry.entry_id
    )
    assert device_entry
    mock_k1_connector["result"].reset_mock()
    device_registry.async_update_device(
        device_id=device_entry.id, name_by_user="Some new name"
    )
    await hass.async_block_till_done()
    assert mock_k1_connector["result"].call_count == 0


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

    connector_id = mock_entry.runtime_data.connector_id
    device_registry = dr.async_get(hass)
    # Test updating the device name for siren 4 will work
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, f"{connector_id}_4"), mock_entry.entry_id
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
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, connector_id), mock_entry.entry_id
    )
    assert device_entry
    mock_k1_connector["result"].reset_mock()
    device_registry.async_update_device(
        device_id=device_entry.id, name_by_user="Some long new name"
    )
    await hass.async_block_till_done()

    assert mock_k1_connector["result"].call_count == 0


async def test_hub_device(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test the K1 hub is set up once and the devices are linked to it."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    # The hub is created, even when the connector has no devices
    hub = device_registry.async_get_device_by_identifier(
        (DOMAIN, "ST_deadbeef0000"), mock_entry.entry_id
    )
    assert hub is not None
    assert hub.connections == {(dr.CONNECTION_NETWORK_MAC, "de:ad:be:ef:00:00")}
    assert hub.model == "K1 (SF40GA)"
    assert hub.name == "Elro Connects K1 ST_deadbeef0000"

    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    await mock_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    devices = dr.async_entries_for_config_entry(device_registry, mock_entry.entry_id)
    sub_devices = [device for device in devices if device.id != hub.id]
    assert sub_devices
    assert all(device.via_device_id == hub.id for device in sub_devices)


async def test_migrate_hub_device(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test the hub with the MAC address as identifier is migrated."""
    old_hub = device_registry.async_get_or_create(
        config_entry_id=mock_entry.entry_id,
        identifiers={(dr.CONNECTION_NETWORK_MAC, "de:ad:be:ef:00:00")},
        name="Elro Connects K1 ST_deadbeef0000",
    )
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    hub = device_registry.async_get(old_hub.id)
    assert hub.identifiers == {(DOMAIN, "ST_deadbeef0000")}
    assert hub.connections == {(dr.CONNECTION_NETWORK_MAC, "de:ad:be:ef:00:00")}
    assert (
        len(dr.async_entries_for_config_entry(device_registry, mock_entry.entry_id))
        == 1
    )


async def test_migrate_options(
    hass: HomeAssistant, mock_k1_connector: dict[AsyncMock]
) -> None:
    """Test the duplicated options of the old options flow are removed."""
    data = {CONF_HOST: "1.1.1.1", CONF_CONNECTOR_ID: "ST_deadbeef0000", CONF_PORT: 1025}
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ST_deadbeef0000",
        minor_version=1,
        data=data,
        options=data,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.minor_version == 2
    assert entry.options == {}
    assert entry.data == data


async def test_migrate_from_future_version(
    hass: HomeAssistant, mock_k1_connector: dict[AsyncMock]
) -> None:
    """Test an entry of a future version is not set up."""
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_update_device_name_ignored(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test a reset name or an unknown device does not update the connector."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, "ST_deadbeef0000_4"), mock_entry.entry_id
    )
    assert device_entry
    device_registry.async_update_device(device_entry.id, name_by_user="New name")
    await hass.async_block_till_done()

    # Resetting the name to the default does not change the name in the connector
    mock_k1_connector["result"].reset_mock()
    device_registry.async_update_device(device_entry.id, name_by_user=None)
    await hass.async_block_till_done()
    assert mock_k1_connector["result"].call_count == 0

    # An update event of a device that no longer exists is ignored
    hass.bus.async_fire(
        dr.EVENT_DEVICE_REGISTRY_UPDATED,
        {
            "action": "update",
            "device_id": "unknown",
            "changes": {"name_by_user": "Old name"},
        },
    )
    await hass.async_block_till_done()
    assert mock_k1_connector["result"].call_count == 0
