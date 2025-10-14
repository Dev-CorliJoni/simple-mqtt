import os
import pytest
from simplemqtt.types import QualityOfService as QoS


def test_build_minimal(mqtt_builder):
    conn = mqtt_builder.build()
    assert conn is not None


def test_build_with_keepalive(mqtt_builder):
    conn = mqtt_builder.keep_alive(60).build()
    assert conn is not None


def test_build_with_persistent_session(mqtt_builder):
    conn = mqtt_builder.persistent_session(True).build()
    assert conn is not None


def test_build_with_auto_reconnect(mqtt_builder):
    conn = mqtt_builder.auto_reconnect(min_delay=1, max_delay=5).build()
    assert conn is not None
