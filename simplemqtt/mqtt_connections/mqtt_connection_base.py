from __future__ import annotations

import paho.mqtt.client as mqtt
from paho.mqtt.properties import Properties
from typing import Callable, Any, Dict, Optional

from simplemqtt import MQTTMessage
from simplemqtt.setup_logging import get_logger
from simplemqtt.types import QualityOfService as QoS

logger = get_logger("MqttConnectionBase")


def get_rc(rc):
    rc = getattr(rc, "value", rc)
    success = rc == 0
    return success, rc


def invoke_callbacks(callbacks, callback_name, *args, **kwargs):
    for callback in callbacks:
        try:
            callback(*args, **kwargs)
        except Exception as e:
            logger.warning(f"{callback_name} handler error: {e}")


class MqttConnectionBase:
    def __init__(self):
        self._client = None
        self._connection_parameters = None
        self._availability_topic = None

        self._subscription_handlers: Dict[str, Callable[[Any, mqtt.Client, Any, MQTTMessage], None]] = {}
        self._on_connect_callbacks = []
        self._before_disconnect_callbacks = []
        self._on_disconnect_callbacks = []

    def inject_client(self, client: mqtt.Client, connection_parameters: dict, availability_topic: str | None) -> None:
        self._client: mqtt.Client = client
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message_handler
        self._connection_parameters = connection_parameters
        self._availability_topic = availability_topic

    @property
    def availability_topic(self) -> str | None:
        return self._availability_topic

    @property
    def is_connected(self):
        return self._client.is_connected

    def connect(self, blocking: bool = False, **connection_parameters):
        """
        Connect to Mqtt Broker.

        :param blocking: If True, run loop_forever(). If False, start a background network loop.
        :param connection_parameters: Kwargs to override connect parameters
        :return: MQTTConnectionV3 or MQTTConnectionV5 wrapper depending on protocol.
        """
        self._client.connect(**self._connection_parameters, **connection_parameters)

        if blocking:
            self._client.loop_forever()
        else:
            self._client.loop_start()

        return self

    def _version_filter(self, version3, version5):
        if self._client.protocol == mqtt.MQTTv5:
            return version5
        else:
            return version3

    def _on_connect_version_parameter_filter(self, client, userdata, flags, properties):
        return self._version_filter((self, client, userdata, flags), (self, client, userdata, flags, properties))

    def _on_disconnect_version_parameter_filter(self, client, userdata, rc, properties):
        return self._version_filter((client, userdata, rc), (client, userdata, rc, properties))

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        success, rc = get_rc(rc)

        if success:
            logger.info("MQTT connected")
            invoke_callbacks(self._on_connect_callbacks, "On Connect",
                             *self._on_connect_version_parameter_filter(client, userdata, flags, properties))
        else:
            logger.error(f"MQTT connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        success, rc = get_rc(rc)

        if success:
            logger.info("MQTT disconnected")
        else:
            rs = getattr(properties, "ReasonString", None)
            if rs:
                logger.warning(f"MQTT disconnected unexpectedly rc={rc} reason={rs}")
            else:
                logger.warning(f"MQTT disconnected unexpectedly rc={rc}")

        invoke_callbacks(self._on_disconnect_callbacks, "On Disconnect",
                         *self._on_disconnect_version_parameter_filter(client, userdata, rc, properties))

    def _on_message_handler(self, client, userdata, msg: mqtt.MQTTMessage):
        message = MQTTMessage(msg)
        on_message_callbacks = [handler for topic, handler in self._subscription_handlers.items()
                                if mqtt.topic_matches_sub(topic, message.topic)]
        invoke_callbacks(on_message_callbacks, f"On Message(Topic: {message.topic})", self, client, userdata, message)

    def _publish(self, topic: str, payload, qos: QoS = QoS.AtMostOnce, retain: bool = False,
                 properties: Optional[Properties] = None, wait_for_publish: bool = False) -> mqtt.MQTTMessageInfo:
        info = self._client.publish(topic, payload, qos, retain, properties)
        if wait_for_publish:
            info.wait_for_publish()
        return info

    def _subscribe(self, topic: str, on_message: Callable[[Any, mqtt.Client, Any, MQTTMessage], None], **kwargs) -> tuple[int, int]:
        self._subscription_handlers[topic] = on_message
        return self._client.subscribe(topic, **kwargs)

    def unsubscribe(self, *topics: str):
        """
        Remove local handlers and send UNSUBSCRIBE.

        :param topics: One or more topic filters to unsubscribe from.
        :return: None
        """
        topics = list(topics)
        for topic in topics:
            self._subscription_handlers.pop(topic, None)
        self._client.unsubscribe(topics)

    def close(self):
        """
        Stop network loop and disconnect cleanly.

        :return: None
        """
        invoke_callbacks(self._before_disconnect_callbacks, "Before Disconnect", self)
        self._client.loop_stop()
        self._client.disconnect()
