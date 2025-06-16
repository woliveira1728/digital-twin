import paho.mqtt.client as mqtt
import time
import random

# Configuração do broker MQTT
BROKER_HOST = "sniffer"
BROKER_PORT = 1884
TOPIC = "sensor/humidity"

client = mqtt.Client()
client.connect(BROKER_HOST, BROKER_PORT, 60)

try:
    while True:
        humidity = random.uniform(40, 60)
        message = f"{humidity:.2f}"
        client.publish(TOPIC, message)
        print(f"[MQTT SENSOR] Umidade publicada: {message}")
        time.sleep(5)
finally:
    client.disconnect()
