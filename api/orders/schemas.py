from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class OrderCount(BaseModel):
    user_id: int = Field(..., alias="telegram_id")
    total_bottles: int
    class Config:
        populate_by_name = True

class OrderStatus(str, Enum):
    processing = "processing"
    in_transit = "in_transit"
    declined = "declined"
    completed = "completed"

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

class ProductRead(BaseModel):
    id: int
    name: str
    price_cents: int
    class Config:
        from_attributes = True

class OrderItemRead(BaseModel):
    id: int
    order_id: int              # ← добавить
    product_id: int
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    product: ProductRead
    class Config:
        from_attributes = True

class UserRead(BaseModel):
    id: int
    name: str
    telegram_id: int
    phone: Optional[str] = None
    created_at: datetime       # ← пусть будет datetime (автосериализуется в строку)
    class Config:
        from_attributes = True

class OrderRead(BaseModel):
    id: int
    telegram_id: int
    user_id: int               # ← добавить
    address: str
    phone: str
    is_paid: bool
    total_price_cents: int
    items: List[OrderItemRead]
    status: OrderStatus
    date: datetime             # ← тоже datetime
    user: UserRead
    class Config:
        from_attributes = True