FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY sniffer.py .

RUN apt-get update && apt-get install -y libffi-dev libssl-dev
RUN pip install --no-cache-dir textual==0.44.1 paho-mqtt aiocoap

CMD ["python", "sniffer.py"]