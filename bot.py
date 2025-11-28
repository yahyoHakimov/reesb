import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.connection import init_db
from handlers import start_router, receipt_router, session_setup_router, meal_selection_router
from middleware import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 70)
    logger.info("🚀 Starting Receipt Splitter Bot...")
    logger.info("=" * 70)
    
    try:
        logger.info("📊 Initializing database...")
        
        await init_db(reset=True)
        logger.info("✅ Database initialized!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return

    try:
        logger.info("🤖 Creating bot instance...")
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        logger.info("⚙️ Creating dispatcher...")
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        logger.info("🔧 Setting up middleware...")
        dp.message.middleware(LoggingMiddleware())
        dp.callback_query.middleware(LoggingMiddleware())

        logger.info("📝 Registering handlers...")
        dp.include_router(start_router)
        dp.include_router(receipt_router)
        dp.include_router(session_setup_router)
        dp.include_router(meal_selection_router)

        logger.info("=" * 70)
        logger.info("✅ Bot started successfully!")
        logger.info("👂 Waiting for messages...")
        logger.info("⌨️  Press Ctrl+C to stop")
        logger.info("=" * 70)
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        logger.info("🔌 Closing bot...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 70)
        logger.info("🛑 Bot stopped by user")
        logger.info("=" * 70)