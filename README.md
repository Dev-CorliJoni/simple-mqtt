# simple-mqtt

Compact Python mqtt wrapper around **paho-mqtt**. Focus: clear builder pattern, clean split between MQTT v3.1.1 and v5.

## Installation

```bash
pip install simple-mqtt
```

## Builder Pattern

`MqttBuilder(client_id, host, protocol)` encapsulates connection options. Configure via method chaining. `build()` returns:
- `MQTTConnectionV3` when `protocol != mqtt.MQTTv5`
- `MQTTConnectionV5` when `protocol == mqtt.MQTTv5`

## Quickstart: Minimal setup

Connect, subscribe, print messages.

```python
from simplemqtt import MqttBuilder, QualityOfService as QoS

conn = MqttBuilder(client_id="demo-client", host="localhost").fast_build()

def on_msg(connection, client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload!r} retain={msg.retain} qos={msg.qos}")

conn.subscribe("test/topic", on_message=on_msg, qos=QoS.AtLeastOnce)
conn.publish("test/topic", "hello", qos=QoS.AtLeastOnce, retain=False)

conn.close()
```

---

# How to get a valid connection

All variants build first, then `connect()`.

> **Defaults:** Protocol = v311, Port `1883`, keepalive `60`, clean session `True`. For v5 a `SessionExpiryInterval=3600` is set.

### 1) Minimal (constructor + connect)

```python
from simplemqtt import MqttBuilder

conn = (
    MqttBuilder("client-1", "broker.example.org")
    .fast_build() # fast_build() = build().connect()
)
```

### 2) With username/password

```python
from simplemqtt import MqttBuilder

conn = (
    MqttBuilder("client-2", "broker.example.org")
    .login("user", "password")
    .fast_build()
)
```

### 3) Port + keepalive + persistent session + auto‑reconnect

```python
import paho.mqtt.client as mqtt
from simplemqtt import MqttBuilder

conn = (
    MqttBuilder("client-3", "broker.example.org", protocol=mqtt.MQTTv311)
    .port(1884)
    .keep_alive(120)
    .persistent_session(True)
    .auto_reconnect(min_delay=1, max_delay=30)
    .fast_build()
)
```

### 4) Last Will (LWT)

```python
from simplemqtt import MqttBuilder, QualityOfService as QoS

conn = (
    MqttBuilder("client-4", "broker.example.org")
    .last_will("devices/dev42/availability", payload="offline", qos=QoS.AtLeastOnce, retain=True)
    .fast_build()
)
```

### 5) Availability topic (includes LWT + online/offline)

Creates an availability topic

```python
from simplemqtt import MqttBuilder

conn = (
    MqttBuilder("client-5", "broker.example.org")
    .availability("devices/dev42/availability", payload_online="online", payload_offline="offline")
    .fast_build()
)
```

### 6) TLS (defaults)

```python
from simplemqtt import MqttBuilder

conn = (
    MqttBuilder("client-6", "broker.example.org")
    .tls()  # verify certificates
    .fast_build()
)
```

### 7) TLS with custom CA

```python
from simplemqtt import MqttBuilder

conn = (
    MqttBuilder("client-7", "broker.example.org")
    .own_tls("/etc/ssl/certs/ca-bundle.pem", allow_insecure=False)
    .fast_build()
)
```

---

# How to use a connection

## Common operations (v3 and v5)

### Connect

```python
from simplemqtt import MqttBuilder

conn = MqttBuilder("client-1", "broker.example.org").build()
    
# Non-blocking (recommended for apps with own threading)
conn.connect()

# Blocking (runs until disconnect)
conn.connect(blocking=True)
```

### Use callbacks V3

```python
import logging
from simplemqtt import MqttBuilder
from simplemqtt.mqtt_connections import MQTTConnectionV3

logger = logging.getLogger("Info")

conn = MqttBuilder("client-2", "broker.example.org").fast_build()

def on_connect_v3(connection: MQTTConnectionV3, client, userdata, flags):
    connection.publish("say/hello", "hello :)")

def before_disconnect_v3(connection: MQTTConnectionV3):
    connection.publish("say/hello", "bye :(")

def on_disconnect_v3(client, userdata, rc):
    logger.info("To late for publishing")
    
conn.add_on_connect(on_connect_v3)
conn.add_before_disconnect(before_disconnect_v3)
conn.add_on_disconnect(on_disconnect_v3)

```

### Use callbacks V3

```python
import logging
from simplemqtt import MqttBuilder
from simplemqtt.mqtt_connections import MQTTConnectionV5

logger = logging.getLogger("Info")

conn = MqttBuilder("client-2", "broker.example.org").fast_build()

def on_connect_v5(connection: MQTTConnectionV5, client, userdata, flags, properties):
    connection.publish("say/hello", "hello :)")

def before_disconnect_v5(connection: MQTTConnectionV5):
    connection.publish("say/hello", "bye :(")

def on_disconnect_v5(client, userdata, rc, properties):
    logger.info("To late for publishing")
    
conn.add_on_connect(on_connect_v5)
conn.add_before_disconnect(before_disconnect_v5)
conn.add_on_disconnect(on_disconnect_v5)
```

### Subscribe

```python
from simplemqtt import QualityOfService as QoS

def on_msg(connection, client, userdata, msg):
    print(msg.topic, msg.payload)

conn.subscribe("sensors/+/temp", on_message=on_msg, qos=QoS.AtLeastOnce)
```

### Unsubscribe

```python
# Remove one or more filters;
conn.unsubscribe("sensors/+/temp", "actuators/#")
```

### Close

```python
conn.close()          # loop_stop + disconnect
# conn.close(force=True)   # stop loop immediately
```

## Protocol-specific

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

> Build with v5 to get a v5 connection:
>
> ```python
> import paho.mqtt.client as mqtt
> from simplemqtt import MqttBuilder
> conn = MqttBuilder("client-5", "broker.example.org", protocol=mqtt.MQTTv5).fast_build()
> ```

**Publish** with properties

```python
import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes
from simplemqtt import QualityOfService as QoS

props = Properties(PacketTypes.PUBLISH)
props.MessageExpiryInterval = 30   # seconds
# More properties: ContentType, ResponseTopic, CorrelationData, UserProperty, ...

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

# no_local: do not receive own publishes
# retain_handling: e.g. only deliver retained on new subscription
conn.subscribe(
    "demo5/#",
    on_message=on_msg_v5,
    qos=QoS.AtLeastOnce,
    no_local=True,
    retain_as_published=True,
    retain_handling=RetainHandling.SendRetainedOnNewSubscription
)
```

---

## Logging

The package uses `logging` with a `NullHandler`. Enable it like this:

```python
import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("simplemqtt").setLevel(logging.DEBUG)
```

## Best practices

- Use a stable `client_id` per device.
- Set LWT (`.last_will(...)`) with QoS≥1 and `retain=True`.
- Enable auto‑reconnect for production.
- For v5 use `retain_handling` and `no_local` to reduce retained floods and pub/sub loops.

## License

MIT (see `LICENSE`).

