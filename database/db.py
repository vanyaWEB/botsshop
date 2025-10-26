from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from database.models import Base
import config
import time
import logging

logger = logging.getLogger(__name__)

engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    connect_args={
        "connect_timeout": 10,
        "options": "-c timezone=utc"
    }
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db(max_retries=5, retry_delay=2):
    """Initialize database tables with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully!")
            return
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error("Failed to connect to database after all retries")
                raise


@contextmanager
def get_db():
    """Get database session as context manager"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Session:
    """Get database session directly (must be closed manually)"""
    return SessionLocal()


def check_db_connection():
    """Check if database connection is working"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
