from __future__ import annotations
import os
import time
import uuid
import queue
import threading
import pytest
import paho.mqtt.client as mqtt

from simplemqtt import MQTTBuilderV3
from simplemqtt.types import QualityOfService as QoS

REQUIRED_KEYS = ("MQTT_CLIENT_ID", "MQTT_HOST")


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def broker_env():
    missing = [k for k in REQUIRED_KEYS if k not in os.environ]
    if missing:
        pytest.skip(f"Missing environment variables: {', '.join(missing)}")
    return {
        "client_id": os.environ["MQTT_CLIENT_ID"],
        "host": os.environ["MQTT_HOST"],
        "port": int(os.environ.get("MQTT_PORT", 1883)),
        "keepalive": int(os.environ.get("MQTT_KEEPALIVE", 60)),
        "username": os.environ.get("MQTT_USERNAME"),
        "password": os.environ.get("MQTT_PASSWORD"),
        "min_reconnect": os.environ.get("MQTT_MIN_RECONNECT"),
        "max_reconnect": os.environ.get("MQTT_MAX_RECONNECT"),
        "persistent": _bool_env("MQTT_PERSISTENT_SESSION"),
        "tls_ca": os.environ.get("MQTT_TLS_CA"),
        "use_tls": _bool_env("MQTT_USE_TLS"),
        "availability_topic": os.environ.get("MQTT_AVAILABILITY_TOPIC"),
        "base_test_topic": os.environ.get("MQTT_TEST_TOPIC"),
        "qos": int(os.environ.get("MQTT_QOS", 1)),
        "retain": _bool_env("MQTT_RETAIN", False),
    }


@pytest.fixture(scope="session")
def mqtt_builder(broker_env):
    b = MQTTBuilderV3(broker_env["client_id"], broker_env["host"])
    b.port(broker_env["port"]).keep_alive(broker_env["keepalive"])

    if broker_env["username"] and broker_env["password"]:
        b.login(broker_env["username"], broker_env["password"])

    if broker_env["min_reconnect"] and broker_env["max_reconnect"]:
        b.auto_reconnect(min_delay=int(broker_env["min_reconnect"]), max_delay=int(broker_env["max_reconnect"]))

    if broker_env["persistent"]:
        b.persistent_session(True)

    if broker_env["tls_ca"]:
        b.own_tls(broker_env["tls_ca"])
    elif broker_env["use_tls"]:
        b.tls()

    if broker_env["availability_topic"]:
        b.availability(broker_env["availability_topic"], "online", "offline", QoS.AtLeastOnce, True)

    yield b


@pytest.fixture(scope="session")
def connection(mqtt_builder, broker_env):
    # Deterministic "connected" signal
    connected = threading.Event()

    def _mark_connected(*_args, **_kwargs):
        connected.set()

    connection = mqtt_builder.build()
    if hasattr(connection, "add_on_connect"):
        connection.add_on_connect(_mark_connected)

    connection.connect()
    assert connected.wait(timeout=10), "Connect timeout"

    yield connection
    connection.close()


@pytest.fixture(scope="session")
def topic_registry():
    """
    Thread-safe registry of all concrete topics created by tests.
    Used once after the suite to clear retained messages.
    """
    s = set()
    lock = threading.Lock()

    def add(topic: str):
        with lock:
            s.add(topic)

    def snapshot() -> set[str]:
        with lock:
            return set(s)

    return {"add": add, "snapshot": snapshot}


@pytest.fixture()
def unique_topic(broker_env, topic_registry):
    base = broker_env["base_test_topic"] or f"{broker_env['client_id']}/tests"

    def _mk(suffix: str = ""):
        u = uuid.uuid4().hex[:8]
        t = f"{base}/{suffix}/{u}" if suffix else f"{base}/{u}"
        topic_registry["add"](t)
        return t

    return _mk


@pytest.fixture()
def msg_queue():
    return queue.Queue()


def wait_for(q: queue.Queue, timeout: float = 5.0):
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        pytest.fail("Timeout: no message received")


@pytest.fixture(scope="session", autouse=True)
def after_all_clear_retained(broker_env, topic_registry):
    """
    Single end-of-suite retained clear.

    Clears:
      - all recorded concrete topics
      - the base prefix topic itself
      - the availability topic (if configured)

    Strategy:
      1) Publish retained-empty to each target (QoS 0 is sufficient and widely compatible).
      2) Verify by subscribing to all targets and collecting retained deliveries with non-empty payload.
         If any remain, publish retained-empty again once.
    """
    yield

    base = broker_env["base_test_topic"] or f"{broker_env['client_id']}/tests"
    targets = topic_registry["snapshot"]() | {base}

    if broker_env.get("availability_topic"):
        targets.add(broker_env["availability_topic"])

    sweeper = MQTTBuilderV3(f"{broker_env['client_id']}-sweep", broker_env["host"]) \
        .port(broker_env["port"]).keep_alive(broker_env["keepalive"])

    if broker_env["username"] and broker_env["password"]:
        sweeper.login(broker_env["username"], broker_env["password"])
    if broker_env["tls_ca"]:
        sweeper.own_tls(broker_env["tls_ca"])
    elif broker_env["use_tls"]:
        sweeper.tls()

    conn = sweeper.build().connect()

    # Phase 1: clear by publishing retained-empty
    for t in list(targets):
        try:
            conn.publish(t, b"", qos=QoS.AtMostOnce, retain=True, wait_for_publish=True)
        except Exception:
            pass

    time.sleep(0.2)  # allow broker to process retained updates

    # Phase 2: verify and re-clear any that still deliver retained with payload
    remaining: set[str] = set()

    def _collect(_conn, _c, _u, msg):
        # If a retained message with a non-empty payload is delivered, it is not cleared
        if getattr(msg, "retain", False) and msg.payload:
            remaining.add(msg.topic)

    # Subscribe to each exact target to probe retained state
    for t in list(targets):
        try:
            conn.subscribe(t, _collect, qos=QoS.AtLeastOnce)
        except Exception:
            pass

    time.sleep(0.4)

    # Re-clear any remaining
    if remaining:
        for t in list(remaining):
            try:
                conn.publish(t, b"", qos=QoS.AtMostOnce, retain=True, wait_for_publish=True)
            except Exception:
                pass
        time.sleep(0.2)

    conn.close()
