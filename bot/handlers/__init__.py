from aiogram import Router
from .commands import router as commands_router
from .admin import router as admin_router

router = Router()
router.include_routers(commands_router, admin_router)