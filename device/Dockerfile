FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY device.py .

RUN pip install requests paho-mqtt

CMD ["python", "device.py"]