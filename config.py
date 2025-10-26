import os
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required in .env file")

BOT_URL = os.getenv("BOT_URL", "https://yourdomain.com")

try:
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    if not ADMIN_IDS:
        raise ValueError("At least one ADMIN_ID is required in .env file")
except ValueError as e:
    logger.error(f"Invalid ADMIN_IDS format: {e}")
    raise ValueError("ADMIN_IDS must be comma-separated integers")

# YooKassa Configuration
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    logger.info("YooKassa payment integration enabled")
else:
    logger.warning("YooKassa credentials not configured - payment features will be disabled")

# Web App Configuration
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8080")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", 8080))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://user:password@localhost:5432/shop_db"
    logger.warning("DATABASE_URL not set, using default PostgreSQL connection")

# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info("Converted postgres:// to postgresql:// for SQLAlchemy compatibility")

if "postgresql://" in DATABASE_URL:
    if "?" not in DATABASE_URL:
        DATABASE_URL += "?connect_timeout=10&application_name=telegram_shop_bot"
    else:
        if "connect_timeout" not in DATABASE_URL:
            DATABASE_URL += "&connect_timeout=10"
        if "application_name" not in DATABASE_URL:
            DATABASE_URL += "&application_name=telegram_shop_bot"

# Channel Configuration (optional)
REQUIRED_CHANNEL_ID = os.getenv("REQUIRED_CHANNEL_ID")
REQUIRED_CHANNEL_URL = os.getenv("REQUIRED_CHANNEL_URL")

if REQUIRED_CHANNEL_ID:
    logger.info(f"Subscription check enabled for channel: {REQUIRED_CHANNEL_ID}")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-please")
if SECRET_KEY == "dev-secret-key-change-in-production-please":
    logger.warning("Using default SECRET_KEY - please set a secure key in production!")

# Theme colors
THEMES = {
    "light": {
        "primary": "#6366f1",
        "secondary": "#8b5cf6",
        "success": "#10b981",
        "danger": "#ef4444",
        "warning": "#f59e0b",
        "background": "#ffffff",
        "surface": "#f9fafb",
        "text": "#111827",
        "text_secondary": "#6b7280",
        "border": "#e5e7eb"
    },
    "dark": {
        "primary": "#818cf8",
        "secondary": "#a78bfa",
        "success": "#34d399",
        "danger": "#f87171",
        "warning": "#fbbf24",
        "background": "#111827",
        "surface": "#1f2937",
        "text": "#f9fafb",
        "text_secondary": "#9ca3af",
        "border": "#374151"
    }
}

def validate_config():
    """Validate critical configuration"""
    errors = []
    
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN is missing")
    
    if not ADMIN_IDS:
        errors.append("ADMIN_IDS is missing or invalid")
    
    if not DATABASE_URL:
        errors.append("DATABASE_URL is missing")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    logger.info("Configuration validated successfully")

# Validate on import
validate_config()
