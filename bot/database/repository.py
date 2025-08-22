# bot/database/repository.py
from __future__ import annotations

from typing import List, Optional, Iterable, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime

from .models import User, Order, OrderItem, Product


# =========================
#          HELPERS
# =========================

def _page_bounds(page: int, page_size: int) -> tuple[int, int]:
    page = max(0, int(page))
    page_size = max(1, int(page_size))
    offset = page * page_size
    return offset, page_size


# =========================
#          USERS
# =========================

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    """Возвращает пользователя по telegram_id (int)."""
    result = await db.execute(select(User).where(User.telegram_id == int(telegram_id)))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    telegram_id: int,
    phone: Optional[str] = None,
    name: Optional[str] = None
) -> User:
    """Создаёт пользователя."""
    user = User(
        telegram_id=int(telegram_id),
        phone=phone,
        name=name,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_phone(db: AsyncSession, telegram_id: int, phone: str) -> Optional[User]:
    """Обновляет телефон пользователя."""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    user.phone = phone
    await db.commit()
    await db.refresh(user)
    return user


async def get_all_users(db: AsyncSession) -> List[User]:
    """Список всех пользователей."""
    result = await db.execute(select(User).order_by(User.id.desc()))
    return result.scalars().all()


async def get_all_users_page(db: AsyncSession, limit: int = 10, offset: int = 0):
    query = select(User).offset(offset).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    total = await db.scalar(select(func.count()).select_from(User))
    return items, total


# =========================
#          ORDERS
# =========================

async def create_order_with_items(
    db: AsyncSession,
    *,
    user_id: int,
    telegram_id: int,
    address: str,
    phone: str,
    items: Iterable[Tuple[int, int]],  # (product_id, quantity)
    unit_price_cents: int,
    is_paid: bool = False,
    status: str = "processing",
) -> Order:
    """
    Создаёт заказ + позиции.
    total_price_cents считается как unit_price_cents * sum(qty).
    """
    now = datetime.utcnow()
    total_qty = sum(q for _, q in items)

    order = Order(
        user_id=user_id,
        telegram_id=int(telegram_id),
        date=now,
        address=address,
        phone=phone,
        is_paid=is_paid,
        status=status,  # требуется столбец orders.status
        total_price_cents=unit_price_cents * total_qty,
    )

    order.items = [
        OrderItem(
            product_id=pid,
            quantity=qty,
            unit_price_cents=unit_price_cents,
            line_total_cents=unit_price_cents * qty,
        )
        for pid, qty in items
    ]

    db.add(order)
    await db.commit()
    await db.refresh(order)

    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product)
        )
        .where(Order.id == order.id)
    )
    return result.scalar_one()


async def get_orders_by_user(db: AsyncSession, user_id: int) -> List[Order]:
    """Список заказов пользователя по user_id (с позициями и продуктами)."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.user_id == user_id)
        .order_by(Order.date.desc())
    )
    return result.scalars().all()


async def get_orders_by_telegram(db: AsyncSession, telegram_id: int) -> List[Order]:
    """Список заказов пользователя по telegram_id (с позициями и продуктами). Удобно для бота."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.telegram_id == int(telegram_id))
        .order_by(Order.date.desc())
    )
    return result.scalars().all()


async def get_order_by_id(db: AsyncSession, order_id: int) -> Optional[Order]:
    """Один заказ по id (с позициями и продуктами)."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_orders_count_by_telegram_id(db: AsyncSession, telegram_id: int) -> int:
    """Кол-во ОПЛАЧЕННЫХ заказов по telegram_id."""
    result = await db.execute(
        select(func.count())
        .select_from(Order)
        .where((Order.telegram_id == int(telegram_id)) & (Order.is_paid == True))
    )
    return int(result.scalar_one())


async def set_order_paid(db: AsyncSession, order_id: int) -> Optional[Order]:
    """Пометить заказ как оплаченный."""
    order = await get_order_by_id(db, order_id)
    if not order:
        return None
    order.is_paid = True
    await db.commit()
    await db.refresh(order)
    return order


async def update_order_status(db: AsyncSession, order_id: int, status: str) -> Optional[Order]:
    """Обновить статус заказа (processing|in_transit|declined|completed)."""
    order = await get_order_by_id(db, order_id)
    if not order:
        return None
    order.status = status
    await db.commit()
    await db.refresh(order)
    return order


# alias под ожидаемое имя в импортах
async def set_order_status(db: AsyncSession, order_id: int, status: str) -> Optional[Order]:
    """Алиас к update_order_status для совместимости с импортами."""
    return await update_order_status(db, order_id, status)


async def get_total_bottles_by_user(db: AsyncSession, telegram_id: int) -> int:
    stmt = (
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .select_from(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .join(User, Order.user_id == User.id)
        .where(User.telegram_id == telegram_id)   # ← ключевая строка
        .where(Order.is_paid.is_(True))
    )
    result = await db.execute(stmt)
    return int(result.scalar_one())


async def get_all_orders(db: AsyncSession) -> List[Order]:
    """Список всех заказов (с позициями и продуктами)."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.date.desc())
    )
    return result.scalars().all()


async def get_all_orders_page(db: AsyncSession, limit: int = 10, offset: int = 0):
    query = select(Order).offset(offset).limit(limit).order_by(Order.date.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    total = await db.scalar(select(func.count()).select_from(Order))
    return items, total

# =========================
#         PRODUCTS
# =========================

async def list_products(db: AsyncSession) -> List[Product]:
    result = await db.execute(select(Product).order_by(Product.name.asc()))
    return result.scalars().all()


async def get_products_page(db: AsyncSession, limit: int = 10, offset: int = 0):
    query = select(Product).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    total = await db.scalar(select(func.count()).select_from(Product))
    return items, total


async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, *, name: str, price_cents: int) -> Product:
    prod = Product(name=name, price_cents=price_cents)
    db.add(prod)
    await db.commit()
    await db.refresh(prod)
    return prod


async def update_product(
    db: AsyncSession,
    product_id: int,
    *,
    name: Optional[str] = None,
    price_cents: Optional[int] = None
) -> Optional[Product]:
    prod = await get_product_by_id(db, product_id)
    if not prod:
        return None
    if name is not None:
        prod.name = name
    if price_cents is not None:
        prod.price_cents = price_cents
    await db.commit()
    await db.refresh(prod)
    return prod


async def update_product_price(db: AsyncSession, product_id: int, price_cents: int) -> Optional[Product]:
    """Точечный апдейт цены — для совместимости с импортами."""
    return await update_product(db, product_id, price_cents=price_cents)


async def delete_product(db: AsyncSession, product_id: int) -> bool:
    prod = await get_product_by_id(db, product_id)
    if not prod:
        return False
    await db.delete(prod)
    await db.commit()
    return True
