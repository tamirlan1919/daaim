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
        user = await get_user_by_telegram_id(db, message.from_user.id)

        if not user:
            await create_user(db, telegram_id=message.from_user.id)

        # Отправляем фото
        with open("daim_co", "rb") as photo:
            await message.answer_photo(photo, caption=None)

        await message.answer(start_message, reply_markup=keyboard)

