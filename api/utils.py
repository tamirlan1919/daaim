import aiohttp
from bot.config import TELEGRAM_API_URL, PAYMENTS_PROVIDER_TOKEN
import json
async def send_telegram_invoice(chat_id: int, title: str, description: str, payload: str, currency: str, prices: list):
    async with aiohttp.ClientSession() as session:
        data = {
            "chat_id": chat_id,
            "title": title,
            "description": description,
            "payload": payload,
            "provider_token": PAYMENTS_PROVIDER_TOKEN,
            "currency": currency,
            "prices": json.dumps(prices),  # ОБЯЗАТЕЛЬНО!
            "start_parameter": "pay",
        }
        async with session.post(TELEGRAM_API_URL, data=data) as resp:
            response = await resp.json()
            print("TELEGRAM RESPONSE:", response)
            return response
