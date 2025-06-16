import requests
import time
import random

HTTP_URL = "http://sniffer:8000/sensor-data"
TEMPO_ESPERADO_MIN = 3
TEMPO_ESPERADO_MAX = 7

while True:
    exec_time = random.uniform(2, 8)
    status = "ok" if TEMPO_ESPERADO_MIN <= exec_time <= TEMPO_ESPERADO_MAX else "alert"
    data = {"exec_time": exec_time, "status": status}
    try:
        response = requests.post(HTTP_URL, json=data)
        print(f"[HTTP SENSOR] Temporizador enviado: {data} | Resposta: {response.status_code}")
    except Exception as e:
        print(f"[HTTP SENSOR] Erro: {e}")
    time.sleep(10)
