from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from bot.database.engine import AsyncSessionLocal
from bot.database.models import Product
from sqlalchemy.future import select
from bot.database.repository import get_all_users, get_all_orders

router = Router()

# --- FSM для добавления вкуса ---
class AddProduct(StatesGroup):
    waiting_for_name = State()
    waiting_for_price = State()

# --- FSM для редактирования вкуса ---
class EditProduct(StatesGroup):
    waiting_for_product = State()
    waiting_for_new_price = State()

@router.message(Command('admin'))
async def admin_panel(message: Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="➕ Добавить вкус")],
            [types.KeyboardButton(text="📝 Редактировать цену")],
            [types.KeyboardButton(text="👥 Пользователи"), types.KeyboardButton(text="📦 Заказы")]
        ],
        resize_keyboard=True
    )
    await message.answer("👑 Админ-панель", reply_markup=kb)

# --- Добавление вкуса ---
@router.message(F.text == "➕ Добавить вкус")
async def add_product_start(message: Message, state: FSMContext):
    await message.answer("Введите название нового вкуса:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddProduct.waiting_for_name)

@router.message(AddProduct.waiting_for_name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите цену (в рублях) за одну бутылку:")
    await state.set_state(AddProduct.waiting_for_price)

@router.message(AddProduct.waiting_for_price)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("Введите корректную цену (число)!")
        return
    data = await state.get_data()
    name = data['name']
    async with AsyncSessionLocal() as db:
        db.add(Product(name=name, price_cents=price*100))
        await db.commit()
    await message.answer(f"Вкус '{name}' добавлен с ценой {price}₽.", reply_markup=ReplyKeyboardRemove())
    await state.clear()

# --- Редактирование цены вкуса ---
@router.message(F.text == "📝 Редактировать цену")
async def edit_product_start(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Product))
        products = result.scalars().all()
    if not products:
        await message.answer("Нет вкусов для редактирования.")
        return
    product_names = [p.name for p in products]
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=name)] for name in product_names],
        resize_keyboard=True
    )
    await message.answer("Выберите вкус для редактирования:", reply_markup=kb)
    await state.set_state(EditProduct.waiting_for_product)

@router.message(EditProduct.waiting_for_product)
async def edit_product_choose(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer("Введите новую цену (в рублях):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditProduct.waiting_for_new_price)

@router.message(EditProduct.waiting_for_new_price)
async def edit_product_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("Введите корректную цену (число)!")
        return
    data = await state.get_data()
    name = data['product_name']
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Product).where(Product.name == name))
        product = result.scalar_one_or_none()
        if not product:
            await message.answer("Вкус не найден.")
            await state.clear()
            return
        product.price_cents = price * 100
        await db.commit()
    await message.answer(f"Цена для '{name}' обновлена на {price}₽.", reply_markup=ReplyKeyboardRemove())
    await state.clear()

# --- Просмотр пользователей ---
@router.message(F.text == "👥 Пользователи")
async def show_users(message: Message):
    async with AsyncSessionLocal() as db:
        users = await get_all_users(db)
    if not users:
        await message.answer("Пользователей нет.")
        return
    text = "Пользователи:\n" + "\n".join([f"{u.id}: {u.name or ''} (tg: {u.telegram_id})" for u in users])
    await message.answer(text)

# --- Просмотр заказов ---
@router.message(F.text == "📦 Заказы")
async def show_orders(message: Message):
    async with AsyncSessionLocal() as db:
        orders = await get_all_orders(db)
    if not orders:
        await message.answer("Заказов нет.")
        return
    text = "Заказы:\n" + "\n".join([
        f"#{o.id} | {o.address} | {o.total_price_cents/100:.2f}₽ | Оплачен: {'Да' if o.is_paid else 'Нет'}"
        for o in orders[:20]
    ])
    await message.answer(text)