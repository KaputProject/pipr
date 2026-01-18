import threading
import logging
from typing import Deque, Optional
from utils.mqttUtils import connect_mqtt, subscribe

class MqttListener:
    """
    Upravlja z MQTT naročnino in poslušanjem sporočil v ozadju.
    """
    def __init__(self, topic: str, data_queue: Deque[str], logger: Optional[logging.Logger] = None):
        self.topic = topic
        self.data_queue = data_queue
        self.logger = logger
        self.client = None
        self._thread = None
        self._is_running = False

    def start(self):
        """Poveže se na MQTT broker in začne poslušati v ločeni niti."""
        if self._is_running:
            if self.logger:
                self.logger.warning("MQTT Listener je že zagnan.")
            return

        try:
            # Povezava in nastavitev callbacka
            self.client = connect_mqtt(on_message=self._on_message)
            subscribe(self.client, self.topic)

            # Zagon zanke v ozadju
            self._thread = threading.Thread(target=self.client.loop_forever, daemon=True)
            self._thread.start()
            self._is_running = True

            if self.logger:
                self.logger.info(f"MQTT listener zagnan na temi `{self.topic}`")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"MQTT povezava ni uspela: {e}. Nadaljujem brez MQTT.")

    def stop(self):
        """Ustavi MQTT zanko in prekine povezavo."""
        if self.client and self._is_running:
            self.client.loop_stop()
            self.client.disconnect()
            self._is_running = False
            if self.logger:
                self.logger.info("MQTT listener ustavljen.")

    def _on_message(self, client, userdata, msg):
        """Interna metoda za obdelavo prejetih sporočil."""
        payload = msg.payload.decode("utf-8", errors="replace")
        self.data_queue.append(payload)
        
        # Logiranje samo če je logger nastavljen
        if self.logger:
            try:
                self.logger.info(f"MQTT prejeto na `{msg.topic}`: {payload}")
            except Exception:
                pass

