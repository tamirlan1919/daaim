from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from texts import start_message
from keyboards.reply_keyboards import get_web_app
from database.repository import get_user_by_telegram_id, create_user
from database.engine import AsyncSessionLocal  # импортируй сессию

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    keyboard = get_web_app()

    async with AsyncSessionLocal() as db:
        user = await get_user_by_telegram_id(db, str(message.from_user.id))

        if not user:
            await create_user(db, telegram_id=str(message.from_user.id))
        
        await message.answer(start_message, reply_markup=keyboard)

