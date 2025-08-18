from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

def get_web_app():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📲 Заказать колд брю",
                    web_app=WebAppInfo(url="https://daim-delta.vercel.app")
                )
            ]
        ],
        resize_keyboard=True
    )
    return keyboard