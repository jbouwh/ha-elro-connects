"""Test the Elro Connects base entity."""

from unittest.mock import AsyncMock

from elro.api import K1
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.elro_connects.const import DOMAIN
from custom_components.elro_connects.coordinator import MAX_RETRIES

from .test_common import MOCK_DEVICE_STATUS_DATA

ENTITY_IDS = (
    "siren.beganegrond_fire_alarm",
    "sensor.beganegrond_battery",
    "sensor.beganegrond_device_state",
    "switch.wall_switch_on_socket",
)


async def test_offline_device_unavailable(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test the entities of an offline device are unavailable."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    for entity_id in (
        "siren.corner_carbon_monoxide_alarm",
        "sensor.corner_battery",
        "sensor.corner_device_state",
    ):
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


async def test_connector_unavailable(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test all entities are unavailable when the connector cannot be reached."""
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    coordinator = mock_entry.runtime_data

    for entity_id in ENTITY_IDS:
        assert hass.states.get(entity_id).state != STATE_UNAVAILABLE

    # Failures are ignored until the maximum number of retries is reached
    mock_k1_connector["result"].side_effect = K1.K1ConnectionError
    for _ in range(MAX_RETRIES - 1):
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("siren.beganegrond_fire_alarm").state == STATE_OFF

    await coordinator.async_refresh()
    await hass.async_block_till_done()
    for entity_id in ENTITY_IDS:
        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    # Entities are available again when the connector recovers
    mock_k1_connector["result"].side_effect = None
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("siren.beganegrond_fire_alarm").state == STATE_OFF
    assert hass.states.get("sensor.beganegrond_battery").state == "100"
    assert hass.states.get("switch.wall_switch_on_socket").state == STATE_ON
