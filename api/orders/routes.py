from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import select, func

# Импорты для асинхронных роутов
from bot.database.engine import get_async_session
from bot.database.repository import get_total_bottles_by_user, get_user_by_telegram_id
from .schemas import  OrderCount, OrderCreate, OrderRead


# Импорты для синхронных роутов
from bot.database.engine import get_async_session
from bot.database.models import Order, OrderItem, Product

PRICING_TIERS = [
    (20, 99, 250),
    (100, 499, 240),
    (500, 999, 220),
    (1000, 1999, 200),
    (2000, float('inf'), 180),
]

def get_price_by_total(total_bottles: int) -> int:
    for min_val, max_val, price in PRICING_TIERS:
        if min_val <= total_bottles <= max_val:
            return price
    return PRICING_TIERS[-1][2]

# Первый роутер для асинхронных заказов
router = APIRouter(
    prefix="/orders",
    tags=["Заказы 🚚"],
)

@router.get("/")
async def list_orders():
    return {'orders': 'This is a placeholder for the order list'}

@router.get("/users/{user_id}", response_model=OrderCount)
async def get_user_bottle_count(user_id: int, db: AsyncSession = Depends(get_async_session)):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    total_bottles = await get_total_bottles_by_user(db, user_id)
    return {"user_id": user_id, "total_bottles": total_bottles}


@router.post("/", response_model=OrderRead)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_async_session)):
    user = await get_user_by_telegram_id(db, payload.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Считаем сколько всего бутылок купил пользователь до этого (только оплаченные заказы)
    result = await db.execute(
        select(func.sum(OrderItem.quantity))
        .join(Order)
        .where((Order.user_id == user.id) & (Order.is_paid == True))
    )
    past_total = result.scalar() or 0

    # Считаем сколько бутылок в этом заказе
    current_total = sum(item.quantity for item in payload.items)
    new_total = past_total + current_total

    # Определяем цену за бутылку
    price_per_bottle = get_price_by_total(new_total)
    calculated_total = price_per_bottle * current_total

    # Проверяем сумму
    if payload.total_price_cents != calculated_total:
        raise HTTPException(status_code=400, detail=f"Сумма не совпадает! Ожидалось {calculated_total}, получено {payload.total_price_cents}")

    # Получаем продукты
    product_ids = {i.product_id for i in payload.items}
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products = result.scalars().all()
    map_products = {p.id: p for p in products}

    # Проверка, что все продукты существуют
    missing = product_ids - set(map_products.keys())
    if missing:
        raise HTTPException(status_code=404, detail=f"Products not found: {sorted(missing)}")

    # Создаём заказ
    order = Order(
        user_id=user.id,
        telegram_id=payload.telegram_id,
        address=payload.address,
        phone=payload.phone,
        is_paid=payload.is_paid,
        total_price_cents=calculated_total
    )

    items = []
    for it in payload.items:
        prod = map_products[it.product_id]
        unit = price_per_bottle  # Цена по накопительной системе
        line = unit * it.quantity
        item = OrderItem(
            product_id=prod.id,
            quantity=it.quantity,
            unit_price_cents=unit,
            line_total_cents=line
        )
        items.append(item)

    order.items = items
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order

