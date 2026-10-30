"""Print the requirements needed to run Home Assistant in the dev container.

Collects the requirements of the integrations Home Assistant sets up at
startup and all their (after) dependencies from the manifests of the
installed Home Assistant package. These are the integrations that are always
loaded, the domains and platforms in the configuration, the integrations with
a config entry and the integrations given on the command line. This makes
sure the dependencies are installed up front, instead of relying on Home
Assistant to install them at startup.

Usage: ha_requirements.py CONFIG_DIR [DOMAIN ...]
"""

import json
from pathlib import Path
import sys

import homeassistant
from homeassistant import bootstrap
from homeassistant.const import BASE_PLATFORMS
from homeassistant.util.yaml import load_yaml_dict

HA_COMPONENTS = Path(homeassistant.__file__).parent / "components"
CUSTOM_COMPONENTS = Path(__file__).parent.parent / "custom_components"

ALWAYS_LOADED = (
    bootstrap.CORE_INTEGRATIONS
    | bootstrap.LOGGING_AND_HTTP_DEPS_INTEGRATIONS
    | bootstrap.FRONTEND_INTEGRATIONS
    | bootstrap.DEFAULT_INTEGRATIONS
)


def _manifest(domain: str) -> dict:
    """Return the manifest of a custom or built-in integration."""
    for path in (CUSTOM_COMPONENTS, HA_COMPONENTS):
        manifest = path / domain / "manifest.json"
        if manifest.exists():
            return json.loads(manifest.read_text(encoding="utf-8"))
    return {}


def config_domains(config_dir: Path) -> set[str]:
    """Return the domains in the configuration and of the config entries."""
    domains: set[str] = set()
    if (configuration := config_dir / "configuration.yaml").exists():
        config = load_yaml_dict(configuration)
        for key, domain_config in config.items():
            # Strip the label from keys like "sensor my_label"
            domain = key.split(" ")[0]
            domains.add(domain)
            if domain not in BASE_PLATFORMS:
                continue
            items = domain_config if isinstance(domain_config, list) else []
            domains.update(
                item["platform"]
                for item in items
                if isinstance(item, dict) and "platform" in item
            )
    if (entries := config_dir / ".storage" / "core.config_entries").exists():
        data = json.loads(entries.read_text(encoding="utf-8"))["data"]
        domains.update(entry["domain"] for entry in data["entries"])
    return domains


def collect_requirements(domains: set[str]) -> list[str]:
    """Collect the requirements of the integrations and their dependencies."""
    requirements: set[str] = set()
    seen: set[str] = set()
    todo = list(domains)
    while todo:
        if (domain := todo.pop()) in seen:
            continue
        seen.add(domain)
        manifest = _manifest(domain)
        requirements.update(manifest.get("requirements", []))
        todo.extend(manifest.get("dependencies", []))
        todo.extend(manifest.get("after_dependencies", []))
    return sorted(requirements)


if __name__ == "__main__":
    domains = ALWAYS_LOADED | config_domains(Path(sys.argv[1])) | set(sys.argv[2:])
    print("\n".join(collect_requirements(domains)))  # noqa: T201
