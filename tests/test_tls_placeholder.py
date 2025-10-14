import os
import pytest


@pytest.mark.skipif(not (os.environ.get("MQTT_TLS_CA") or os.environ.get("MQTT_USE_TLS")),
                    reason="TLS not configured; test intentionally skipped")
def test_tls_connect_placeholder():
    # Intentionally empty. Enable once a TLS-capable broker is available.
    assert True
