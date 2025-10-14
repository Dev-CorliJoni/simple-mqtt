import time
import threading


def test_callback_order(mqtt_builder):
    # Dedicated short-lived connection to capture the order precisely
    events = []
    lock = threading.Lock()

    def tag(name):
        with lock:
            events.append(name)

    conn = mqtt_builder.build()

    if hasattr(conn, "add_on_connect"):
        conn.add_on_connect(lambda *_: tag("on_connect"))

    if hasattr(conn, "add_before_disconnect"):
        conn.add_before_disconnect(lambda _conn: tag("before_disconnect"))

    if hasattr(conn, "add_on_disconnect"):
        conn.add_on_disconnect(lambda *_: tag("on_disconnect"))

    conn.connect()
    # Wait for connect
    t0 = time.time()
    while "on_connect" not in events and time.time() - t0 < 10:
        time.sleep(0.05)

    assert "on_connect" in events

    conn.close()
    # on_disconnect arrives asynchronously
    t0 = time.time()
    while "on_disconnect" not in events and time.time() - t0 < 5:
        time.sleep(0.05)

    # Expected relative order
    assert events.index("on_connect") < events.index("before_disconnect")
    assert events.index("before_disconnect") < events.index("on_disconnect")
