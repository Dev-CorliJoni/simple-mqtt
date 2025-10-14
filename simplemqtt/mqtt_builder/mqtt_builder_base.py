from __future__ import annotations

from typing import TypeVar, Generic, Type

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from ..setup_logging import get_logger
from ..types import QualityOfService as QoS
from ..mqtt_config import MQTTConfig
from ..mqtt_connections import MQTTConnectionV3, MQTTConnectionV5


C = TypeVar("C", MQTTConnectionV3, MQTTConnectionV5)
logger = get_logger(f"MqttBuilder")


class MqttBuilder(Generic[C]):
    def __init__(self, client_id: str, host: str, connector: Type[C]):
        self._config = MQTTConfig(client_id, host)
        self._config.protocol = mqtt.MQTTv311 if connector is MQTTConnectionV3 else mqtt.MQTTv5

        self._connection: Type[C] = connector()

    def persistent_session(self, persistent_session: bool = True) -> MqttBuilder[C]:
        """
        Control session persistence.

        :param persistent_session: True for persistent session, False for clean start.
        :return: MqttBuilder
        """
        self._config.clean_session = not persistent_session
        return self

    def port(self, port: int) -> MqttBuilder[C]:
        """
        Set broker port. Default: 1883

        :param port: Usually 1883 (MQTT) or 8883 (MQTTS).
        :return: MqttBuilder
        """
        self._config.port = port
        return self

    def keep_alive(self, keep_alive: int) -> MqttBuilder[C]:
        """
        Set keepalive seconds.

        :param keep_alive: Interval in seconds for PINGREQ heartbeats.
        :return: MqttBuilder
        """
        self._config.keep_alive = keep_alive
        return self

    def login(self, username: str, password: str) -> MqttBuilder[C]:
        """
        Set username and password.

        :param username: Username string.
        :param password: Password string.
        :return: MqttBuilder
        """
        self._config.username = username
        self._config.password = password
        return self

    def availability(self, topic: str, payload_online: str = "online", payload_offline: str = "offline", qos: QoS = QoS.AtLeastOnce, retain: bool = True) -> MqttBuilder[C]:
        """
        Configure an availability topic.
        On successful connect, publish 'payload_online' to 'topic' with given qos/retain.
        Also sets the Last Will to 'payload_offline' for unclean disconnects.

        :param topic: Availability topic. Use a stable, retained topic so new subscribers see status immediately.
        :param payload_online: Payload published on connect.
        :param payload_offline: Payload set as Last Will and sent by broker on unclean disconnect.
        :param qos: Delivery level for availability messages. Usually 1.
        :param retain: Retain both online and will messages so late subscribers see the latest state.
        :return: MqttBuilder
        """
        args = topic, payload_online, qos, retain
        if isinstance(self._connection, MQTTConnectionV3):
            self._connection.add_on_connect(lambda connection, _1, _2, _3: connection.publish(*args))
        elif isinstance(self._connection, MQTTConnectionV5):
            self._connection.add_on_connect(lambda connection, _1, _2, _3, _4: connection.publish(*args))

        self._connection.add_before_disconnect(
            lambda connection: connection.publish(topic, payload_offline, qos, retain, wait_for_publish=True)
        )
        self.last_will(topic, payload_offline, qos, retain)
        return self

    def last_will(self, topic: str, payload: str = "offline",  qos: QoS = QoS.AtLeastOnce, retain: bool = True) -> MqttBuilder[C]:
        """
        Set MQTT Last Will and Testament.

        :param topic: Target topic for the will message.
        :param payload: Will payload sent by the broker on unclean disconnect.
        :param qos: Will QoS.
        :param retain: Whether the will is retained.
        :return: MqttBuilder
        """
        self._config.last_will = {
            "topic": topic,
            "payload": payload,
            "qos": qos,
            "retain": retain
        }
        return self

    # TLS Missing
    """    
    2. 
    client.tls_set(
        ca_certs="/path/ca.pem",
        certfile="/path/client.crt",
        keyfile="/path/client.key",
        # keyfile_password="***"  # optional if key encrypted
    )
    """

    def _tls(self, settings: dict, allow_insecure: bool = False) -> MqttBuilder[C]:
        self._config.tls = {
            "settings": settings,
            "allow_insecure": allow_insecure
        }
        return self

    def tls(self, allow_insecure: bool = False) -> MqttBuilder[C]:
        """
        Enable TLS with default settings.

        :param allow_insecure: If True, disable certificate hostname checks (insecure).
        :return: MqttBuilder
        """
        return self._tls({}, allow_insecure)

    def own_tls(self, ca_certs: str, allow_insecure: bool = False) -> MqttBuilder[C]:
        """
        Enable TLS with a custom CA bundle.

        :param ca_certs: Path to CA certificate bundle file.
        :param allow_insecure: If True, disable certificate hostname checks (insecure).
        :return: MqttBuilder
        """
        return self._tls({"ca_certs": ca_certs}, allow_insecure)

    def auto_reconnect(self, min_delay=1, max_delay=30) -> MqttBuilder[C]:
        """
        Enable exponential backoff reconnects.

        :param min_delay: Initial backoff in seconds before the first reconnect attempt.
        :param max_delay: Maximum backoff cap in seconds. The delay grows up to this value.
        :return: MqttBuilder
        """
        self._config.auto_reconnect = {
            "min_delay": min_delay,
            "max_delay": max_delay
        }
        return self

    def build(self, **additional_client_params) -> C:
        """
        Create the client and apply configuration.

        :param additional_client_params: Extra kwargs forwarded to paho.Client(...), e.g. transport="websockets".
        :return: MQTTConnectionV3 or MQTTConnectionV5 wrapper depending on protocol.
        """
        if self._config.protocol != mqtt.MQTTv5:
            additional_client_params["clean_session"] = self._config.clean_session

        client = mqtt.Client(client_id=self._config.client_id, protocol=self._config.protocol, **additional_client_params)

        if self._config.has_auto_reconnect:
            client.reconnect_delay_set(**self._config.auto_reconnect)

        if self._config.has_tls:
            client.tls_set(**self._config.tls["settings"])
            client.tls_insecure_set(self._config.tls["allow_insecure"])

        if self._config.require_login:
            client.username_pw_set(self._config.username, self._config.password)

        if self._config.has_last_will:
            client.will_set(**self._config.last_will)

        connection_parameters = {
            "host": self._config.host,
            "port": self._config.port,
            "keepalive": self._config.keep_alive,
        }

        if self._config.protocol == mqtt.MQTTv5:
            # MQTT version 5 clean session. Is persistent for 3600 sec
            connection_parameters["clean_start"] = self._config.clean_session
            props = Properties(PacketTypes.CONNECT)
            props.SessionExpiryInterval = 3600 if not self._config.clean_session else 0  # seconds
            connection_parameters["properties"] = props

        self._connection.inject_client(client, connection_parameters)
        return self._connection

    def fast_build(self, **additional_client_params) -> C:
        """
        Create the client, apply configuration and connect.

        :param additional_client_params: Extra kwargs forwarded to paho.Client(...), e.g. transport="websockets".
        :return: MQTTConnectionV3 or MQTTConnectionV5 wrapper depending on protocol.
        """
        return self.build(**additional_client_params).connect()
