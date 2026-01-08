import logging
import sys
import threading
import signal

from utils.mqttUtils import connect_mqtt, subscribe, TOPIC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        client = connect_mqtt()
    except Exception as e:
        logger.error("Failed to connect to MQTT broker: %s", e)
        sys.exit(1)

    logger.info("Successfully connected to MQTT broker")
    subscribe(client, TOPIC)

    stop_event = threading.Event()

    def handle_signal(sig, frame):
        logger.info("Stopping server...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Listening on topic `%s` (Ctrl+C to exit)", TOPIC)

    try:
        client.loop_start()
        stop_event.wait()
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Disconnected from MQTT broker")

#testna datoteka za mqtt util
if __name__ == "__main__":
    main()
