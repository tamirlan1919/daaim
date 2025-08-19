# routes/products.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import Product
from bot.database.engine import get_async_session  # твоя зависимость для БД

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/", summary="Получить список товаров")
async def get_products(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Product))
    products = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "price_cents": p.price_cents,
            "price": round(p.price_cents / 100, 2)  # можно отдать и в рублях
        }
        for p in products
    ]


@router.get("/{product_id}", summary="Получить товар по ID")
async def get_product(product_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        return {"error": "Product not found"}

    return {
        "id": product.id,
        "name": product.name,
        "price_cents": product.price_cents,
        "price": round(product.price_cents / 100, 2)
    }
