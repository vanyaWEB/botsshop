import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required in .env file")

BOT_URL = os.getenv("BOT_URL", "https://yourdomain.com")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

if not ADMIN_IDS:
    raise ValueError("At least one ADMIN_ID is required in .env file")

# YooKassa Configuration
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Web App Configuration
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8080")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", 8080))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Default to PostgreSQL for production, SQLite for local dev
    DATABASE_URL = "postgresql://user:password@localhost:5432/shop_db"
    print("WARNING: DATABASE_URL not set, using default PostgreSQL connection")

# Convert postgres:// to postgresql:// for SQLAlchemy compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "postgresql://" in DATABASE_URL:
    # Ensure proper connection parameters for Railway/production
    if "?" not in DATABASE_URL:
        DATABASE_URL += "?connect_timeout=10"
    else:
        if "connect_timeout" not in DATABASE_URL:
            DATABASE_URL += "&connect_timeout=10"

# Channel Configuration (optional)
REQUIRED_CHANNEL_ID = os.getenv("REQUIRED_CHANNEL_ID")
REQUIRED_CHANNEL_URL = os.getenv("REQUIRED_CHANNEL_URL")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-please")

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
