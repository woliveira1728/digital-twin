from opcua import Client
import time
import random

OPCUA_SERVER_URL = "opc.tcp://digital_twin:4840"

client = Client(OPCUA_SERVER_URL)
try:
    client.connect()
    print("[OPC-UA SENSOR] Conectado ao servidor OPC-UA")

    while True:
        # 1. Coleta a caixa na esteira
        tempo_coleta = random.uniform(1, 2)
        print(f"[OPC-UA SENSOR] Braço: COLETANDO caixa na esteira (tempo: {tempo_coleta:.2f}s)")
        # Exemplo: client.get_node("ns=2;i=2").set_value("coletando")
        time.sleep(tempo_coleta)

        # 2. Move o braço para a pilha de embalagem
        tempo_mover = random.uniform(1, 3)
        print(f"[OPC-UA SENSOR] Braço: MOVENDO para pilha de embalagem (tempo: {tempo_mover:.2f}s)")
        # Exemplo: client.get_node("ns=2;i=2").set_value("movendo")
        time.sleep(tempo_mover)

        # 3. Deposita a caixa na pilha
        tempo_depositar = random.uniform(0.5, 1.5)
        print(f"[OPC-UA SENSOR] Braço: DEPOSITANDO caixa na pilha (tempo: {tempo_depositar:.2f}s)")
        # Exemplo: client.get_node("ns=2;i=2").set_value("depositando")
        time.sleep(tempo_depositar)

        tempo_total = tempo_coleta + tempo_mover + tempo_depositar
        print(f"[OPC-UA SENSOR] Ciclo completo! Tempo total: {tempo_total:.2f}s")
        # Exemplo: client.get_node("ns=2;i=3").set_value(tempo_total)
        time.sleep(3)
finally:
    client.disconnect()
