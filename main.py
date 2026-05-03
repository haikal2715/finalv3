# -*- coding: utf-8 -*-
"""
Zenith Bot — Main Entry Point
Menjalankan Aiogram bot + FastAPI web server secara bersamaan
"""

import asyncio
import uvicorn
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.logger import setup_logger
from app.database import get_vps_pool, close_vps_pool
from app.middlewares.auth_middleware import AuthMiddleware
from app.scheduler import setup_scheduler
from app.web_server import app as web_app, set_bot

# Import all routers
from app.handlers.start_handler import router as start_router
from app.handlers.menu_handler import router as menu_router
from app.handlers.request_handler import router as request_router
from app.handlers.alert_handler import router as alert_router
from app.handlers.skill_handler import router as skill_router
from app.handlers.admin_handler import router as admin_router


async def run_bot():
    """Jalankan Aiogram bot"""
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register middleware
    dp.update.middleware(AuthMiddleware())

    # Register routers
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(request_router)
    dp.include_router(alert_router)
    dp.include_router(skill_router)
    dp.include_router(admin_router)

    # Set bot ke web server untuk notifikasi
    set_bot(bot)

    # Setup scheduler
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started")

    # Init VPS DB pool
    try:
        await get_vps_pool()
        logger.info("VPS DB pool initialized")
    except Exception as e:
        logger.warning(f"VPS DB init warning (akan dicoba ulang): {e}")

    # Start polling
    logger.info("Zenith Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await close_vps_pool()
        await bot.session.close()
        logger.info("Zenith Bot stopped")


async def run_web():
    """Jalankan FastAPI web server"""
    config = uvicorn.Config(
        app=web_app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Jalankan bot dan web server secara concurrent"""
    logger.info("=" * 50)
    logger.info("ZENITH BOT v1.0 — Starting...")
    logger.info(f"Environment : {settings.app_env}")
    logger.info(f"Admin ID    : {settings.admin_telegram_id}")
    logger.info("=" * 50)

    await asyncio.gather(
        run_bot(),
        run_web(),
    )


if __name__ == "__main__":
    asyncio.run(main())
