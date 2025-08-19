from aiogram import Bot, Dispatcher
import logging
import asyncio
from config import BOT_TOKEN
from handlers import router
from database.engine import engine as async_engine
from database.models import Base

async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def main():
    logging.basicConfig(level=logging.INFO)
    await create_tables()  # ← добавь это
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as error:
        print(error)





