from aiogram import Bot, Dispatcher
import logging
import asyncio
from config import BOT_TOKEN
from handlers import router

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as error:
        print(error)





