import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from paho.mqtt.client import Client, CallbackAPIVersion
import asyncio
from aiocoap import Context, Message, Code
from aiocoap.resource import Site, Resource
import time

SNIFFER_HOST = '0.0.0.0'
TCP_PORT = 9000
HTTP_PORT = 8000
MQTT_PORT = 1884
COAP_PORT = 5684

sensores_status = {
    "temperatura": True,
    "umidade": True,
    "braco": True
}

medias_registradas = []
min_max_pps = {"device_to_twin": {"min": None, "max": None}, "twin_to_device": {"min": None, "max": None}}
min_max_bps = {"device_to_twin": {"min": None, "max": None}, "twin_to_device": {"min": None, "max": None}}
teste_inicial_finalizado = False
ciclo_teste_inicial = 0

stats = {
    "device_to_twin": {"pps": 0, "bps": 0, "count": 0, "bytes": 0},
    "twin_to_device": {"pps": 0, "bps": 0, "count": 0, "bytes": 0},
}

def log_event(msg):
    print(msg, flush=True)
    try:
        with open("/logs/sniffer.log", "a") as f:
            f.write(msg + "\n")
    except Exception as e:
        print(f"[SNIFFER] Erro ao escrever no log: {e}", flush=True)

def update_stats(direction, byte_count):
    stats[direction]["count"] += 1
    stats[direction]["bytes"] += byte_count

def stats_monitor():
    INTERVAL = 1
    header = (
        f"{'Direção':<18} | {'PPS':>8} | {'BPS':>8}\n"
        + "-" * 42
    )
    log_event(header)
    ciclo = 0
    global ciclo_teste_inicial
    while True:
        for direction in stats:
            stats[direction]["pps"] = stats[direction]["count"]
            stats[direction]["bps"] = stats[direction]["bytes"]
            stats[direction]["count"] = 0
            stats[direction]["bytes"] = 0
        medias_registradas.append({
            "ciclo": ciclo,
            "status": sensores_status.copy(),
            "pps": {k: stats[k]["pps"] for k in stats},
            "bps": {k: stats[k]["bps"] for k in stats}
        })
        # Atualiza min/max durante o teste inicial
        if not teste_inicial_finalizado:
            for direction in stats:
                pps = stats[direction]["pps"]
                bps = stats[direction]["bps"]
                if min_max_pps[direction]["min"] is None or pps < min_max_pps[direction]["min"]:
                    min_max_pps[direction]["min"] = pps
                if min_max_pps[direction]["max"] is None or pps > min_max_pps[direction]["max"]:
                    min_max_pps[direction]["max"] = pps
                if min_max_bps[direction]["min"] is None or bps < min_max_bps[direction]["min"]:
                    min_max_bps[direction]["min"] = bps
                if min_max_bps[direction]["max"] is None or bps > min_max_bps[direction]["max"]:
                    min_max_bps[direction]["max"] = bps
        ciclo += 1
        table = (
            f"\n******************************************************\n"
            f"{'Device→Twin':<18} | {stats['device_to_twin']['pps']:>8} | {stats['device_to_twin']['bps']:>8}\n"
            f"{'Twin→Device':<18} | {stats['twin_to_device']['pps']:>8} | {stats['twin_to_device']['bps']:>8}\n"
            f"******************************************************"
        )
        log_event(table)
        for sensor, status in sensores_status.items():
            if not status:
                log_event(f"[SNIFFER][ALERTA] Sensor '{sensor}' está desligado!")
        # Alerta se os valores atuais excederem os máximos do teste inicial
        if teste_inicial_finalizado:
            for direction in stats:
                max_pps = min_max_pps[direction]["max"]
                current_pps = stats[direction]["pps"]
                if max_pps is not None and current_pps > max_pps:
                    log_event(f"[SNIFFER][ALERTA] PPS de {direction} ({current_pps}) excedeu o máximo de {max_pps} definido no teste inicial.")

                max_bps = min_max_bps[direction]["max"]
                current_bps = stats[direction]["bps"]
                if max_bps is not None and current_bps > max_bps:
                    log_event(f"[SNIFFER][ALERTA] BPS de {direction} ({current_bps}) excedeu o máximo de {max_bps} definido no teste inicial.")
        # Exibe min/max após teste inicial
        if teste_inicial_finalizado and ciclo == ciclo_teste_inicial + 1:
            for direction in stats:
                log_event(f"[SNIFFER][INFO] {direction} - PPS min: {min_max_pps[direction]['min']}, max: {min_max_pps[direction]['max']}")
                log_event(f"[SNIFFER][INFO] {direction} - BPS min: {min_max_bps[direction]['min']}, max: {min_max_bps[direction]['max']}")
        time.sleep(INTERVAL)

log_event("[SNIFFER] Servidor iniciando...")

def monitor_tcp():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sniffer_socket:
        sniffer_socket.bind((SNIFFER_HOST, TCP_PORT))
        sniffer_socket.listen()
        log_event(f"[SNIFFER] Monitorando conexões TCP na porta {TCP_PORT}...")
        while True:
            conn, addr = sniffer_socket.accept()
            with conn:
                data = conn.recv(1024)
                if data:
                    direction = "device_to_twin" if b"protocolo=" in data else "twin_to_device"
                    update_stats(direction, len(data))
                    log_event(f"[SNIFFER] Capturado via TCP: {data.decode('utf-8')}")

class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        direction = "twin_to_device" if self.path == "/device" else "device_to_twin"
        update_stats(direction, len(post_data))
        log_event(f"[SNIFFER] Capturado via HTTP: {post_data.decode('utf-8')}")
        self.send_response(200)
        self.end_headers()

def monitor_http():
    server = HTTPServer((SNIFFER_HOST, HTTP_PORT), HTTPHandler)
    log_event(f"[SNIFFER] Monitorando conexões HTTP na porta {HTTP_PORT}...")
    server.serve_forever()

def monitor_mqtt():
    def on_connect(client, userdata, flags, rc):
        log_event(f"[SNIFFER] Conectado ao broker MQTT com código {rc}")
        client.subscribe("#")

    def on_message(client, userdata, msg):
        global teste_inicial_finalizado, ciclo_teste_inicial
        payload = msg.payload.decode('utf-8')
        if msg.topic == "device/commands":
            direction = "twin_to_device"
            if payload == "fim_teste_inicial":
                # Registra o ciclo do fim do teste inicial
                if medias_registradas:
                    ciclo_teste_inicial = medias_registradas[-1]["ciclo"]
                else:
                    ciclo_teste_inicial = 0
                teste_inicial_finalizado = True
                log_event("[SNIFFER] Teste inicial finalizado. Alertas dinâmicos ativados!")
            elif payload == "desliga_temp":
                sensores_status["temperatura"] = False
                log_event("[SNIFFER][ALERTA] Sensor de temperatura desligado!")
            elif payload == "liga_temp":
                sensores_status["temperatura"] = True
                log_event("[SNIFFER][ALERTA] Sensor de temperatura ligado!")
            elif payload == "desliga_umid":
                sensores_status["umidade"] = False
                log_event("[SNIFFER][ALERTA] Sensor de umidade desligado!")
            elif payload == "liga_umid":
                sensores_status["umidade"] = True
                log_event("[SNIFFER][ALERTA] Sensor de umidade ligado!")
            elif payload == "desliga_arm":
                sensores_status["braco"] = False
                log_event("[SNIFFER][ALERTA] Sensor do braço desligado!")
            elif payload == "liga_arm":
                sensores_status["braco"] = True
                log_event("[SNIFFER][ALERTA] Sensor do braço ligado!")
        else:
            direction = "device_to_twin"
        update_stats(direction, len(msg.payload))
        log_event(f"[SNIFFER] Capturado via MQTT no tópico {msg.topic}: {payload}")

    client = Client(CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect("mqtt_broker", MQTT_PORT, 60)
        log_event(f"[SNIFFER] Monitorando conexões MQTT na porta {MQTT_PORT}...")
        client.loop_forever()
    except Exception as e:
        log_event(f"[SNIFFER] Erro ao conectar ao broker MQTT: {e}")

class CoAPResource(Resource):
    async def render_post(self, request):
        direction = "twin_to_device" if self.path == "/device" else "device_to_twin"
        update_stats(direction, len(request.payload))
        log_event(f"[SNIFFER] Capturado via CoAP: {request.payload.decode('utf-8')}")
        return Message(code=Code.CONTENT, payload=b"Recebido")

async def monitor_coap():
    root = Site()
    root.add_resource(('.well-known', 'core'), CoAPResource())
    root.add_resource(('sensor-data',), CoAPResource())

    context = await Context.create_server_context(root, bind=(SNIFFER_HOST, COAP_PORT))
    log_event(f"[SNIFFER] Monitorando conexões CoAP na porta {COAP_PORT}...")
    await asyncio.get_running_loop().create_future()

threading.Thread(target=monitor_tcp, daemon=True).start()
threading.Thread(target=monitor_http, daemon=True).start()
threading.Thread(target=monitor_mqtt, daemon=True).start()
threading.Thread(target=stats_monitor, daemon=True).start()
asyncio.run(monitor_coap())