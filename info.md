[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

[![Community Forum][forum-shield]][forum]

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Adds a `device state` sensor, a `battery level` sensor and a `signal` sensor (disabled by default) for each device.
`siren` | Represents Elro Connects alarms as a siren. Turn the siren `ON` to test it. Turn it `OFF` to silence the (test) alarm.

The `device_state` sensor can have of the following states:
- `FAULT`
- `SILENCE`
- `TEST ALARM`
- `FIRE ALARM`
- `ALARM`
- `NORMAL`
- `UNKNOWN`
- `OFFLINE`

Note that the sensors are polled about every 15 seconds. So it might take some time before an alarm state will be propagated. If an unknown state is found that is not supported yet, the hexadecimal code will be assigned as state. Please open an issue [here](https://github.com/jbouwh/lib-elro-connects/issues/new) if a new state needs to be supported.

The `siren` platform (for enabling a test alarm) was tested and is supported for Fire, Heat, CO and Water alarms.

{% if not installed %}

## Installation

1. Click install.
2. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Elro Connects" and add the integration.
3. When the installation via HACS is done, restart Home Assistant.
4. You need the IP-address and your Elro Connects cloud credentials to setup the integration. This will get the `connector_id` and `api_key` for local access of your connector. After the setup has finished setup, the cloud credentials will not be used during operation. Skip this step if you want to do a manual setup.
5. An alternative is a manual setup. For this you need the `connector_id` which can be obtained from the Elro Connects app. Go to the `home` tab and click on the settings wheel. Select `current connector`. A list will be shown with your connectors. The ID starts with `ST_xxx...`.
6. The API key is currently not needed because it is provided by the connector locally. This behavior might change in the future

{% endif %}

***

[integration_blueprint]: https://github.com/jbouwh/ha-elro/connects
[commits-shield]: https://img.shields.io/github/commit-activity/y/jbouwh/ha-elro-connects.svg?style=for-the-badge
[commits]: https://github.com/jbouwh/ha-elro-connects/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license]: https://github.com/jbouwh/ha-elro/connects/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/jbouwh/ha-elro/connects.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jan%20Bouwhuis%20%40jbouwh-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jbouwh/ha-elro/connects.svg?style=for-the-badge
[releases]: https://github.com/jbouwh/ha-elro/connects/releases
[user_profile]: https://github.com/jbouwh
