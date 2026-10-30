# ha-elro-connects

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

[![Community Forum][forum-shield]][forum]

# Elro Connects K1
The Elro Connects integration will allow users to integrate their Elro Connects fire, heat, CO, gas, water, or smoke alarms, door/window sensors and sockets into Home Assistant. Each alarm is represented by a binary sensor, the main entity of the device, to use in automations. A diagnostic siren entity can be used to test (turn on) and silence (turn off) the alarm. The integration discovers entities (automatically) through an Elro Connects K1 connector plug. The entity names assigned in the Elro Connects app will be synced with Home Assistant.

> There is also a K2 connector available, but this K2 connector will not work with this software.

The integration only supports the Elro Connects K1 connector (SF40GA) mainly sold in Germany, the Netherlands, Belgium and France. The manufacturer of this connector is Siterwell, and its products are also sold under the name FamilyWell Smart Security EcoSystem (gateway product GS188A). This integration supports the legacy gateway, not the new generation that is working via Tuya using a zigbee gateway.
The integration is not tested with the Siterwell branded devices, but some user reports indicate this is working too.

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Adds an alarm sensor for each alarm (device class `carbon_monoxide`, `gas`, `heat`, `moisture` or `smoke`) and an `opening` sensor for each door/window sensor. This is the main entity of the device and is named after the device. Each of these devices also gets a `problem` and a low `battery` diagnostic sensor, which are disabled by default.
`sensor` | Adds a `device state`, a `battery level` and a `signal` (disabled by default) diagnostic sensor for each device.
`siren` | A diagnostic entity to test the alarm. Turn the siren `ON` to test it. Turn it `OFF` to silence the (test) alarm.
`switch` | Adds a switch for each socket.

The `device_state` sensor can have one of the following states:
- `fault`
- `silence`
- `test_alarm`
- `fire_alarm`
- `alarm`
- `normal`
- `unknown`
- `open`
- `closed`
- `low_battery`
- `temperature_alarm`

When a device is offline, or the connector cannot be reached, its entities are unavailable.

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

## Use cases

- **Get warned when an alarm goes off.** Trigger an automation on the alarm binary sensor, as in the example above. A critical notification of the Home Assistant Companion app also comes through when the phone is muted.
- **Make the house safe during a fire or CO alarm.** Turn on the lights to light the escape routes, and stop the ventilation or the heating, so smoke or carbon monoxide is not spread through the house.
- **Limit water damage.** When a water alarm goes off, close a smart water valve and send a notification.
- **Use the door and window sensors.** Turn off the heating in a room when a window is open, or use the opening sensors in an alarm panel.
- **Keep the alarms working.** Enable the `problem` and `battery` diagnostic sensors to get a notification when an alarm has a fault or a low battery. Use the `siren` to test the alarms regularly. A test alarm does not turn on the alarm binary sensor, so it does not trigger your alarm automations.

Example automation that tests an alarm on the first Saturday of the month. Note that the alarm sounds during the test:

```yaml
automation:
  - alias: "Monthly alarm test"
    triggers:
      - trigger: time
        at: "11:00:00"
    conditions:
      - condition: template
        value_template: "{{ now().weekday() == 5 and now().day <= 7 }}"
    actions:
      - action: siren.turn_on
        target:
          entity_id: siren.beganegrond_test_alarm
      - delay: "00:00:10"
      - action: siren.turn_off
        target:
          entity_id: siren.beganegrond_test_alarm
```

## Installation

### Using HACS

1. Install the [Home Assistant Community Store (HACS)](https://hacs.xyz/docs/use/download/download/).
2. Search for `Elro Connects` in HACS and download it.
3. Restart Home Assistant.
4. Go to `Settings` -> `Devices & services`, select `Add integration` and search for `Elro Connects`.

### Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `elro_connects`.
4. Download _all_ the files from the `custom_components/elro_connects/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. Go to `Settings` -> `Devices & services`, select `Add integration` and search for `Elro Connects`.

Using your HA configuration directory (folder) as a starting point you should now also have something like this:

```text
custom_components/elro_connects/translations/en.json
custom_components/elro_connects/translations/nl.json
...
custom_components/elro_connects/__init__.py
custom_components/elro_connects/binary_sensor.py
custom_components/elro_connects/config_flow.py
custom_components/elro_connects/const.py
custom_components/elro_connects/coordinator.py
custom_components/elro_connects/diagnostics.py
custom_components/elro_connects/entity.py
custom_components/elro_connects/helpers.py
custom_components/elro_connects/icons.json
custom_components/elro_connects/manifest.json
custom_components/elro_connects/sensor.py
custom_components/elro_connects/siren.py
custom_components/elro_connects/strings.json
custom_components/elro_connects/switch.py
```

## Configuring the integration

The integration is set up in the UI. It needs the following parameters:

Parameter | Description
-- | --
`host` | The hostname or IP address of the K1 connector in your local network.
`port` | The UDP port of the K1 connector. The default port `1025` works in most cases.
`username` and `password` | Optional. The account of the Elro Connects app. When given, the `connector_id` and `api_key` are fetched from the cloud. The credentials are stored in the config entry, but are only used during setup and reconfiguration, not during operation.
`connector_id` | The ID of the connector, which starts with `ST_`. Not needed when you log in with your account. In the Elro Connects app, go to the `home` tab, open the settings and select `current connector`. A list with your connectors is shown.
`api_key` | Optional. Only needed if the connector does not provide the key locally. It is filled in automatically when you log in with your account.

To change the host, port or credentials later, select `Reconfigure` in the menu (⋮) of the integration entry. The connector ID cannot be changed. To use another connector, add a new integration entry.

## Troubleshooting

- If the connector cannot be reached, all entities are unavailable and Home Assistant retries the connection. Check that the host and port are correct, and that the connector is online in the Elro Connects app.
- To get more details, enable debug logging on the integration page (`Enable debug logging`), or add this to `configuration.yaml`:

  ```yaml
  logger:
    logs:
      custom_components.elro_connects: debug
      elro: debug
  ```

- When opening an [issue](https://github.com/jbouwh/ha-elro-connects/issues), please attach the diagnostics: open the integration entry, select the menu (⋮) and select `Download diagnostics`. Credentials and the API key are removed, and the MAC address of the connector is masked.

## Removing devices

Devices are not removed automatically. The K1 connector sends each device in a separate UDP message, so a device can be missing from a single update without being removed from the connector. When a device is removed from the connector in the Elro Connects app, it can be deleted in Home Assistant: open the device page, select the menu (⋮) and select `Delete`. This is only possible when the connector no longer reports the device.

## Removing the integration

This integration follows standard integration removal, no extra steps are required.

1. Go to `Settings` -> `Devices & services` and select the `Elro Connects` integration.
2. Select the menu (⋮) of the integration entry and select `Delete`.
3. If the integration was installed with HACS, it can be removed in HACS as well, and Home Assistant needs a restart.

***

[elro_connects]: https://github.com/jbouwh/ha-elro-connects
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/jbouwh/ha-elro-connects.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jan%20Bouwhuis-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/v/release/jbouwh/ha-elro-connects?include_prereleases&style=for-the-badge
[releases]: https://github.com/jbouwh/ha-elro-connects/releases
