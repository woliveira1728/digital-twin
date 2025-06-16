import asyncio
import random
from aiocoap import Context, Message, POST

COAP_URL = "coap://sniffer:5684/sensor-data"

async def main():
    context = await Context.create_client_context()
    while True:
        temperature = random.uniform(20, 30)
        payload = f"temperature={temperature:.2f}".encode('utf-8')
        request = Message(code=POST, uri=COAP_URL, payload=payload)
        try:
            response = await context.request(request).response
            print(f"[COAP SENSOR] Temperatura enviada: {payload.decode()} | Resposta: {response.code}")
        except Exception as e:
            print(f"[COAP SENSOR] Erro: {e}")
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
