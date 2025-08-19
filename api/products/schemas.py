# schemas/product.py
from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    price_cents: int


class ProductRead(ProductBase):
    id: int
    price: float  # цена в рублях

    class Config:
        orm_mode = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    price_cents: int | None = None
