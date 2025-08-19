# backend/utils/notify.py
import httpx
from bot.config import BOT_TOKEN, ADMINS

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def notify_admins_new_order(order):
    text = (
        f"🆕 <b>Новый заказ #{order.id}</b>\n"
        f"{order.flavor} ×{order.bottle_count}\n"
        f"Сумма: {order.price/100:.2f} ₽\n"
        f"Клиент: <a href='tg://user?id={order.telegram_id}'>профиль</a>\n"
        f"Адрес: {order.address}\nТелефон: {order.phone}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        for admin_id in ADMINS:
            await client.post(f"{API}/sendMessage", json={
                "chat_id": admin_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "Открыть в админке", "callback_data": f"admin:order:{order.id}"}
                    ]]
                }
            })
