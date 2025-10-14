import time
import pytest
from simplemqtt.types import QualityOfService as QoS


def test_unsubscribe_stops_delivery(connection, unique_topic, msg_queue, topic_registry):
    base = unique_topic("unsub")
    wildcard = f"{base}/#"
    t1 = f"{base}/a"
    t2 = f"{base}/b"

    # Record derived concrete topics so the after-all sweeper can clear them.
    topic_registry["add"](t1)
    topic_registry["add"](t2)

    def _cb(conn, client, userdata, msg):
        msg_queue.put(msg.topic)

    connection.subscribe(wildcard, _cb, qos=QoS.AtLeastOnce)
    time.sleep(0.2)

    connection.publish(t1, "x", qos=QoS.AtLeastOnce)
    assert msg_queue.get(timeout=5) == t1

    connection.unsubscribe(wildcard)
    time.sleep(0.2)

    connection.publish(t2, "y", qos=QoS.AtLeastOnce)
    with pytest.raises(Exception):
        msg_queue.get(timeout=2)