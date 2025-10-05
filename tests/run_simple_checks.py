"""Local smoke test for the simple-mqtt package.

Run this module with `python tests/run_simple_checks.py` to trigger a few quick
checks against the package without shipping anything in the pip distribution.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Ensure the project root is on sys.path so we can import the local package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


"""
Nginx confi für tls testing
stream {
    upstream mqtt_upstream { server 127.0.0.1:1883; }
    server {
        listen 8883 ssl;
        ssl_certificate     /etc/ssl/certs/fullchain.pem;
        ssl_certificate_key /etc/ssl/private/privkey.pem;
        proxy_pass mqtt_upstream;
    }
}
"""


def main() -> int:
    print("== simple-mqtt smoke test ==")

    try:
        mqtt_module = importlib.import_module("simplemqtt.mqtt")
    except ModuleNotFoundError as exc:
        print("! Failed to import simplemqtt.mqtt:", exc)
        return 1

    print("Imported simplemqtt.mqtt successfully.")
    exported_names = sorted(name for name in dir(mqtt_module) if not name.startswith("__"))
    if exported_names:
        print("Exported symbols:")
        for name in exported_names:
            print(f"  - {name}")
    else:
        print("Module does not expose any public symbols yet.")

    try:
        import importlib.metadata as metadata

        version = metadata.version("simple-mqtt")
        print(f"Installed package version: {version}")
    except ModuleNotFoundError:
        print("`importlib.metadata` not available; skipping version lookup.")
    except metadata.PackageNotFoundError:
        print("Package metadata not found. Did you install the project with pip?")

    print("Smoke test finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
