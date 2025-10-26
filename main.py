"""
Unified launcher for Telegram Bot and Web App
Runs both services in parallel with shared database
"""
import asyncio
import logging
import sys
import os
from threading import Thread

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_webapp():
    """Run Flask web application"""
    from webapp.app import app
    import config
    
    logger.info(f"Starting Web App on port {config.WEBAPP_PORT}...")
    app.run(
        host='0.0.0.0',
        port=config.WEBAPP_PORT,
        debug=False,
        use_reloader=False
    )


async def run_bot():
    """Run Telegram bot"""
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.fsm.storage.memory import MemoryStorage
    
    import config
    from database.db import init_db, check_db_connection
    from handlers import user_handlers, admin_handlers, cart_handlers, order_handlers, payment_handlers
    
    logger.info("Initializing shared database...")
    try:
        init_db(max_retries=10, retry_delay=3)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.error("Please check your DATABASE_URL and ensure PostgreSQL is running")
        sys.exit(1)
    
    if not check_db_connection():
        logger.error("Database connection verification failed")
        sys.exit(1)
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register routers
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(cart_handlers.router)
    dp.include_router(order_handlers.router)
    dp.include_router(payment_handlers.router)
    
    logger.info("Telegram Bot started successfully!")
    logger.info(f"Admin IDs: {config.ADMIN_IDS}")
    logger.info(f"Web App URL: {config.WEBAPP_URL}")
    
    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


async def main():
    """Main entry point - runs both bot and webapp"""
    logger.info("=" * 60)
    logger.info("Starting E-Commerce Telegram Bot System")
    logger.info("=" * 60)
    
    # Start webapp in separate thread
    webapp_thread = Thread(target=run_webapp, daemon=True)
    webapp_thread.start()
    
    await asyncio.sleep(3)
    
    # Run bot in main thread
    await run_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("System stopped by user")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
