from ..mqtt_connections import MQTTConnectionV3
from .mqtt_builder_base import MqttBuilder


class MQTTBuilderV3(MqttBuilder[MQTTConnectionV3]):
    def __init__(self, client_id: str, host: str):
        """
        Initialize the builder.

        :param client_id: Client identifier used by the MQTT client.
        :param host: Broker hostname or IPv4/IPv6 literal.
        """
        super().__init__(client_id, host, connector=MQTTConnectionV3)
