import logging
from functools import wraps
from aiogram.types import Message, CallbackQuery
from database.db import get_db
from utils.keyboards import get_back_button

logger = logging.getLogger(__name__)


def error_handler(func):
    """Decorator for handling errors in handlers"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            # Find message object
            message = None
            for arg in args:
                if isinstance(arg, Message):
                    message = arg
                    break
                elif isinstance(arg, CallbackQuery):
                    message = arg.message
                    break
            
            if message:
                try:
                    await message.answer(
                        "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору.",
                        reply_markup=get_back_button("main_menu")
                    )
                except:
                    pass
    
    return wrapper


def db_error_handler(func):
    """Decorator for handling database errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {e}", exc_info=True)
            raise
    
    return wrapper


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_price(price_str: str) -> float:
    """Validate and convert price string to float"""
    try:
        price = float(price_str.strip().replace(',', '.'))
        if price <= 0:
            raise ValidationError("Цена должна быть больше 0")
        if price > 1000000:
            raise ValidationError("Цена слишком большая")
        return price
    except ValueError:
        raise ValidationError("Неверный формат цены. Введите число.")


def validate_stock(stock_str: str) -> int:
    """Validate and convert stock string to int"""
    try:
        stock = int(stock_str.strip())
        if stock < 0:
            raise ValidationError("Количество не может быть отрицательным")
        if stock > 100000:
            raise ValidationError("Количество слишком большое")
        return stock
    except ValueError:
        raise ValidationError("Неверный формат количества. Введите целое число.")


def validate_phone(phone: str) -> str:
    """Validate phone number"""
    phone = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if len(phone) < 10:
        raise ValidationError("Номер телефона слишком короткий")
    if len(phone) > 15:
        raise ValidationError("Номер телефона слишком длинный")
    return phone


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """Sanitize and truncate text input"""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text
