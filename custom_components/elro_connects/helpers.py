"""Helper functions for Elro Connects."""

from elro.device import ATTR_DEVICE_TYPE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ELRO_CONNECTS_NEW_DEVICE
from .coordinator import ElroConnectsConfigEntry


@callback
def async_set_up_discovery_helper(
    hass: HomeAssistant,
    entity_class: type,
    entry: ElroConnectsConfigEntry,
    current: set[int],
    descriptions: dict[str, EntityDescription],
    async_add_entities: AddEntitiesCallback,
):
    """Help to set up an entity."""

    @callback
    def _async_add_entities():
        coordinator = entry.runtime_data
        device_data: dict[int, dict] = coordinator.connector_data
        if not device_data:
            return
        new_items = []
        for device_id, attributes in device_data.items():
            # description
            if device_id in current:
                continue
            if ATTR_DEVICE_TYPE not in attributes:
                # Skip a data update if there is no device type attribute provided
                continue
            # Ensure we only add entities once
            current.add(device_id)
            device_type = attributes[ATTR_DEVICE_TYPE]
            if device_type in descriptions:
                new_item = entity_class(
                    coordinator, device_id, descriptions[device_type]
                )
                new_items.append(new_item)
            else:
                for attribute in attributes:
                    if attribute in descriptions:
                        new_item = entity_class(
                            coordinator, device_id, descriptions[attribute]
                        )
                        new_items.append(new_item)

        async_add_entities(new_items)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            ELRO_CONNECTS_NEW_DEVICE.format(entry.entry_id),
            _async_add_entities,
        )
    )
    # Initial setup on first fetch
    _async_add_entities()
