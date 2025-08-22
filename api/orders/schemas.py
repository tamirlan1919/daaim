# schemas.py
from enum import Enum

from pydantic import BaseModel, Field, conint
from typing import List, Optional


class OrderCount(BaseModel):
    user_id: int = Field(..., alias="telegram_id")
    total_bottles: int

    class Config:
        populate_by_name = True  # pydantic v1
        # pydantic v2:
        # model_config = {"populate_by_name": True}


class OrderStatus(str, Enum):
    processing = "processing"  # оформляется / на сборке
    in_transit = "in_transit"  # передан в доставку
    declined = "declined"  # отменён / отклонён
    completed = "completed"  # доставлен / завершён


class OrderUpdateAdmin(BaseModel):
    status: Optional[OrderStatus] = None
    is_paid: Optional[bool] = None


class OrderItemCreate(BaseModel):
    product_id: int = Field(..., example=1)
    quantity: int = Field(..., gt=0, example=3)


class OrderCreate(BaseModel):
    telegram_id: int
    address: str
    phone: str
    is_paid: bool = False
    items: List[OrderItemCreate]
    total_price_cents: int


class OrderItemRead(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price_cents: int
    line_total_cents: int

    class Config:
        from_attributes = True


class OrderRead(BaseModel):
    id: int
    telegram_id: int
    address: str
    phone: str
    is_paid: bool
    total_price_cents: int
    items: List[OrderItemRead]
    status: OrderStatus   # 👈 добавить это поле


    class Config:
        from_attributes = True
