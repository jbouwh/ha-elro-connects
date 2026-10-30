# ha-elro-connects

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

[![Community Forum][forum-shield]][forum]

# Elro Connects K1
The Elro Connects integration will allow users to integrate their Elro Connects fire, heat, CO, gas, water, or smoke alarms and door/window sensors into Home Assistant. Each alarm is represented by a binary sensor, the main entity of the device, to use in automations. A diagnostic siren entity can be used to test (turn on) and silence (turn off) the alarm. The integration discovers entities (automatically) through an Elro Connects K1 connector plug. The entity names assigned in the Elro Connects app will be synced with Home Assistant.

> There is also a K2 connector available, but this K2 connector will not work with this software.

The integration only supports the Elro Connects K1 connector (SF40GA) mainly sold in Germany, the Netherlands, Belgium and France. The manufactor of this connector is Siterwell, and its products are also sold under the name FamilyWell Smart Security EcoSystem (gateway product GS188A). This integration support the legacy gateway, not the new generation that is working via Tuya using a zigbee gateway.
The integration is not tested with the Siterwell branded devices, but some user reports indicate this is working too.

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Adds an alarm sensor for each alarm (device class `carbon_monoxide`, `gas`, `heat`, `moisture` or `smoke`) and an `opening` sensor for each door/window sensor. This is the main entity of the device and is named after the device. Each of these devices also gets a `problem` and a low `battery` diagnostic sensor, which are disabled by default.
`sensor` | Adds a `device state`, a `battery level` and a `signal` (disabled by default) diagnostic sensor for each device.
`siren` | A diagnostic entity to test the alarm. Turn the siren `ON` to test it. Turn it `OFF` to silence the (test) alarm.

The `device_state` sensor can have of the following states:
- `fault`
- `silence`
- `test_alarm`
- `fire_alarm`
- `alarm`
- `normal`
- `unknown`
- `offline`
- `open`
- `closed`
- `low_battery`
- `temperature_alarm`

Note that the sensors are polled about every 15 seconds. So it might take some time before an alarm state will be propagated. If a device reports a state that is not supported yet, the `device_state` sensor is `unknown` and a warning with the hexadecimal code is logged. Please open an issue [here](https://github.com/jbouwh/lib-elro-connects/issues/new) if a new state needs to be supported.

If the name of the device is changed in HA, it is also updated in the Elro Connects app. Note the name has a 15 character length limit.

The alarm binary sensor is `on` when the device reports `alarm`, `fire_alarm` or `temperature_alarm`. A test alarm does not turn it on, so testing an alarm does not trigger your alarm automations. The `problem` sensor is `on` when the device reports `fault`, and the `battery` sensor is `on` when the device reports `low_battery`. Note that a device reports one state at a time. The door/window `opening` sensor is `on` when the door or window is open, and `unknown` while the sensor reports another state, such as `low_battery`.

Example automation that sends a notification when a smoke alarm goes off:

```yaml
automation:
  - alias: "Smoke alarm"
    triggers:
      - trigger: state
        entity_id: binary_sensor.beganegrond
        to: "on"
    actions:
      - action: notify.notify
        data:
          message: "Smoke detected: {{ trigger.to_state.name }}"
```

The `siren` platform (for enabling a test alarm) was tested and is supported for Fire, Heat, CO and Water alarms.

## Installation

### Using HACS

1. Install the [Home Assistant Community Store (HACS)](https://hacs.xyz/docs/setup/download).
2. Select `integration` as category and click `+` to add an integration.
3. Find and install install Elro Connects via HACS.
4. When the installation via HACS is done, restart Home Assistant.
5. In the HA UI go to `Configuration` -> `Integrations` click `+` and search for `Elro Connects`

### Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `elro_connects`.
4. Download _all_ the files from the `custom_components/elro_connects/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to `Configuration` -> `Integrations` click `+` and search for `Elro Connects`

Using your HA configuration directory (folder) as a starting point you should now also have something like this:

#### Configuring the integration

1. You need the IP-address and your Elro Connects cloud credentials (`username` and `password`) to setup the integration. This will get the `connector_id` and `api_key` for local access of your connector. After the setup has finished setup, the cloud credentials will not be used during operation.
2. An alternative is a manual setup. For this you need to fill in the `connector_id`, leave `username` and `password` fields open. which can be obtained from the Elro Connects app. Go to the `home` tab and click on the settings wheel. Select `current connector`. A list will be shown with your connectors. The ID starts with `ST_xxx...`.
3. The API key is probably not needed as long as it is provided by the connector locally. This behavior might change in the future.
4. To change the host, port or credentials later, select `Reconfigure` in the menu of the integration entry.


```text
custom_components/elro_connects/translations/en.json
custom_components/elro_connects/translations/nl.json
custom_components/elro_connects/__init__.py
custom_components/elro_connects/api.py
custom_components/elro_connects/binary_sensor.py
custom_components/elro_connects/sensor.py
custom_components/elro_connects/siren.py
custom_components/elro_connects/config_flow.py
custom_components/elro_connects/const.py
custom_components/elro_connects/manifest.json
...
```

## Removing devices

Devices are not removed automatically. The K1 connector sends each device in a separate UDP message, so a device can be missing from a single update without being removed from the connector. When a device is removed from the connector in the Elro Connects app, it can be deleted in Home Assistant: open the device page, select the menu (⋮) and select `Delete`. This is only possible when the connector no longer reports the device.

## Removing the integration

This integration follows standard integration removal, no extra steps are required.

1. Go to `Settings` -> `Devices & services` and select the `Elro Connects` integration.
2. Select the menu (⋮) of the integration entry and select `Delete`.
3. If the integration was installed with HACS, it can be removed in HACS as well, and Home Assistant needs a restart.

## Configuration is done in the UI

<!---->


***

[elro_connects]: https://github.com/jbouwh/ha-elro-connects
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/custom-components/blueprint.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jan%20Bouwhuis-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/jbouwh/ha-elro-connects?include_prereleases&style=for-the-badge
[releases]: https://github.com/jbouwh/ha-elro-connects/releases
