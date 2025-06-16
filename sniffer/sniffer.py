import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from paho.mqtt.client import Client
import asyncio
from aiocoap import Context, Message, Code
from aiocoap.resource import Site, Resource

# Configurações gerais
SNIFFER_HOST = '0.0.0.0'
TCP_PORT = 9000
HTTP_PORT = 8000
MQTT_PORT = 1884
COAP_PORT = 5684

def log_event(msg):
    print(msg, flush=True)
    try:
        with open("/tmp/sniffer.log", "a") as f:
            f.write(msg + "\n")
    except Exception as e:
        print(f"[SNIFFER] Erro ao escrever no log: {e}", flush=True)

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
                    log_event(f"[SNIFFER] Capturado via TCP: {data.decode('utf-8')}")

# Classe para monitorar requisições HTTP
class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
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
        log_event(f"[SNIFFER] Capturado via MQTT no tópico {msg.topic}: {msg.payload.decode('utf-8')}")

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

# Inicia as threads para cada protocolo
threading.Thread(target=monitor_tcp, daemon=True).start()
threading.Thread(target=monitor_http, daemon=True).start()
threading.Thread(target=monitor_mqtt, daemon=True).start()
asyncio.run(monitor_coap())