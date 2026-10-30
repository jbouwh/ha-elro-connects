"""Test the Elro Connects diagnostics."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion

from custom_components.elro_connects.const import DOMAIN

from .test_common import MOCK_DEVICE_STATUS_DATA


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_k1_connector: dict[AsyncMock],
    mock_entry: ConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the config entry diagnostics with the secrets redacted."""
    hass.config_entries.async_update_entry(
        mock_entry,
        data={
            **mock_entry.data,
            CONF_API_KEY: "secret-key",
            CONF_USERNAME: "user@example.com",
            CONF_PASSWORD: "secret-password",
        },
    )
    mock_k1_connector["result"].return_value = MOCK_DEVICE_STATUS_DATA
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, mock_entry)
    assert diagnostics == snapshot
    for secret in ("secret-key", "user@example.com", "secret-password"):
        assert secret not in str(diagnostics)
