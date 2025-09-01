# Use uma imagem base leve do Python
FROM python:3.9-slim

# Define o diretório de trabalho no contêiner
WORKDIR /app

# Copia o script do atacante para o contêiner
COPY attacker.py .

# Instala as dependências necessárias (paho-mqtt)
RUN pip install paho-mqtt requests

# O comando padrão será definido no docker-compose para flexibilidade
# CMD ["python", "attacker.py", "mitm"]
