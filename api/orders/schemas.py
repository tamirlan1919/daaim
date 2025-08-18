# schemas.py
from pydantic import BaseModel, Field, conint
from typing import List

class OrderCount(BaseModel):
    user_id: int
    total_bottles: int

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

    class Config:
        from_attributes = True
