import time
import paho.mqtt.client as mqtt
import pytest
from simplemqtt.types import QualityOfService as QoS


@pytest.mark.parametrize("qos", [QoS.AtMostOnce, QoS.AtLeastOnce])
def test_roundtrip_publish_subscribe(connection, unique_topic, msg_queue, qos):
    topic = unique_topic("roundtrip")
    payload = f"hello-{int(time.time())}"

    def _cb(conn, client, userdata, msg):
        msg_qos = msg.qos
        assert msg.topic == topic
        assert msg.payload.decode() == payload
        msg_queue.put(msg_qos)

    rc, _ = connection.subscribe(topic, _cb, qos=qos)
    assert rc == mqtt.MQTT_ERR_SUCCESS

    time.sleep(0.2)  # Allow a moment for the subscription to settle
    connection.publish(topic, payload, qos=qos, retain=False, wait_for_publish=True)

    received_qos = msg_queue.get(timeout=5)
    assert received_qos == int(qos)


def test_retain_flag(connection, unique_topic, msg_queue):
    topic = unique_topic("retain")
    # Publish a retained message
    connection.publish(topic, "retained", qos=QoS.AtLeastOnce, retain=True, wait_for_publish=True)

    def _cb(conn, client, userdata, msg):
        assert msg.retain is True
        msg_queue.put(msg.payload.decode())

    rc, _ = connection.subscribe(topic, _cb, qos=QoS.AtLeastOnce)
    assert rc == 0
    assert msg_queue.get(timeout=5) == "retained"
