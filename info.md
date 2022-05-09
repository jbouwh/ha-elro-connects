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

{% if not installed %}

## Installation

1. Click install.
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Elro Connects".

{% endif %}

***

[integration_blueprint]: https://github.com/jbouwh/ha-elro/connects
[commits-shield]: https://img.shields.io/github/commit-activity/y/jbouwh/ha-elro/connects.svg?style=for-the-badge
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
