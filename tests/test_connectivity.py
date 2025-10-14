import threading


def test_connect_once_and_reuse_without_paho(mqtt_builder):
    hit = threading.Event()
    conn = mqtt_builder.build()
    if hasattr(conn, "add_on_connect"):
        conn.add_on_connect(lambda *_: hit.set())

    conn.connect()
    assert hit.wait(10)

    hit.clear()
    conn.close()
    conn.connect()
    assert hit.wait(10)

    conn.close()
