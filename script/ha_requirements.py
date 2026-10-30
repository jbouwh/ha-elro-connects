"""Print the requirements needed to run Home Assistant in the dev container.

Collects the requirements of the given integrations and all their
(after) dependencies from the manifests of the installed Home Assistant
package. This makes sure the dependencies are installed up front, instead
of relying on Home Assistant to install them at startup.
"""

import json
from pathlib import Path
import sys

import homeassistant

HA_COMPONENTS = Path(homeassistant.__file__).parent / "components"
CUSTOM_COMPONENTS = Path(__file__).parent.parent / "custom_components"


def _manifest(domain: str) -> dict:
    """Return the manifest of a custom or built-in integration."""
    for path in (CUSTOM_COMPONENTS, HA_COMPONENTS):
        manifest = path / domain / "manifest.json"
        if manifest.exists():
            return json.loads(manifest.read_text(encoding="utf-8"))
    return {}


def collect_requirements(domains: list[str]) -> list[str]:
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
    print("\n".join(collect_requirements(sys.argv[1:])))  # noqa: T201
