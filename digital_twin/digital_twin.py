import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from paho.mqtt.client import Client, CallbackAPIVersion
from opcua import Server
import asyncio
from aiocoap import Context, Message, Code
from aiocoap.resource import Site, Resource
import time

# Configurações gerais
HOST = '0.0.0.0'
TCP_PORT = 9090
HTTP_PORT = 8080
MQTT_PORT = 1884
OPCUA_PORT = 4840
COAP_PORT = 5683

print("[TWIN] Servidor iniciando...")

# Cliente MQTT persistente para publicar comandos.
# Isso evita a sobrecarga de conectar/desconectar para cada comando.
try:
    command_publisher_client = Client(CallbackAPIVersion.VERSION1, "twin_command_publisher")
    command_publisher_client.connect("mqtt_broker", MQTT_PORT, 60)
    command_publisher_client.loop_start() # Mantém a conexão ativa em uma thread de fundo
    print("[TWIN] Cliente publicador de comandos conectado ao broker.")
except Exception as e:
    print(f"[TWIN][ERRO] Falha ao conectar cliente publicador de comandos: {e}")
    command_publisher_client = None


# Função para lidar com conexões TCP
def handle_tcp():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, TCP_PORT))
        s.listen()
        print(f"[TWIN] Aguardando conexões TCP na porta {TCP_PORT}...")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"[TWIN] Conectado por {addr}")
                data = conn.recv(1024)
                if data:
                    message = data.decode('utf-8')
                    print(f"[TWIN] Dados recebidos via TCP: {message}")

# Classe para lidar com requisições HTTP
class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        print(f"[TWIN] Dados recebidos via HTTP: {post_data}")

        # Adicionado: Processa o comando e o encaminha para o device
        try:
            if '=' in post_data:
                key, value = post_data.split('=', 1)
                if key.strip() == 'comando':
                    command_to_send = value.strip()
                    print(f"[TWIN] Encaminhando comando '{command_to_send}' para o device via MQTT.")
                    send_command_to_device(command_to_send)
        except Exception as e:
            print(f"[TWIN] Erro ao processar comando HTTP: {e}")

        self.send_response(200)
        self.end_headers()

# Função para iniciar o servidor HTTP
def handle_http():
    server = HTTPServer((HOST, HTTP_PORT), HTTPHandler)
    print(f"[TWIN] Servidor HTTP escutando na porta {HTTP_PORT}...")
    server.serve_forever()

# Função para lidar com mensagens MQTT (API atualizada)
def handle_mqtt():
    def on_connect(client, userdata, flags, rc):
        print(f"[TWIN] Conectado ao broker MQTT com código {rc}")
        client.subscribe("#")  # Inscreve-se em todos os tópicos

    def on_message(client, userdata, msg):
        print(f"[TWIN] Dados recebidos via MQTT no tópico {msg.topic}: {msg.payload.decode('utf-8')}")

    client = Client(CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect("mqtt_broker", MQTT_PORT, 60)
        print(f"[TWIN] Servidor MQTT escutando na porta {MQTT_PORT}...")
        client.loop_start()
    except Exception as e:
        print(f"[TWIN] Erro ao conectar ao broker MQTT: {e}")

# Função para enviar comandos ao device via MQTT
def send_command_to_device(command):
    """Usa o cliente MQTT persistente para publicar um comando."""
    if command_publisher_client and command_publisher_client.is_connected():
        command_publisher_client.publish("device/commands", command)
    else:
        print("[TWIN][ERRO] Cliente publicador de comandos não está conectado. O comando não foi enviado.")

# Prompt interativo para enviar comandos a qualquer momento
def command_prompt():
    while True:
        cmd = input("[TWIN] Digite um comando para o device (ou 'exit' para sair): ")
        if cmd.strip().lower() == "exit":
            print("[TWIN] Encerrando prompt de comandos.")
            break
        send_command_to_device(cmd)

# Função para lidar com conexões OPC-UA (endpoints abertos)
def handle_opcua():
    server = Server()
    server.set_endpoint(f"opc.tcp://{HOST}:{OPCUA_PORT}")
    server.set_security_policy([])  # Remove políticas de segurança para endpoints abertos
    print(f"[TWIN] Servidor OPC-UA escutando na porta {OPCUA_PORT}...")
    server.start()

# Classe para lidar com requisições CoAP
class CoAPResource(Resource):
    async def render_post(self, request):
        print(f"[TWIN] Dados recebidos via CoAP: {request.payload.decode('utf-8')}")
        return Message(code=Code.CONTENT, payload=b"Recebido")

# Função para lidar com conexões CoAP (endereço explícito)
async def handle_coap():
    root = Site()
    root.add_resource(('.well-known', 'core'), CoAPResource())
    root.add_resource(('sensor-data',), CoAPResource())

    context = await Context.create_server_context(root, bind=(HOST, COAP_PORT))
    print(f"[TWIN] Servidor CoAP escutando na porta {COAP_PORT}...")
    await asyncio.get_running_loop().create_future()

# Inicia as threads para cada protocolo
threading.Thread(target=handle_tcp, daemon=True).start()
threading.Thread(target=handle_http, daemon=True).start()
threading.Thread(target=handle_mqtt, daemon=True).start()
threading.Thread(target=handle_opcua, daemon=True).start()
threading.Thread(target=lambda: asyncio.run(handle_coap()), daemon=True).start()
# O prompt de comando interativo bloqueia a execução em modo detached.
# Substituímos por um loop para manter o contêiner ativo.
print("[TWIN] Gêmeo Digital em execução. Pressione Ctrl+C para parar se estiver em modo interativo.")
try:
    while True:
        time.sleep(3600) # Mantém a thread principal viva
except KeyboardInterrupt:
    print("\n[TWIN] Gêmeo Digital encerrando.")