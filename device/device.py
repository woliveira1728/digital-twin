import time
import random
import threading
import queue
import paho.mqtt.client as mqtt

BROKER_HOST = "mqtt_broker"
BROKER_PORT = 1884

command_queue = queue.Queue()

sensor_temp_interval = 5
sensor_umid_interval = 5
sensor_arm_interval = 3
arm_action = "ciclo"

sensor_temp_on = True
sensor_umid_on = True
sensor_arm_on = True

def on_command(client, userdata, msg):
    command = msg.payload.decode('utf-8')
    print(f"[DEVICE] Comando recebido do Twin: {command}", flush=True)
    if command == "desliga_temp":
        global sensor_temp_on
        sensor_temp_on = False
        print("[DEVICE] Sensor de temperatura desligado!", flush=True)
    elif command == "liga_temp":
        sensor_temp_on = True
        print("[DEVICE] Sensor de temperatura ligado!", flush=True)
    elif command == "desliga_umid":
        global sensor_umid_on
        sensor_umid_on = False
        print("[DEVICE] Sensor de umidade desligado!", flush=True)
    elif command == "liga_umid":
        sensor_umid_on = True
        print("[DEVICE] Sensor de umidade ligado!", flush=True)
    elif command == "desliga_arm":
        global sensor_arm_on
        sensor_arm_on = False
        print("[DEVICE] Sensor do braço desligado!", flush=True)
    elif command == "liga_arm":
        sensor_arm_on = True
        print("[DEVICE] Sensor do braço ligado!", flush=True)
    else:
        command_queue.put(command)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_message = on_command
client.connect(BROKER_HOST, BROKER_PORT, 60)
client.subscribe("device/commands")
client.loop_start()

def sensor_temperatura():
    global sensor_temp_interval
    while True:
        if not sensor_temp_on:
            time.sleep(1)
            continue
        while not command_queue.empty():
            cmd = command_queue.get()
            if cmd.startswith("set_temp_interval:"):
                sensor_temp_interval = int(cmd.split(":")[1])
        temperature = random.uniform(20, 30)
        payload = f"protocolo=coap;temperature={temperature:.2f}"
        client.publish("sensor/temperature", payload)
        time.sleep(sensor_temp_interval)

def sensor_umidade():
    global sensor_umid_interval
    while True:
        if not sensor_umid_on:
            time.sleep(1)
            continue
        while not command_queue.empty():
            cmd = command_queue.get()
            if cmd.startswith("set_umid_interval:"):
                sensor_umid_interval = int(cmd.split(":")[1])
        humidity = random.uniform(40, 60)
        payload = f"protocolo=mqtt;humidity={humidity:.2f}"
        client.publish("sensor/humidity", payload)
        time.sleep(sensor_umid_interval)

def sensor_braco():
    global sensor_arm_interval, arm_action
    while True:
        if not sensor_arm_on:
            time.sleep(1)
            continue
        while not command_queue.empty():
            cmd = command_queue.get()
            if cmd.startswith("set_arm_interval:"):
                sensor_arm_interval = int(cmd.split(":")[1])
            elif cmd.startswith("set_arm_action:"):
                arm_action = cmd.split(":")[1]
        if arm_action == "coletar":
            tempo_coleta = random.uniform(1, 2)
            client.publish("sensor/arm", f"protocolo=opcua;arm=Braço coletando caixa da esteira;tempo={tempo_coleta:.2f}")
            time.sleep(tempo_coleta)
        elif arm_action == "mover":
            tempo_mover = random.uniform(1, 3)
            client.publish("sensor/arm", f"protocolo=opcua;arm=Braço movendo caixa para a pilha;tempo={tempo_mover:.2f}")
            time.sleep(tempo_mover)
        elif arm_action == "depositar":
            tempo_depositar = random.uniform(0.5, 1.5)
            client.publish("sensor/arm", f"protocolo=opcua;arm=Braço depositando a caixa na pilha;tempo={tempo_depositar:.2f}")
            time.sleep(tempo_depositar)
        else:
            tempo_coleta = random.uniform(1, 2)
            client.publish("sensor/arm", f"protocolo=opcua;arm=Braço coletando caixa da esteira;tempo={tempo_coleta:.2f}")
            time.sleep(tempo_coleta)
            tempo_mover = random.uniform(1, 3)
            client.publish("sensor/arm", f"protocolo=opcua;arm=Braço movendo caixa para a pilha;tempo={tempo_mover:.2f}")
            time.sleep(tempo_mover)
            tempo_depositar = random.uniform(0.5, 1.5)
            client.publish("sensor/arm", f"protocolo=opcua;arm=Braço depositando a caixa na pilha;tempo={tempo_depositar:.2f}")
            time.sleep(tempo_depositar)
            tempo_total = tempo_coleta + tempo_mover + tempo_depositar
            client.publish("sensor/arm", f"protocolo=opcua;arm=ciclo_completo;tempo_total={tempo_total:.2f}")
            time.sleep(sensor_arm_interval)

def simular_ciclos_sensores():
    sensores = ["temp", "umid", "arm"]
    client_sim = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client_sim.connect(BROKER_HOST, BROKER_PORT, 60)

    # 1. Período com todos os sensores ligados para estabelecer a linha de base máxima.
    print("[DEVICE][SIM] Início do teste: Todos os sensores ligados para calibração (15s).")
    time.sleep(15)

    # 2. Desliga cada sensor individualmente para determinar os valores mínimos.
    for sensor in sensores:
        # Desliga um sensor
        client_sim.publish("device/commands", f"desliga_{sensor}")
        print(f"[DEVICE][SIM] Teste: Desligando sensor '{sensor}' para medição (15s).")
        time.sleep(15)
        # Religa o sensor para o próximo ciclo
        client_sim.publish("device/commands", f"liga_{sensor}")
        print(f"[DEVICE][SIM] Teste: Religando sensor '{sensor}'.")
        time.sleep(2) # Pequena pausa para estabilizar

    print("[DEVICE][SIM] Fim do teste de calibração. Enviando sinal para o sniffer.")
    client_sim.publish("device/commands", "fim_teste_inicial")
    client_sim.disconnect()

if __name__ == "__main__":
    threading.Thread(target=sensor_temperatura, daemon=True).start()
    threading.Thread(target=sensor_umidade, daemon=True).start()
    threading.Thread(target=sensor_braco, daemon=True).start()
    simular_ciclos_sensores()
    while True:
        time.sleep(1)