from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from typing import Callable, Dict, Any, Awaitable
import logging
import time

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware to log all incoming updates"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        update: Update = data.get("event_update")
        
        if update and update.message:
            user = update.message.from_user
            if update.message.text:
                message_text = update.message.text[:50]
                logger.info(f"📨 Message from {user.first_name} (ID:{user.id}): {message_text}")
            elif update.message.photo:
                logger.info(f"📷 Photo from {user.first_name} (ID:{user.id})")
        elif update and update.callback_query:
            user = update.callback_query.from_user
            callback_data = update.callback_query.data
            logger.info(f"🔘 Callback from {user.first_name} (ID:{user.id}): {callback_data}")
        
        start_time = time.time()
        
        try:
            result = await handler(event, data)
            duration = (time.time() - start_time) * 1000
            logger.debug(f"⏱ Handler executed in {duration:.2f}ms")
            return result
        except Exception as e:
            logger.error(f"❌ Error in handler: {e}", exc_info=True)
            raise