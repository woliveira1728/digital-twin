import time
import random
import threading
import queue
import paho.mqtt.client as mqtt

BROKER_HOST = "mqtt_broker"
BROKER_PORT = 1884

# Fila para comandos recebidos
command_queue = queue.Queue()

# Variáveis globais para controlar sensores
sensor_temp_interval = 5
sensor_umid_interval = 5
sensor_arm_interval = 3  # Intervalo do braço
arm_action = "ciclo"     # Tipo de movimento do braço: ciclo, coletar, mover, depositar

def on_command(client, userdata, msg):
    command = msg.payload.decode('utf-8')
    print(f"[DEVICE] Comando recebido do Twin: {command}", flush=True)
    command_queue.put(command)

client = mqtt.Client()
client.on_message = on_command
client.connect(BROKER_HOST, BROKER_PORT, 60)
client.subscribe("device/commands")
client.loop_start()

def sensor_temperatura():
    global sensor_temp_interval
    while True:
        # Processa comandos
        while not command_queue.empty():
            cmd = command_queue.get()
            if cmd.startswith("set_temp_interval:"):
                sensor_temp_interval = int(cmd.split(":")[1])
                print(f"[DEVICE] Intervalo do sensor de temperatura alterado para {sensor_temp_interval}s", flush=True)
            elif cmd.startswith("set_umid_interval:"):
                command_queue.put(cmd)
            elif cmd.startswith("set_arm_interval:"):
                command_queue.put(cmd)
            elif cmd.startswith("set_arm_action:"):
                command_queue.put(cmd)
        temperature = random.uniform(20, 30)
        payload = f"protocolo=coap;temperature={temperature:.2f}"
        client.publish("sensor/temperature", payload)
        print(f"[DEVICE] MQTT Sent: {payload}", flush=True)
        time.sleep(sensor_temp_interval)

def sensor_umidade():
    global sensor_umid_interval
    while True:
        # Processa comandos
        while not command_queue.empty():
            cmd = command_queue.get()
            if cmd.startswith("set_umid_interval:"):
                sensor_umid_interval = int(cmd.split(":")[1])
                print(f"[DEVICE] Intervalo do sensor de umidade alterado para {sensor_umid_interval}s", flush=True)
            elif cmd.startswith("set_temp_interval:"):
                command_queue.put(cmd)
            elif cmd.startswith("set_arm_interval:"):
                command_queue.put(cmd)
            elif cmd.startswith("set_arm_action:"):
                command_queue.put(cmd)
        humidity = random.uniform(40, 60)
        payload = f"protocolo=mqtt;humidity={humidity:.2f}"
        client.publish("sensor/humidity", payload)
        print(f"[DEVICE] MQTT Sent: {payload}", flush=True)
        time.sleep(sensor_umid_interval)

def sensor_temporizador():
    TEMPO_ESPERADO_MIN = 3
    TEMPO_ESPERADO_MAX = 7
    while True:
        exec_time = random.uniform(2, 8)
        status = "ok" if TEMPO_ESPERADO_MIN <= exec_time <= TEMPO_ESPERADO_MAX else "alert"
        payload = f"protocolo=http;timer_exec_time={exec_time:.2f};status={status}"
        client.publish("sensor/timer", payload)
        print(f"[DEVICE] MQTT Sent: {payload}", flush=True)
        time.sleep(10)

def sensor_braco():
    global sensor_arm_interval, arm_action
    while True:
        # Processa comandos
        while not command_queue.empty():
            cmd = command_queue.get()
            if cmd.startswith("set_arm_interval:"):
                sensor_arm_interval = int(cmd.split(":")[1])
                print(f"[DEVICE] Intervalo do braço alterado para {sensor_arm_interval}s", flush=True)
            elif cmd.startswith("set_arm_action:"):
                arm_action = cmd.split(":")[1]
                print(f"[DEVICE] Tipo de movimento do braço alterado para '{arm_action}'", flush=True)
            elif cmd.startswith("set_temp_interval:"):
                command_queue.put(cmd)
            elif cmd.startswith("set_umid_interval:"):
                command_queue.put(cmd)
        # Executa o movimento solicitado
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
        else:  # ciclo completo (padrão)
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

if __name__ == "__main__":
    threading.Thread(target=sensor_temperatura, daemon=True).start()
    threading.Thread(target=sensor_umidade, daemon=True).start()
    threading.Thread(target=sensor_temporizador, daemon=True).start()
    threading.Thread(target=sensor_braco, daemon=True).start()
    while True:
        time.sleep(1)