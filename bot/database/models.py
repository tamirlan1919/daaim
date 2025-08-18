from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    phone = Column(String)
    name = Column(String)  # 👈 новое поле
    created_at = Column(DateTime, default=datetime.utcnow)
    orders = relationship('Order', back_populates='user')

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    # Можно сделать Enum('vanilla','caramel',...), но таблица гибче
    name = Column(String, unique=True, nullable=False)
    # хранить деньги лучше в копейках/центах (Integer) или Numeric(10,2)
    price_cents = Column(Integer, nullable=False)

    # опционально: is_active, stock, etc.


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    address = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    # Итоговую сумму лучше хранить отдельным полем для отчетов
    total_price_cents = Column(Integer, nullable=False, default=0)
    is_paid = Column(Boolean, default=False, nullable=False)

    user_id = Column(BigInteger, ForeignKey('users.id'))
    user = relationship('User', back_populates='orders')

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="joined"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    quantity = Column(Integer, nullable=False)         # сколько бутылок данного вкуса
    unit_price_cents = Column(Integer, nullable=False) # цена за 1 на момент заказа
    line_total_cents = Column(Integer, nullable=False) # quantity * unit_price_cents

    order = relationship("Order", back_populates="items")
    product = relationship("Product")