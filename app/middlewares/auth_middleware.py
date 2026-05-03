# -*- coding: utf-8 -*-
"""
Zenith Bot — Auth Middleware
Inject user data ke setiap update Aiogram
"""

from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger

from app.services.auth_service import get_user_by_telegram_id
from app.services.subscription_service import get_active_subscription


class AuthMiddleware(BaseMiddleware):
    """
    Middleware yang inject user info ke handler data.
    Handler bisa akses via: data['user'], data['subscription'], data['tier']
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            telegram_id = None

            if hasattr(event, "message") and event.message:
                telegram_id = event.message.from_user.id
            elif hasattr(event, "callback_query") and event.callback_query:
                telegram_id = event.callback_query.from_user.id

            if telegram_id:
                user = await get_user_by_telegram_id(telegram_id)
                data["user"] = user
                data["telegram_id"] = telegram_id

                if user:
                    sub = await get_active_subscription(user["id"])
                    data["subscription"] = sub
                    data["tier"] = sub["tier"] if sub else None
                else:
                    data["subscription"] = None
                    data["tier"] = None
            else:
                data["user"] = None
                data["subscription"] = None
                data["tier"] = None
                data["telegram_id"] = None

        except Exception as e:
            logger.error(f"AuthMiddleware error: {e}")
            data["user"] = None
            data["subscription"] = None
            data["tier"] = None

        return await handler(event, data)
