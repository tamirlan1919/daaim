from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from bot.database.engine import get_async_session
from bot.database.repository import get_user_by_telegram_id, get_total_bottles_by_user
from bot.database.models import Order, OrderItem, Product, User
from .schemas import OrderCreate, OrderRead, OrderCount,  OrderStatus, OrderUpdateAdmin

router = APIRouter(
    prefix="/orders",
    tags=["Заказы 🚚"],
)

# --- Ценовые уровни (накопительный эффект) ---
PRICING_TIERS = [
    (1, 19, 250),      # 👈 базовый уровень
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

# --- Роуты ---

@router.get("/users/bottles/{telegram_id}", response_model=OrderCount)
async def get_user_bottle_count(telegram_id: int, db: AsyncSession = Depends(get_async_session)):
    if telegram_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    total_bottles = await get_total_bottles_by_user(db, telegram_id)
    # вариант с алиасом
    return OrderCount(user_id=telegram_id, total_bottles=total_bottles).model_dump(by_alias=True)

@router.get("/users/{telegram_id}", response_model=List[OrderRead])
async def get_user_orders(
    telegram_id: int,
    db: AsyncSession = Depends(get_async_session),
    title: Optional[str] = Query(
        None, description="Номер заказа (id) или часть адреса"
    ),
    status: Optional[OrderStatus] = Query(
        None, description="Статус: processing | in_transit | declined | completed"
    ),
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Максимум заказов (1–1000)"
    ),

):
    """Получить заказы пользователя с фильтрами по адресу/номеру и статусу"""
    if telegram_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    stmt = select(Order).where(Order.telegram_id == telegram_id)

    # title: число -> поиск по Order.id; иначе ILIKE по адресу
    if title:
        t = title.strip()
        if t.isdigit():
            stmt = stmt.where(Order.id == int(t))
        else:
            stmt = stmt.where(Order.address.ilike(f"%{t}%"))

    if status is not None:
        stmt = stmt.where(Order.status == status)

    stmt = stmt.order_by(Order.date.desc())


    if limit:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=OrderRead)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_async_session)):
    """Создать заказ"""
    user = await get_user_by_telegram_id(db, payload.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # прошлые бутылки (только оплаченные)
    result = await db.execute(
        select(func.sum(OrderItem.quantity))
        .join(Order)
        .where((Order.user_id == user.id) & (Order.is_paid == True))
    )
    past_total = result.scalar() or 0

    # новые бутылки
    current_total = sum(item.quantity for item in payload.items)
    new_total = past_total + current_total

    # цена за 1 по накопительной системе
    price_per_bottle = get_price_by_total(new_total)
    calculated_total = price_per_bottle * current_total

    if payload.total_price_cents != calculated_total:
        raise HTTPException(
            status_code=400,
            detail=f"Сумма не совпадает! Ожидалось {calculated_total}, получено {payload.total_price_cents}"
        )

    # Проверка продуктов
    product_ids = {i.product_id for i in payload.items}
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products = result.scalars().all()
    map_products = {p.id: p for p in products}

    missing = product_ids - set(map_products.keys())
    if missing:
        raise HTTPException(status_code=404, detail=f"Products not found: {sorted(missing)}")

    # Создание заказа
    order = Order(
        user_id=user.id,
        telegram_id=payload.telegram_id,
        address=payload.address,
        phone=payload.phone,
        is_paid=payload.is_paid,
        total_price_cents=calculated_total,
        status=OrderStatus.processing,   # 👈 новый статус по умолчанию
    )

    # Позиции заказа
    order.items = [
        OrderItem(
            product_id=it.product_id,
            quantity=it.quantity,
            unit_price_cents=price_per_bottle,
            line_total_cents=price_per_bottle * it.quantity,
        )
        for it in payload.items
    ]

    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/", response_model=List[OrderRead])
async def list_orders(db: AsyncSession = Depends(get_async_session)):
    """Список всех заказов (для админа)"""
    result = await db.execute(select(Order).order_by(Order.date.desc()))
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, db: AsyncSession = Depends(get_async_session)):
    """Получить один заказ"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderRead)
async def admin_update_order(
    order_id: int,
    payload: OrderUpdateAdmin,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Админский апдейт заказа: можно менять статус и ключ is_paid
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if payload.status is not None:
        order.status = payload.status
    if payload.is_paid is not None:
        order.is_paid = payload.is_paid

    await db.commit()
    await db.refresh(order)
    return order