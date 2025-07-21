import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from paho.mqtt.client import Client
import asyncio
from aiocoap import Context, Message, Code
from aiocoap.resource import Site, Resource
import time

# Configurações gerais
SNIFFER_HOST = '0.0.0.0'
TCP_PORT = 9000
HTTP_PORT = 8000
MQTT_PORT = 1884
COAP_PORT = 5684

# Estatísticas globais
stats = {
    "device_to_twin": {"pps": 0, "bps": 0, "count": 0, "bytes": 0},
    "twin_to_device": {"pps": 0, "bps": 0, "count": 0, "bytes": 0},
}

def log_event(msg):
    print(msg, flush=True)
    try:
        with open("/tmp/sniffer.log", "a") as f:
            f.write(msg + "\n")
    except Exception as e:
        print(f"[SNIFFER] Erro ao escrever no log: {e}", flush=True)

def update_stats(direction, byte_count):
    stats[direction]["count"] += 1
    stats[direction]["bytes"] += byte_count

def stats_monitor():
    INTERVAL = 0.001  # 1 ms
    header = (
        f"{'Direção':<18} | {'PPS':>8} | {'BPS':>8}\n"
        + "-" * 42
    )
    log_event(header)
    while True:
        for direction in stats:
            # Ajuste: calcula PPS/BPS para 1 segundo
            stats[direction]["pps"] = int(stats[direction]["count"] / INTERVAL)
            stats[direction]["bps"] = int(stats[direction]["bytes"] / INTERVAL)
            stats[direction]["count"] = 0
            stats[direction]["bytes"] = 0
        table = (
            f"\n\n******************************************************\n"
            f"{'Device→Twin':<18} | {stats['device_to_twin']['pps']:>8}(pps) | {stats['device_to_twin']['bps']:>8}(bps)\n"
            f"{'Twin→Device':<18} | {stats['twin_to_device']['pps']:>8}(pps)| {stats['twin_to_device']['bps']:>8}(bps)\n"
            f"******************************************************\n\n"
        )
        log_event("\n" + table)
        time.sleep(1)

log_event("[SNIFFER] Servidor iniciando...")

# Função para monitorar conexões TCP
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
                    # Supondo que device envia para twin se "protocolo=" estiver no início
                    direction = "device_to_twin" if b"protocolo=" in data else "twin_to_device"
                    update_stats(direction, len(data))
                    log_event(f"[SNIFFER] Capturado via TCP: {data.decode('utf-8')}")

# Classe para monitorar requisições HTTP
class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        # Supondo que comandos do twin para device vão para /device, e do device para twin vão para /twin
        direction = "twin_to_device" if self.path == "/device" else "device_to_twin"
        update_stats(direction, len(post_data))
        log_event(f"[SNIFFER] Capturado via HTTP: {post_data.decode('utf-8')}")
        self.send_response(200)
        self.end_headers()

# Função para iniciar o monitoramento HTTP
def monitor_http():
    server = HTTPServer((SNIFFER_HOST, HTTP_PORT), HTTPHandler)
    log_event(f"[SNIFFER] Monitorando conexões HTTP na porta {HTTP_PORT}...")
    server.serve_forever()

# Função para monitorar mensagens MQTT (API atualizada)
def monitor_mqtt():
    def on_connect(client, userdata, flags, rc):
        log_event(f"[SNIFFER] Conectado ao broker MQTT com código {rc}")
        client.subscribe("#")

    def on_message(client, userdata, msg):
        payload = msg.payload.decode('utf-8')
        # Heurística: comandos do twin para device vão para "device/commands"
        if msg.topic == "device/commands":
            direction = "twin_to_device"
        else:
            direction = "device_to_twin"
        update_stats(direction, len(msg.payload))
        log_event(f"[SNIFFER] Capturado via MQTT no tópico {msg.topic}: {payload}")

    client = Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect("mqtt_broker", MQTT_PORT, 60)
        log_event(f"[SNIFFER] Monitorando conexões MQTT na porta {MQTT_PORT}...")
        client.loop_forever()
    except Exception as e:
        log_event(f"[SNIFFER] Erro ao conectar ao broker MQTT: {e}")

# Classe para monitorar requisições CoAP
class CoAPResource(Resource):
    async def render_post(self, request):
        # Supondo que comandos do twin para device vão para /device, e do device para twin vão para /twin
        direction = "twin_to_device" if self.path == "/device" else "device_to_twin"
        update_stats(direction, len(request.payload))
        log_event(f"[SNIFFER] Capturado via CoAP: {request.payload.decode('utf-8')}")
        return Message(code=Code.CONTENT, payload=b"Recebido")

# Função para monitorar conexões CoAP
async def monitor_coap():
    root = Site()
    root.add_resource(('.well-known', 'core'), CoAPResource())
    root.add_resource(('sensor-data',), CoAPResource())

    context = await Context.create_server_context(root, bind=(SNIFFER_HOST, COAP_PORT))
    log_event(f"[SNIFFER] Monitorando conexões CoAP na porta {COAP_PORT}...")
    await asyncio.get_running_loop().create_future()

# Inicia as threads para cada protocolo e para estatísticas
threading.Thread(target=monitor_tcp, daemon=True).start()
threading.Thread(target=monitor_http, daemon=True).start()
threading.Thread(target=monitor_mqtt, daemon=True).start()
threading.Thread(target=stats_monitor, daemon=True).start()
asyncio.run(monitor_coap())