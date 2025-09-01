import socket
import threading

LOCAL_HOST = '0.0.0.0'
LOCAL_PORT = 1885  # Porta que o proxy escuta
REMOTE_HOST = 'mqtt_broker'
REMOTE_PORT = 1884  # Porta do serviço real (MQTT Broker)

def decode_remaining_length(stream):
    """Decodifica o campo 'Remaining Length' de um stream de bytes MQTT."""
    multiplier = 1
    value = 0
    length_bytes = b''
    while True:
        encoded_byte = stream.recv(1)
        if not encoded_byte:
            return None, None
        length_bytes += encoded_byte
        value += (encoded_byte[0] & 127) * multiplier
        if (encoded_byte[0] & 128) == 0:
            break
        multiplier *= 128
    return value, length_bytes

def encode_remaining_length(length):
    """Codifica um inteiro para o formato 'Remaining Length' do MQTT."""
    encoded = bytearray()
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 128
        encoded.append(digit)
        if length == 0:
            break
    return encoded

def handle_client(client_socket, remote_socket):
    """Lida com o tráfego do cliente para o servidor remoto."""
    while True:
        try:
            # Lê o primeiro byte (cabeçalho fixo)
            fixed_header = client_socket.recv(1)
            if not fixed_header:
                break

            # Decodifica o 'Remaining Length'
            remaining_length, length_bytes = decode_remaining_length(client_socket)
            if remaining_length is None:
                break

            # Lê o resto do pacote (cabeçalho variável + payload)
            variable_part = b''
            if remaining_length > 0:
                variable_part = client_socket.recv(remaining_length)

            # --- LÓGICA DE MODIFICAÇÃO ---
            # Apenas modifica pacotes do tipo PUBLISH (primeiros 4 bits do cabeçalho)
            if (fixed_header[0] & 0xF0) == 0x30: # 0x30 é o código para PUBLISH
                if b'liga_temp' in variable_part:
                    print(f"[PROXY][ALTERADO] Interceptado comando 'liga_temp'. Alterando para 'desliga_temp'.")
                    variable_part = variable_part.replace(b'liga_temp', b'desliga_temp')

            # Reconstrói o pacote com o novo 'Remaining Length'
            new_remaining_length_bytes = encode_remaining_length(len(variable_part))
            new_packet = fixed_header + new_remaining_length_bytes + variable_part

            print(f"[PROXY] C->S: {len(new_packet)} bytes (Original: {1 + len(length_bytes) + remaining_length})")
            remote_socket.sendall(new_packet)

        except (ConnectionResetError, BrokenPipeError, OSError):
            break
    client_socket.close()
    remote_socket.close()

def handle_remote(remote_socket, client_socket):
    """Lida com o tráfego do servidor remoto para o cliente."""
    while True:
        try:
            data = remote_socket.recv(4096)
            if not data:
                break
            print(f"[PROXY] S->C: {len(data)} bytes")
            client_socket.sendall(data)
        except (ConnectionResetError, BrokenPipeError, OSError):
            break
    remote_socket.close()
    client_socket.close()

def main():
    print(f"[PROXY] Iniciando proxy. Escutando em {LOCAL_HOST}:{LOCAL_PORT}")
    print(f"[PROXY] Redirecionando para {REMOTE_HOST}:{REMOTE_PORT}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((LOCAL_HOST, LOCAL_PORT))
    server.listen(5)

    while True:
        client_socket, addr = server.accept()
        print(f"[PROXY] Nova conexão de {addr}")
        
        try:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((REMOTE_HOST, REMOTE_PORT))
        except Exception as e:
            print(f"[PROXY] Erro ao conectar ao servidor remoto: {e}")
            client_socket.close()
            continue

        threading.Thread(target=handle_client, args=(client_socket, remote_socket), daemon=True).start()
        threading.Thread(target=handle_remote, args=(remote_socket, client_socket), daemon=True).start()

if __name__ == '__main__':
    main()
