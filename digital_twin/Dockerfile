FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY digital_twin.py .

# Instala as dependências necessárias
RUN apt-get update && apt-get install -y libffi-dev libssl-dev && \
    pip install paho-mqtt opcua aiocoap cryptography

CMD ["python", "digital_twin.py"]
