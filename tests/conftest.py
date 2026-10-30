"""Fixtures for testing the Elro Connects integration."""

from collections.abc import Generator
from unittest.mock import AsyncMock, PropertyMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from custom_components.elro_connects.const import CONF_CONNECTOR_ID, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration mocking."""
    return


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return the snapshot assertion with the Home Assistant extension.

    Both syrupy and pytest-homeassistant-custom-component provide a snapshot
    fixture, and which one is used depends on the order the plugins are
    loaded. Set the extension here, so the snapshots are always stored in
    the snapshots directory.
    """
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Enable the entities that are disabled by default."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
        new_callable=PropertyMock,
    ):
        yield


@pytest.fixture
def mock_get() -> AsyncMock:
    """Mock aiohttp get and post requests."""
    with patch("aiohttp.ClientSession.get") as mock_session_get:
        yield mock_session_get


@pytest.fixture
def mock_post() -> AsyncMock:
    """Mock aiohttp get and post requests."""
    with patch("aiohttp.ClientSession.post") as mock_session_post:
        yield mock_session_post


@pytest.fixture
def mock_k1_connector() -> dict[AsyncMock]:
    """Mock the Elro K1 connector class."""
    with (
        patch(
            "elro.api.K1.async_connect",
            AsyncMock(),
        ) as mock_connect,
        patch(
            "elro.api.K1.async_disconnect",
            AsyncMock(),
        ) as mock_disconnect,
        patch(
            "elro.api.K1.async_configure",
            AsyncMock(),
        ) as mock_configure,
        patch(
            "elro.api.K1.async_process_command",
            AsyncMock(return_value={}),
        ) as mock_result,
    ):
        yield {
            "connect": mock_connect,
            "disconnect": mock_disconnect,
            "configure": mock_configure,
            "result": mock_result,
        }


@pytest.fixture
def mock_entry(hass: HomeAssistant) -> ConfigEntry:
    """Mock a Elro Connects config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="ST_deadbeef0000",
        minor_version=2,
        data={
            CONF_HOST: "1.1.1.1",
            CONF_CONNECTOR_ID: "ST_deadbeef0000",
            CONF_PORT: 1025,
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_k1_api(hass: HomeAssistant) -> dict[AsyncMock]:
    """Mock the Elro K1 API."""
    with (
        patch(
            "elro.api.K1.async_connect",
            AsyncMock(),
        ) as mock_connect,
        patch(
            "elro.api.K1.async_disconnect",
            AsyncMock(),
        ) as mock_disconnect,
        patch(
            "elro.api.K1.async_configure",
            AsyncMock(),
        ) as mock_configure,
        patch(
            "elro.api.K1.async_process_command",
            AsyncMock(return_value={}),
        ) as mock_result,
        patch(
            "elro.auth.ElroConnectsSession._async_get_domain",
            AsyncMock(return_value="hekr.me"),
        ) as mock_result,
    ):
        yield {
            "connect": mock_connect,
            "disconnect": mock_disconnect,
            "configure": mock_configure,
            "result": mock_result,
        }
