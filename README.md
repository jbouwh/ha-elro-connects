# ha-elro-connects

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

[![Community Forum][forum-shield]][forum]

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Adds a `device state` sensor, a `battery level` sensor and a `signal` sensor (disabled by default) for each device.
`siren` | Represents Elro Connects alarms as a siren. Turn the siren `ON` to test it. Turn it `OFF` to silence the (test) alarm.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `elro_connects`.
4. Download _all_ the files from the `custom_components/elro_connects/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Elro Connects"

Using your HA configuration directory (folder) as a starting point you should now also have something like this:

```text
custom_components/elro_connects/translations/en.json
custom_components/elro_connects/translations/nl.json
custom_components/elro_connects/__init__.py
custom_components/elro_connects/api.py
custom_components/elro_connects/sensor.py
custom_components/elro_connects/siren.py
custom_components/elro_connects/config_flow.py
custom_components/elro_connects/const.py
custom_components/elro_connects/manifest.json
...
```

## Configuration is done in the UI

<!---->


***

[elro_connects]: https://github.com/jbouwh/ha-elro-connects
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/custom-components/blueprint.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jan%20Bouwhuis-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/elro_connects/blueprint.svg?style=for-the-badge
[releases]: https://github.com/jbouwh/ha-elro-connects/releases
