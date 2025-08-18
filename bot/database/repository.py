from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import User, Order
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import selectinload

# --- USER CRUD ---


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, telegram_id: int, phone: str = None, name: str = None):
    user = User(telegram_id=telegram_id, phone=phone, name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_phone(db: AsyncSession, telegram_id: int, phone: str):
    user = await get_user_by_telegram_id(db, telegram_id)
    if user:
        user.phone = phone
        await db.commit()
        await db.refresh(user)
    return user



# --- ORDER CRUD ---


async def create_order(db: AsyncSession, user_id: int, telegram_id: int, address: str, phone: str, flavor: str, bottle_count: int, price: int, is_paid: bool = False):
    order = Order(
        user_id=user_id,
        telegram_id=telegram_id,
        date=datetime.utcnow(),
        address=address,
        phone=phone,
        flavor=flavor,
        bottle_count=bottle_count,
        price=price,
        is_paid=is_paid
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order

async def get_orders_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Order).where(Order.user_id == user_id).order_by(Order.date.desc())
    )
    return result.scalars().all()

async def get_order_by_id(db: AsyncSession, order_id: int):
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()

async def get_orders_count_by_telegram_id(db: AsyncSession, telegram_id: int) -> int:
    result = await db.execute(
        select(func.count()).select_from(Order).where(Order.telegram_id == telegram_id)
    )
    return result.scalar_one()

async def set_order_paid(db: AsyncSession, order_id: int):
    order = await get_order_by_id(db, order_id)
    if order:
        order.is_paid = True
        await db.commit()
        await db.refresh(order)
    return order

async def get_total_bottles_by_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Order).where(Order.user_id == user_id, Order.is_paid == True)
    )
    orders = result.scalars().all()
    return sum(order.bottle_count for order in orders)

# --- Дополнительно ---

async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()

async def get_all_orders(db: AsyncSession):
    result = await db.execute(select(Order).order_by(Order.date.desc()))
    return result.scalars().all()


