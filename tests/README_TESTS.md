# Live Tests Against a Real MQTT Broker

## Required Environment Variables

Required:
- `MQTT_CLIENT_ID`  
- `MQTT_HOST`

Optional:
- `MQTT_PORT` (default 1883)
- `MQTT_KEEPALIVE` (default 60)
- `MQTT_USERNAME`, `MQTT_PASSWORD`
- `MQTT_PROTOCOL` (`MQTTv311` or `MQTTv5`)
- `MQTT_MIN_RECONNECT`, `MQTT_MAX_RECONNECT`
- `MQTT_PERSISTENT_SESSION` (`1`/`true`...)
- `MQTT_TLS_CA` or `MQTT_USE_TLS=1` -> enables TLS tests (skipped otherwise)
- `MQTT_AVAILABILITY_TOPIC`
- `MQTT_TEST_TOPIC` (base prefix for topics, otherwise `${CLIENT_ID}/tests`)
- `MQTT_QOS` (default 1)
- `MQTT_RETAIN` (default 0)

## Start

CLI:
```bash
export MQTT_CLIENT_ID=demo-client
export MQTT_HOST=localhost
pytest
```

# Quick PyCharm Setup

1) Run/Debug Configuration -> `pytest`.  
2) Working directory = project root.  
3) Set environment variables. Recommendation: create a `.env` in the root and enable "Load variables from ..." in the configuration. Example:

    ```
    MQTT_CLIENT_ID=demo-client
    MQTT_HOST=localhost
    MQTT_PORT=1883
    MQTT_KEEPALIVE=60
    MQTT_TEST_TOPIC=demo/devices/test
    ```

4) Click `Apply` and start the run configuration.

# Notes

- Tests use a session-wide connection (the `connection` fixture). Some specialized tests open short-lived connections.  
- Topics are unique per test case (`uuid`). Retained messages are cleared best-effort at the end without broker-specific logic.  
- TLS: the placeholder test remains skipped until `MQTT_TLS_CA` or `MQTT_USE_TLS` is set.  
- Availability: if `MQTT_AVAILABILITY_TOPIC` is set, the builder publishes "online" on connect and "offline" before disconnect. The tests do not rely on broker will semantics.  

If you need additional scenarios (QoS 2, no_local, v5 properties), let me know and the suite can be extended accordingly.
