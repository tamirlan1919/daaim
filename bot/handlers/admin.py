# handlers/admin_inline.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from datetime import datetime
from config import ADMINS

from database.engine import AsyncSessionLocal
from database.repository import (
    get_all_users_page, get_all_orders_page,
    get_user_by_telegram_id, get_order_by_id,
    set_order_status, set_order_paid,
    get_products_page, create_product, update_product_price, delete_product,
)

router = Router()

# ---------- helpers ----------
def is_admin(user_id: int) -> bool:
    return int(user_id) in set(ADMINS)

async def deny_not_admin(event: Message | CallbackQuery):
    text = "Доступ запрещён"
    if isinstance(event, Message):
        await event.answer(text)
    else:
        await event.answer(text, show_alert=True)

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:0"),
            InlineKeyboardButton(text="📦 Заказы", callback_data="admin:orders:0"),
        ],
        [
            InlineKeyboardButton(text="🧃 Товары", callback_data="admin:products:0"),
        ],
        [InlineKeyboardButton(text="🏠 Клиентское меню", callback_data="nav:menu")],
    ])

async def send_or_edit(event: Message | CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None):
    if isinstance(event, Message):
        return await event.answer(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        return await event.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)

# ---------- /admin ----------
@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        return await deny_not_admin(message)
    await message.answer("<b>Админ-панель</b>", reply_markup=admin_menu_kb())

@router.callback_query(F.data == "admin:menu")
async def admin_menu(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    await cb.answer()
    await send_or_edit(cb, "<b>Админ-панель</b>", admin_menu_kb())

# ---------- Users ----------
def users_kb(page: int, has_next: bool) -> InlineKeyboardMarkup:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:users:{page-1}"))
    if has_next:
        row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"admin:users:{page+1}"))
    rows = [row] if row else []
    rows.append([InlineKeyboardButton(text="🏁 В админ-меню", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(F.data.startswith("admin:users:"))
async def admin_users(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    page = int(cb.data.split(":")[2])
    limit = 10
    async with AsyncSessionLocal() as db:
        items, total = await get_all_users_page(db, limit=limit, offset=page*limit)
    if not items:
        text = "<b>Пользователи</b>\nНет данных."
    else:
        lines = [f"<b>Пользователи</b> (стр {page+1}, всего {total})", ""]
        for u in items:
            lines.append(f"• <code>{u.id}</code> — {u.name or 'без имени'} — tg:<code>{u.telegram_id}</code> — {u.phone or '—'}")
        text = "\n".join(lines)
    has_next = (page + 1) * limit < total
    await cb.answer()
    await send_or_edit(cb, text, users_kb(page, has_next))

# ---------- Orders ----------
def fmt_price(minor: int) -> str:
    rub = minor // 100
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

def admin_orders_kb(page: int, has_next: bool) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:orders:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"admin:orders:{page+1}"))
    rows = [nav] if nav else []
    rows.append([InlineKeyboardButton(text="🏁 В админ-меню", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(F.data.startswith("admin:orders:"))
async def admin_orders(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    page = int(cb.data.split(":")[2])
    limit = 10
    async with AsyncSessionLocal() as db:
        items, total = await get_all_orders_page(db, limit=limit, offset=page*limit)
    if not items:
        text = "<b>Заказы</b>\nНет данных."
        kb = admin_orders_kb(page, False)
    else:
        lines = [f"<b>Заказы</b> (стр {page+1}, всего {total})", ""]
        for o in items:
            status = STATUS_LABELS.get(getattr(o, "status", None), "—") if o.is_paid else "⏳ Не оплачен"

            # собираем список позиций заказа
            item_lines = [
                f"{item.product.name} ×{item.quantity}"
                for item in o.items
            ]
            items_str = ", ".join(item_lines) if item_lines else "—"

            lines.append(
                f"• <b>#{o.id}</b> — {items_str} — {fmt_price(o.total_price_cents)} — {status} "
                f"[<a href='tg://user?id={o.telegram_id}'>tg</a>]"
            )

        text = "\n".join(lines)
        kb = admin_orders_kb(page, (page+1)*limit < total)

    await cb.answer()
    await send_or_edit(cb, text, kb)

def order_admin_actions_kb(order_id: int, is_paid: bool) -> InlineKeyboardMarkup:
    status_row = [
        InlineKeyboardButton(text="🚧 Processing", callback_data=f"admin:ost:{order_id}:processing"),
        InlineKeyboardButton(text="🚚 In transit", callback_data=f"admin:ost:{order_id}:in_transit"),
    ]
    status_row2 = [
        InlineKeyboardButton(text="❌ Declined", callback_data=f"admin:ost:{order_id}:declined"),
        InlineKeyboardButton(text="✅ Completed", callback_data=f"admin:ost:{order_id}:completed"),
    ]
    rows = [status_row, status_row2]
    if not is_paid:
        rows.append([InlineKeyboardButton(text="💳 Пометить оплаченным", callback_data=f"admin:paid:{order_id}")])
    rows.append([
        InlineKeyboardButton(text="⬅️ К списку заказов", callback_data="admin:orders:0"),
        InlineKeyboardButton(text="🏁 Админ-меню", callback_data="admin:menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(F.data.startswith("admin:order:"))
async def admin_order_details(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    order_id = int(cb.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        o = await get_order_by_id(db, order_id)
    if not o:
        return await cb.answer("Заказ не найден", show_alert=True)
    status = STATUS_LABELS.get(getattr(o, "status", None), "—") if o.is_paid else "⏳ Не оплачен"
    text = (
        f"<b>Заказ #{o.id}</b>\n"
        f"Дата: {fmt_dt(o.date)}\n"
        f"Клиент: <a href='tg://user?id={o.telegram_id}'>профиль</a>\n"
        f"Товар: {o.flavor} ×{o.bottle_count}\n"
        f"Сумма: {fmt_price(o.price)}\n"
        f"Статус: {status}\n\n"
        f"Адрес: {o.address}\nТелефон: {o.phone}"
    )
    await cb.answer()
    await send_or_edit(cb, text, order_admin_actions_kb(o.id, o.is_paid))

@router.callback_query(F.data.startswith("admin:ost:"))
async def admin_set_status(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    _, _, order_id, status = cb.data.split(":")
    order_id = int(order_id)
    async with AsyncSessionLocal() as db:
        await set_order_status(db, order_id, status)
        o = await get_order_by_id(db, order_id)
    await cb.answer("Статус обновлён ✅")
    await send_or_edit(cb, await _render_order_text(o), order_admin_actions_kb(o.id, o.is_paid))

async def _render_order_text(o):
    status = STATUS_LABELS.get(getattr(o, "status", None), "—") if o.is_paid else "⏳ Не оплачен"
    return (
        f"<b>Заказ #{o.id}</b>\n"
        f"Дата: {fmt_dt(o.date)}\n"
        f"Клиент: <a href='tg://user?id={o.telegram_id}'>профиль</a>\n"
        f"Товар: {o.flavor} ×{o.bottle_count}\n"
        f"Сумма: {fmt_price(o.price)}\n"
        f"Статус: {status}\n\n"
        f"Адрес: {o.address}\nТелефон: {o.phone}"
    )

@router.callback_query(F.data.startswith("admin:paid:"))
async def admin_mark_paid(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    order_id = int(cb.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        await set_order_paid(db, order_id)
        o = await get_order_by_id(db, order_id)
    await cb.answer("Помечен как оплаченный ✅")
    await send_or_edit(cb, await _render_order_text(o), order_admin_actions_kb(o.id, o.is_paid))

# ---------- Products ----------
class AdminAddProduct(StatesGroup):
    name = State()
    price = State()

def products_list_kb(page: int, has_next: bool, items) -> InlineKeyboardMarkup:
    rows = []
    for p in items:
        rows.append([InlineKeyboardButton(text=f"#{p.id} • {p.name} • {fmt_price(p.price_cents)}", callback_data=f"admin:prod:{p.id}")])
    nav = []
    nav.append(InlineKeyboardButton(text="➕ Добавить", callback_data="admin:padd"))
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:products:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:products:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏁 Админ-меню", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_actions_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"admin:pedit:{pid}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:pdel:{pid}"),
        ],
        [InlineKeyboardButton(text="⬅️ К списку", callback_data="admin:products:0")],
    ])

@router.callback_query(F.data.startswith("admin:products:"))
async def admin_products(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    page = int(cb.data.split(":")[2])
    limit = 10
    async with AsyncSessionLocal() as db:
        items, total = await get_products_page(db, limit=limit, offset=page*limit)
    header = f"<b>🧃 Товары</b> (стр {page+1}, всего {total})"
    await cb.answer()
    await send_or_edit(cb, header, products_list_kb(page, (page+1)*limit < total, items))

@router.callback_query(F.data == "admin:padd")
async def product_add_start(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    await state.set_state(AdminAddProduct.name)
    await cb.answer()
    await send_or_edit(cb, "Введите <b>название товара</b> одной строкой:", InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="admin:products:0")]]
    ))

@router.message(AdminAddProduct.name)
async def product_add_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await deny_not_admin(message)
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AdminAddProduct.price)
    await message.answer(f"Название: <b>{name}</b>\nТеперь введите <b>цену</b> (например: 350, 350.00, 350,50):")

def parse_price_to_cents(s: str) -> int:
    s = s.strip().replace("₽", "").replace("руб", "").replace(" ", "")
    s = s.replace(",", ".")
    if "." in s:
        rub, frac = s.split(".", 1)
        frac = (frac + "00")[:2]
        return int(rub) * 100 + int(frac)
    return int(float(s)) * 100

@router.message(AdminAddProduct.price)
async def product_add_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await deny_not_admin(message)
    try:
        price_cents = parse_price_to_cents(message.text)
    except Exception:
        return await message.answer("Не понял цену. Пример: 350 или 350.50")
    data = await state.get_data()
    name = data["name"]
    async with AsyncSessionLocal() as db:
        await create_product(db, name=name, price_cents=price_cents)
        items, total = await get_products_page(db, limit=10, offset=0)
    await state.clear()
    await message.answer("Товар добавлен ✅")
    await message.answer("<b>🧃 Товары</b> (стр 1)", reply_markup=products_list_kb(0, total > 10, items))

@router.callback_query(F.data.startswith("admin:prod:"))
async def product_open(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    pid = int(cb.data.split(":")[2])
    # Здесь показываем карточку товара по id (минимал)
    async with AsyncSessionLocal() as db:
        items, _ = await get_products_page(db, limit=1, offset=0)  # простой способ показать список заново
    await cb.answer()
    await send_or_edit(cb, f"<b>Товар #{pid}</b>\nВыберите действие:", product_actions_kb(pid))

@router.callback_query(F.data.startswith("admin:pdel:"))
async def product_delete(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    pid = int(cb.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        await delete_product(db, pid)
        items, total = await get_products_page(db, limit=10, offset=0)
    await cb.answer("Удалено ✅")
    await send_or_edit(cb, "<b>🧃 Товары</b> (стр 1)", products_list_kb(0, total > 10, items))

class AdminEditPrice(StatesGroup):
    pid = State()
    price = State()

@router.callback_query(F.data.startswith("admin:pedit:"))
async def product_edit_price(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await deny_not_admin(cb)
    pid = int(cb.data.split(":")[2])
    await state.set_state(AdminEditPrice.pid)
    await state.update_data(pid=pid)
    await state.set_state(AdminEditPrice.price)
    await cb.answer()
    await send_or_edit(cb, f"Введите новую цену для товара #{pid}:")

@router.message(AdminEditPrice.price)
async def product_edit_price_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await deny_not_admin(message)
    data = await state.get_data()
    pid = data["pid"]
    try:
        price_cents = parse_price_to_cents(message.text)
    except Exception:
        return await message.answer("Не понял цену. Пример: 350 или 350.50")
    async with AsyncSessionLocal() as db:
        await update_product_price(db, pid, price_cents)
        items, total = await get_products_page(db, limit=10, offset=0)
    await state.clear()
    await message.answer("Цена обновлена ✅")
    await message.answer("<b>🧃 Товары</b> (стр 1)", reply_markup=products_list_kb(0, total > 10, items))
