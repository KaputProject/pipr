import logging
import ssl
import random
import os
from typing import Callable, Optional

from paho.mqtt import client as mqtt_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BROKER_STR = os.getenv("MQTT_BROKER", "")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD =  os.getenv("MQTT_PASSWORD", "")
TOPIC = "test"


def _parse_broker(broker: str):
    use_ssl = False

    if not broker:
        return "localhost", 1883, False

    if broker.startswith("ssl://"):
        use_ssl = True
        broker = broker.split("://", 1)[1]
    elif broker.startswith(("tcp://", "mqtt://")):
        broker = broker.split("://", 1)[1]

    if ":" in broker:
        host, port_str = broker.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = 8883 if use_ssl else 1883
    else:
        host = broker
        port = 8883 if use_ssl else 1883

    return host, port, use_ssl


def connect_mqtt(
    on_message: Optional[Callable[[mqtt_client.Client, object, "mqtt_client.MQTTMessage"], None]] = None
) -> mqtt_client.Client:
    """Create and connect an MQTT client. Optionally set a custom on_message callback."""
    host, port, use_ssl = _parse_broker(BROKER_STR)
    client_id = f"hivemq-subscriber-{random.randint(0, 1000)}"

    logger.info(
        "Connecting to MQTT broker host=%s port=%s ssl=%s client_id=%s",
        host,
        port,
        use_ssl,
        client_id,
    )

    client = mqtt_client.Client(client_id=client_id)

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD or "")

    if use_ssl:
        client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
            ciphers=None,
        )
        client.tls_insecure_set(False)

    def on_connect(cli, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
        else:
            logger.error("Failed to connect, return code: %s", rc)

    client.on_connect = on_connect

    if on_message is not None:
        client.on_message = on_message

    client.connect(host, port)
    return client


def subscribe(client: mqtt_client.Client, topic: str = TOPIC) -> None:
    client.subscribe(topic)
    logger.info("Subscribed to topic `%s`", topic)
