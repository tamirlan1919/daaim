# handlers/ui_inline.py
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery
)
from datetime import datetime
from database.models import Order

from database.engine import AsyncSessionLocal
from database.repository import (
    get_user_by_telegram_id, create_user,
    get_orders_by_user, get_order_by_id, set_order_paid,
    get_orders_count_by_telegram_id, get_total_bottles_by_user,
)

router = Router()

WEBAPP_URL = "https://daim-web-zeta.vercel.app/products"
SUPPORT_URL = "https://t.me/veamogam"
CURRENCY = "RUB"
PROVIDER_TOKEN = "390540012:LIVE:73124"

def fmt_price(minor: int) -> str:
    rub = minor
    kop = minor % 100
    return f"{rub:,}".replace(",", " ") + f".{kop:02d} ₽"

def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")

STATUS_LABELS = {
    "processing": "🚧 В обработке",
    "in_transit": "🚚 В пути",
    "declined":   "❌ Отклонён",
    "completed":  "✅ Завершён",
}
def fmt_status(order) -> str:
    if not order.is_paid:
        return "⏳ Не оплачен"
    return STATUS_LABELS.get(getattr(order, "status", None), "🚧 В обработке")

def order_card_text(o: Order) -> str:
    items_text = "\n".join(
        f"{it.quantity} × {it.product.name} — {fmt_price(it.line_total_cents)}"
        for it in o.items
    )
    return (
        f"Заказ №{o.id}\n"
        f"Статус: <b>{o.status.value}</b>\n"
        f"Оплата: {'✅' if o.is_paid else '❌'}\n"
        f"Адрес: {o.address}\n"
        f"Телефон: {o.phone}\n\n"
        f"Товары:\n{items_text}\n\n"
        f"Итого: <b>{fmt_price(o.total_price_cents)}</b>"
    )

def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Каталог", web_app={"url": WEBAPP_URL}),
            InlineKeyboardButton(text="📦 Заказы", callback_data="orders:list"),
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="nav:profile"),
            InlineKeyboardButton(text="❓ FAQ", callback_data="nav:faq"),
        ],
        [InlineKeyboardButton(text="💬 Поддержка", url=SUPPORT_URL)],
    ])

def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders:list"),
            InlineKeyboardButton(text="🛒 Каталог", web_app={"url": WEBAPP_URL}),
        ],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")],
    ])

def orders_list_kb(orders) -> InlineKeyboardMarkup:
    rows = []
    for o in orders:
        label = f"№{o.id} • {'Оплачен' if o.is_paid else 'Не оплачен'} • {fmt_price(o.total_price_cents)}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"order:{o.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def order_actions_kb(o) -> InlineKeyboardMarkup:
    rows = []
    if not o.is_paid:
        rows.append([InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay:{o.id}")])
    rows.append([
        InlineKeyboardButton(text="📦 К списку", callback_data="orders:list"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def faq_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")]
    ])

async def send_or_edit(event: Message | CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None):
    if isinstance(event, Message):
        return await event.answer(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        return await event.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)

@router.message(CommandStart())
async def start(message: Message):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            await create_user(db, telegram_id=message.from_user.id, name=message.from_user.full_name)
    await message.answer(
        "Добро пожаловать в <b>Daim Coffee</b> ☕",
        reply_markup=menu_kb()
    )

@router.callback_query(F.data == "nav:menu")
async def nav_menu(cb: CallbackQuery):
    await cb.answer()
    await send_or_edit(cb, "Главное меню:", menu_kb())

@router.callback_query(F.data == "nav:profile")
async def profile(cb: CallbackQuery):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, cb.from_user.id)
        orders_count = await get_orders_count_by_telegram_id(db, cb.from_user.id)
        total_bottles = await get_total_bottles_by_user(db, user.id) if user else 0
    phone = user.phone if user and user.phone else "—"
    text = (
        "<b>👤 Профиль</b>\n\n"
        f"Имя: {cb.from_user.full_name}\n"
        f"Телефон: {phone}\n"
        f"Заказы: <b>{orders_count}</b>\n"
        f"Оплаченных бутылок: <b>{total_bottles}</b>"
    )
    await cb.answer()
    await send_or_edit(cb, text, profile_kb())

FAQ_TEXT = (
    "<b>❓ FAQ</b>\n\n"
    "• <b>Как заказать?</b> Нажмите «🛒 Каталог».\n"
    "• <b>Оплата?</b> Откройте заказ → «💳 Оплатить».\n"
    "• <b>Статус?</b> У оплаченных: «В обработке / В пути / Отклонён / Завершён».\n"
    "• <b>Поддержка?</b> «💬 Поддержка» в меню."
)

@router.callback_query(F.data == "nav:faq")
async def faq(cb: CallbackQuery):
    await cb.answer()
    await send_or_edit(cb, FAQ_TEXT, faq_kb())

@router.callback_query(F.data == "orders:list")
async def orders_list(cb: CallbackQuery):
    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, cb.from_user.id)
        orders = await get_orders_by_user(db, user.id) if user else []
    if not orders:
        await cb.answer()
        return await send_or_edit(cb, "У вас пока нет заказов.", InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="nav:menu")]]
        ))
    orders = orders[:10]
    header = "<b>📦 Ваши заказы</b>\nВыберите заказ:"
    await cb.answer()
    await send_or_edit(cb, header, orders_list_kb(orders))

@router.callback_query(F.data.startswith("order:"))
async def order_details(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[1])
    async with AsyncSessionLocal() as db:
        o = await get_order_by_id(db, order_id)
    if not o or o.telegram_id != cb.from_user.id:
        return await cb.answer("Заказ не найден", show_alert=True)
    await cb.answer()
    await send_or_edit(cb, order_card_text(o), order_actions_kb(o))

@router.callback_query(F.data.startswith("pay:"))
async def pay_order(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[1])
    async with AsyncSessionLocal() as db:
        o = await get_order_by_id(db, order_id)
    if not o or o.telegram_id != cb.from_user.id:
        return await cb.answer("Заказ не найден", show_alert=True)
    if o.is_paid:
        return await cb.answer("Этот заказ уже оплачен ✅", show_alert=True)
    prices = [
        LabeledPrice(
            label=f"Заказ №{o.id}",
            amount=int(o.total_price * 100)  # переводим рубли → копейки
        )
    ]
    lines = []
    for item in o.items:
        lines.append(f"{item.product.name} × {item.quantity}")

    description = "\n".join(lines) + f"\nИтого: {fmt_price(o.total_price_cents)}"
    await cb.message.bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"Daim Coffee • #{o.id}",
        description=description,
        payload=f"order:{o.id}",
        provider_token=PROVIDER_TOKEN,
        currency=CURRENCY,
        prices=prices
    )
    await cb.answer()

@router.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    await pcq.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("order:"):
        return await message.answer("Платёж получен, но заказ не найден. Напишите в поддержку.")
    order_id = int(payload.split(":")[1])
    async with AsyncSessionLocal() as db:
        await set_order_paid(db, order_id)
        o = await get_order_by_id(db, order_id)
    await message.answer("Спасибо за оплату! 🎉\n" + order_card_text(o), reply_markup=menu_kb())
