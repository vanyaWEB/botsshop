import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database.db import init_db
from handlers import user_handlers, admin_handlers, cart_handlers, order_handlers, payment_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main bot function"""
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(cart_handlers.router)
    dp.include_router(order_handlers.router)
    dp.include_router(payment_handlers.router)
    
    logger.info("Bot started successfully!")
    logger.info(f"Admin IDs: {config.ADMIN_IDS}")
    
    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
