from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger,
    Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# -------- Статусы заказа --------
class OrderStatus(str, Enum):
    processing = "processing"     # оформляется / на сборке
    in_transit = "in_transit"     # передан в доставку
    declined = "declined"         # отменён / отклонён
    completed = "completed"       # доставлен / завершён


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    phone = Column(String)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    orders = relationship(
        'Order',
        back_populates='user',
        cascade="save-update",
        lazy="selectin",   # масштабируется лучше, чем joined, когда у юзера много заказов
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    # деньги храним в центах/копейках
    price_cents = Column(Integer, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)

    total_price_cents = Column(Integer, nullable=False, default=0)
    is_paid = Column(Boolean, default=False, nullable=False)

    # 🔧 Исправлено: тип FK теперь Integer, как и users.id
    user_id = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"), nullable=True)
    user = relationship('User', back_populates='orders', lazy="selectin")

    # 🔥 Новый статус (ENUM на уровне БД)
    status = Column(
        SAEnum(OrderStatus, name="order_status", create_constraint=True),
        nullable=False,
        default=OrderStatus.processing,
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)          # сколько единиц позиции
    unit_price_cents = Column(Integer, nullable=False)  # цена за 1 на момент заказа
    line_total_cents = Column(Integer, nullable=False)  # quantity * unit_price_cents

    order = relationship("Order", back_populates="items", lazy="selectin")
    product = relationship("Product", lazy="selectin")
