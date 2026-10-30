"""Test the Elro Connects config flow."""

import json
from pathlib import Path
import re
from typing import Any
from unittest.mock import AsyncMock, patch

from elro.api import K1
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorType
from homeassistant.setup import async_setup_component
import pytest

from custom_components.elro_connects.config_flow import ELRO_CONNECTS_DATA_SCHEMA
from custom_components.elro_connects.const import CONF_CONNECTOR_ID, DOMAIN

from .test_common import (
    MOCK_AUTH_RESPONSE,
    MOCK_DEVICE_RESPONSE,
    MOCK_PASSWORD,
    MOCK_USER,
)


def _validators(form: FlowResult) -> dict[str, Any]:
    """Return the validators of the form fields, by field name."""
    return {str(key): value for key, value in form["data_schema"].schema.items()}


async def test_form(hass: HomeAssistant, mock_k1_api: dict[AsyncMock]) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "connector_id": "ST_deadbeef0000",
                "port": 1025,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Elro Connects K1 Connector"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_CONNECTOR_ID: "ST_deadbeef0000",
        CONF_PORT: 1025,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_with_cloud(
    hass: HomeAssistant,
    mock_k1_api: dict[AsyncMock],
    mock_get: AsyncMock,
    mock_post: AsyncMock,
) -> None:
    """Test form with login and fetch info."""
    mock_post.return_value.__aenter__.return_value.json = AsyncMock(
        side_effect=[MOCK_AUTH_RESPONSE]
    )
    mock_get.return_value.__aenter__.return_value.json = AsyncMock(
        side_effect=[MOCK_DEVICE_RESPONSE]
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 1025,
                CONF_USERNAME: MOCK_USER,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Elro Connects K1 Connector"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: 1025,
        CONF_USERNAME: MOCK_USER,
        CONF_PASSWORD: MOCK_PASSWORD,
        CONF_API_KEY: "deadbeefdeadbeefdeadbeefdeadbeef",
        CONF_CONNECTOR_ID: "ST_deadbeef0000",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_with_cloud_error(
    hass: HomeAssistant, mock_k1_api: dict[AsyncMock], mock_post: AsyncMock
) -> None:
    """Test form with login and fetch info."""
    mock_post.return_value.__aenter__.return_value.json = AsyncMock(
        side_effect=TimeoutError
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 1025,
                CONF_USERNAME: MOCK_USER,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.FORM


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (K1.K1ConnectionError, "cannot_connect"),
        (Exception("Some unhandled error"), "unknown"),
    ],
)
async def test_form_cannot_connect(
    hass: HomeAssistant,
    mock_k1_api: dict[AsyncMock],
    side_effect: Exception,
    error: str,
) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_k1_api["connect"].side_effect = side_effect
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "1.1.1.1",
            CONF_CONNECTOR_ID: "ST_deadbeef0000",
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": error}


async def test_already_setup(hass: HomeAssistant, mock_k1_api: dict[AsyncMock]) -> None:
    """Test we cannot create a duplicate setup."""
    # Setup the existing unique config entry
    await test_form(hass, mock_k1_api)

    # Now assert the entry creation is aborted if we try
    # to create an entry with the same unique device_id
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.2",
                CONF_CONNECTOR_ID: "ST_deadbeef0000",
                CONF_PORT: 1024,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.ABORT


async def test_reconfigure(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_k1_api: dict[AsyncMock],
    mock_entry: ConfigEntry,
) -> None:
    """Test we can update the configuration."""
    # Setup the existing config entry
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]

    # Start config flow

    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # Change interval, IP address and port
    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.1.1.2",
                CONF_PORT: 1024,
                CONF_CONNECTOR_ID: "ST_deadbeef0000",
            },
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert config_entry.data.get(CONF_HOST) == "1.1.1.2"
    assert config_entry.data.get(CONF_CONNECTOR_ID) == "ST_deadbeef0000"
    assert config_entry.data.get(CONF_PORT) == 1024


async def test_reconfigure_from_cloud(
    hass: HomeAssistant,
    mock_k1_connector: dict[AsyncMock],
    mock_k1_api: dict[AsyncMock],
    mock_entry: ConfigEntry,
    mock_get: AsyncMock,
    mock_post: AsyncMock,
) -> None:
    """Test we can update the configuration with cloud attributes."""
    mock_post.return_value.__aenter__.return_value.json = AsyncMock(
        side_effect=[MOCK_AUTH_RESPONSE]
    )
    mock_get.return_value.__aenter__.return_value.json = AsyncMock(
        side_effect=[MOCK_DEVICE_RESPONSE]
    )

    # Setup the existing config entry
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]

    # Start config flow

    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # Change IP address and port, fetch api_key FORM the cloud
    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.1.1.2",
                CONF_PORT: 1024,
                CONF_USERNAME: MOCK_USER,
                CONF_PASSWORD: MOCK_PASSWORD,
                CONF_CONNECTOR_ID: "ST_deadbeef0000",
            },
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert config_entry.data.get(CONF_HOST) == "1.1.1.2"
    assert config_entry.data.get(CONF_CONNECTOR_ID) == "ST_deadbeef0000"
    assert config_entry.data.get(CONF_API_KEY) == "deadbeefdeadbeefdeadbeefdeadbeef"
    assert config_entry.data.get(CONF_PORT) == 1024


@pytest.mark.parametrize(
    "side_effect",
    [
        (K1.K1ConnectionError,),
        (Exception("Some unhandled error"),),
    ],
)
async def test_reconfigure_cannot_connect_handling(
    hass: HomeAssistant, mock_k1_api: dict[AsyncMock], side_effect: Exception
) -> None:
    """Test cannot connect when updating the configuration."""
    # Setup the existing config entry
    await test_form(hass, mock_k1_api)

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]

    # Start config flow

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": config_entry.entry_id,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    # Change IP address and port
    mock_k1_api["connect"].side_effect = side_effect
    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.1.1.2",
                CONF_PORT: 1024,
                CONF_CONNECTOR_ID: "ST_deadbeef0000",
            },
        )
    assert result["type"] == FlowResultType.FORM


@pytest.mark.parametrize(
    "translations",
    [
        "strings.json",
        *(
            f"translations/{language}.json"
            for language in ("de", "en", "es", "fr", "nl", "pt", "uk")
        ),
    ],
)
def test_data_descriptions(translations: str) -> None:
    """Test every field of the user and reconfigure step has a description."""
    path = Path(__file__).parent.parent / "custom_components" / DOMAIN / translations
    strings = json.loads(path.read_text(encoding="utf-8"))
    fields = {str(key) for key in ELRO_CONNECTS_DATA_SCHEMA.schema}
    for step in ("user", "reconfigure"):
        step_strings = strings["config"]["step"][step]
        assert set(step_strings["data"]) == fields
        assert set(step_strings["data_description"]) == fields


async def test_secret_fields_hidden(
    hass: HomeAssistant, mock_k1_connector: dict[AsyncMock], mock_entry: ConfigEntry
) -> None:
    """Test the password and API key fields are hidden in both forms."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    user_form = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    reconfigure_form = await mock_entry.start_reconfigure_flow(hass)

    for form in (user_form, reconfigure_form):
        validators = _validators(form)
        for field in (CONF_PASSWORD, CONF_API_KEY):
            assert isinstance(validators[field], TextSelector)
            assert validators[field].config["type"] == TextSelectorType.PASSWORD
        assert not isinstance(validators[CONF_HOST], TextSelector)


async def test_reconfigure_form_suggests_current_data(
    hass: HomeAssistant, mock_k1_connector: dict[AsyncMock], mock_entry: ConfigEntry
) -> None:
    """Test the reconfigure form is filled in with the current data."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    result = await mock_entry.start_reconfigure_flow(hass)
    suggested = {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description
    }
    assert suggested == {
        CONF_HOST: "1.1.1.1",
        CONF_CONNECTOR_ID: "ST_deadbeef0000",
        CONF_PORT: 1025,
    }


async def test_reconfigure_connector_id_read_only(
    hass: HomeAssistant, mock_k1_api: dict[AsyncMock], mock_entry: ConfigEntry
) -> None:
    """Test the connector ID is read only and cannot be changed."""
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    result = await mock_entry.start_reconfigure_flow(hass)
    validators = _validators(result)
    # The form has the same fields in the same order as the user step
    assert list(validators) == [str(key) for key in ELRO_CONNECTS_DATA_SCHEMA.schema]
    assert validators[CONF_CONNECTOR_ID].config["read_only"] is True

    with patch(
        "custom_components.elro_connects.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.1.1.2",
                CONF_PORT: 1025,
                CONF_CONNECTOR_ID: "ST_cafecafe0000",
            },
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_entry.data[CONF_HOST] == "1.1.1.2"
    assert mock_entry.data[CONF_CONNECTOR_ID] == "ST_deadbeef0000"


@pytest.mark.parametrize("language", ["de", "en", "es", "fr", "nl", "pt", "uk"])
def test_exception_translations(language: str) -> None:
    """Test every language translates all exceptions with the same placeholders."""
    base = Path(__file__).parent.parent / "custom_components" / DOMAIN
    strings = json.loads((base / "strings.json").read_text(encoding="utf-8"))
    translations = json.loads(
        (base / "translations" / f"{language}.json").read_text(encoding="utf-8")
    )
    assert set(translations["exceptions"]) == set(strings["exceptions"])
    for key, exception in strings["exceptions"].items():
        placeholders = re.findall(r"{\w+}", exception["message"])
        translated = translations["exceptions"][key]["message"]
        assert re.findall(r"{\w+}", translated) == placeholders


async def test_cloud_login_uses_shared_websession(
    hass: HomeAssistant, mock_k1_api: dict[AsyncMock]
) -> None:
    """Test the cloud login uses the shared aiohttp session of Home Assistant."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "custom_components.elro_connects.config_flow.ElroConnectsSession"
    ) as mock_session:
        mock_session.return_value.async_login = AsyncMock()
        mock_session.return_value.async_get_connectors = AsyncMock(return_value=[])
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 1025,
                CONF_USERNAME: MOCK_USER,
                CONF_PASSWORD: MOCK_PASSWORD,
            },
        )
    mock_session.assert_called_once_with(async_get_clientsession(hass))
