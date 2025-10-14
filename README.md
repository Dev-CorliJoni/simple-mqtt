# simple-mqtt

Compact Python MQTT wrapper around **paho-mqtt**. Focus: clear builder pattern and an explicit split between MQTT v3.1.1 and MQTT v5.

## Installation

```bash
pip install simple-mqtt
```

## Builders

This package exposes two concrete builders:

- `MQTTBuilderV3(client_id, host)` → builds a `MQTTConnectionV3` (MQTT v3.1.1)
- `MQTTBuilderV5(client_id, host)` → builds a `MQTTConnectionV5` (MQTT v5.0)

Both builders provide the same fluent configuration API.

`build()` creates the connection wrapper and prepares the client.  
`fast_build()` equals `build().connect()`.

---

## Quickstart: minimal setup

Connect, subscribe, print messages.

Identical for v3 and v5.
```python
from simplemqtt import MQTTBuilderV3, QualityOfService as QoS  # for v5 swap to MQTTBuilderV5

conn = MQTTBuilderV3(client_id="demo-client", host="localhost").fast_build()

def on_msg(connection, client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload!r} retain={msg.retain} qos={msg.qos}")

conn.subscribe("test/topic", on_message=on_msg, qos=QoS.AtLeastOnce)
conn.publish("test/topic", "hello", qos=QoS.AtLeastOnce, retain=False)

conn.close()
```

---

## Defaults

- Port: `1883`, Keepalive: `60`  
- Clean session: `True`  
- For v5: `SessionExpiryInterval` = 0 by default (non‑persistent). If you call `.persistent_session(True)`, it is set to 3600 seconds.  

---

## Build a connection

### 1) Minimal (constructor + connect)
```python
from simplemqtt import MQTTBuilderV3  # for v5 swap to MQTTBuilderV5

conn = (
    MQTTBuilderV3("client-1", "broker.example.org")
    .fast_build()  # build().connect()
)
```

### 2) With username/password
```python
from simplemqtt import MQTTBuilderV3  # for v5 swap to MQTTBuilderV5

conn = (
    MQTTBuilderV3("client-2", "broker.example.org")
    .login("user", "password")
    .fast_build()
)
```

### 3) Port + keepalive + persistent session + auto‑reconnect
```python
from simplemqtt import MQTTBuilderV3  # for v5 swap to MQTTBuilderV5

conn = (
    MQTTBuilderV3("client-3", "broker.example.org")
    .port(1884)
    .keep_alive(120)
    .persistent_session(True)
    .auto_reconnect(min_delay=1, max_delay=30)
    .fast_build()
)
```

### 4) Last Will (LWT)
```python
from simplemqtt import MQTTBuilderV3, QualityOfService as QoS  # for v5 swap to MQTTBuilderV5

conn = (
    MQTTBuilderV3("client-4", "broker.example.org")
    .last_will("devices/dev42/availability", payload="offline", qos=QoS.AtLeastOnce, retain=True)
    .fast_build()
)
```

### 5) Availability topic
```python
from simplemqtt import MQTTBuilderV3  # for v5 swap to MQTTBuilderV5

conn = (
    MQTTBuilderV3("client-5", "broker.example.org")
    .availability("devices/dev42/availability", payload_online="online", payload_offline="offline")
    .fast_build()
)
```

### 6) TLS (defaults)
```python
from simplemqtt import MQTTBuilderV3  # for v5 swap to MQTTBuilderV5

conn = (
    MQTTBuilderV3("client-6", "broker.example.org")
    .tls()  # verify certificates using system defaults
    .fast_build()
)
```

### 7) TLS with custom CA
```python
from simplemqtt import MQTTBuilderV3  # for v5 swap to MQTTBuilderV5

conn = (
    MQTTBuilderV3("client-7", "broker.example.org")
    .own_tls("/etc/ssl/certs/ca-bundle.pem", allow_insecure=False)
    .fast_build()
)
```

> **TLS capabilities (current):**
>
> - Supported: server TLS with system CAs (`.tls()`), server TLS with custom CA bundle (`.own_tls(ca_certs=...)`), optional hostname skip via `allow_insecure=True`.
> - Not yet wired in the builder: client certificates (`certfile`/`keyfile` mTLS), custom ciphers/TLS versions, WebSockets-specific TLS options. You can still access these via raw `paho-mqtt` if needed.

---

## Use a connection

### Connect

```python
from simplemqtt import MQTTBuilderV3  # for v5 swap to MQTTBuilderV5

conn = MQTTBuilderV3("client-1", "broker.example.org").build()
conn.connect()
# or
conn.connect(blocking=True)
```

### Callbacks (V3)
```python
import logging
from simplemqtt import MQTTBuilderV3
from simplemqtt.mqtt_connections import MQTTConnectionV3

logger = logging.getLogger("Info")

conn = MQTTBuilderV3("client-2", "broker.example.org").fast_build()

def on_connect_v3(connection: MQTTConnectionV3, client, userdata, flags):
    connection.publish("say/hello", "hello :)")

def before_disconnect_v3(connection: MQTTConnectionV3):
    connection.publish("say/hello", "bye :(")

def on_disconnect_v3(client, userdata, rc):
    logger.info("Too late for publishing")

conn.add_on_connect(on_connect_v3)
conn.add_before_disconnect(before_disconnect_v3)
conn.add_on_disconnect(on_disconnect_v3)
```

### Callbacks (V5)
```python
import logging
from simplemqtt import MQTTBuilderV5
from simplemqtt.mqtt_connections import MQTTConnectionV5

logger = logging.getLogger("Info")

conn = MQTTBuilderV5("client-2", "broker.example.org").fast_build()

def on_connect_v5(connection: MQTTConnectionV5, client, userdata, flags, properties):
    connection.publish("say/hello", "hello :)")

def before_disconnect_v5(connection: MQTTConnectionV5):
    connection.publish("say/hello", "bye :(")

def on_disconnect_v5(client, userdata, rc, properties):
    logger.info("Too late for publishing")

conn.add_on_connect(on_connect_v5)
conn.add_before_disconnect(before_disconnect_v5)
conn.add_on_disconnect(on_disconnect_v5)
```

### Subscribe

Identical for v3 and v5.
```python
from simplemqtt import QualityOfService as QoS

def on_msg(connection, client, userdata, msg):
    print(msg.topic, msg.payload)

conn.subscribe("sensors/+/temp", on_message=on_msg, qos=QoS.AtLeastOnce)
```

### Unsubscribe

Identical for v3 and v5.
```python
# Remove one or more filters
conn.unsubscribe("sensors/+/temp", "actuators/#")
```

### Close

Identical for v3 and v5.
```python
conn.close()          # loop_stop + disconnect
```

---

## Protocol specifics

### MQTT v3.1.1

**Publish**
```python
from simplemqtt import QualityOfService as QoS

# Simple
conn.publish("demo/topic", "payload")

# With QoS/retain
conn.publish("demo/topic", "payload", qos=QoS.AtLeastOnce, retain=True)

# Wait for publish completion
conn.publish("demo/topic", "payload", qos=QoS.AtLeastOnce, wait_for_publish=True)
```

**Subscribe**
```python
from simplemqtt import QualityOfService as QoS

def on_msg_v3(connection, client, userdata, msg):
    print("v3:", msg.topic, msg.payload)

conn.subscribe("demo/v3/#", on_message=on_msg_v3, qos=QoS.ExactlyOnce)
```

### MQTT v5

**Build a v5 connection**
```python
from simplemqtt import MQTTBuilderV5
conn = MQTTBuilderV5("client-5", "broker.example.org").fast_build()
```

**Publish** with properties
```python
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes
from simplemqtt import QualityOfService as QoS

props = Properties(PacketTypes.PUBLISH)
props.MessageExpiryInterval = 30  # seconds

# Simple
conn.publish("demo5/topic", "payload-v5")

# With QoS/retain/properties
conn.publish("demo5/topic", "payload-v5", qos=QoS.AtLeastOnce, retain=False, properties=props)

# Wait for completion
conn.publish("demo5/topic", "payload-v5", qos=QoS.AtLeastOnce, wait_for_publish=True, properties=props)
```

**Subscribe** with options
```python
from simplemqtt import QualityOfService as QoS, RetainHandling

def on_msg_v5(connection, client, userdata, msg):
    print("v5:", msg.topic, msg.payload, "retain:", msg.retain)

conn.subscribe(
    "demo5/#",
    on_message=on_msg_v5,
    qos=QoS.AtLeastOnce,
    no_local=True,
    retain_as_published=True,
    retain_handling=RetainHandling.SendRetainedOnNewSubscription,
)
```

---

## Logging

This package uses `logging` with a `NullHandler`. Enable it like this:

```python
import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("simplemqtt").setLevel(logging.DEBUG)
```

## Best practices

- Use a stable `client_id` per device.
- Set LWT (`.last_will(...)`) with QoS ≥ 1 and `retain=True`.
- Enable auto‑reconnect for production.
- For v5, use `retain_handling` and `no_local` to reduce retained floods and pub/sub loops.

## License

MIT (see `LICENSE`).
</file>
