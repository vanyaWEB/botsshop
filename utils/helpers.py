from aiogram import Bot
from aiogram.types import User as TelegramUser
from database.models import User
from database.db import get_db
from database import crud
import config


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Check if user is subscribed to required channel"""
    if not config.REQUIRED_CHANNEL_ID:
        return True
    
    try:
        member = await bot.get_chat_member(config.REQUIRED_CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False


async def is_subscribed(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Check if user is subscribed to channel"""
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in config.ADMIN_IDS


def format_price(price: float) -> str:
    """Format price with currency"""
    return f"{price:,.2f}₽".replace(',', ' ')


def get_status_text(status: str) -> str:
    """Get human-readable status text"""
    statuses = {
        'pending': '⏳ Ожидает оплаты',
        'paid': '✅ Оплачен',
        'processing': '📦 В обработке',
        'shipped': '🚚 Отправлен',
        'delivered': '✅ Доставлен',
        'cancelled': '❌ Отменен',
        'completed': '✅ Завершен'
    }
    return statuses.get(status, status)


def format_order_details(order) -> str:
    """Format order details for display"""
    items_text = "\n".join([
        f"  • {item.product_name} {f'({item.size})' if item.size else ''} x{item.quantity} - {format_price(item.product_price * item.quantity)}"
        for item in order.items
    ])
    
    text = f"""
📦 <b>Заказ {order.order_number}</b>

<b>Статус:</b> {get_status_text(order.status)}
<b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}

<b>Товары:</b>
{items_text}

<b>Итого:</b> {format_price(order.total_amount)}
"""
    
    if order.phone:
        text += f"\n<b>Телефон:</b> {order.phone}"
    if order.delivery_address:
        text += f"\n<b>Адрес доставки:</b> {order.delivery_address}"
    if order.comment:
        text += f"\n<b>Комментарий:</b> {order.comment}"
    
    return text.strip()


def format_product_details(product) -> str:
    """Format product details for display"""
    text = f"""
<b>{product.name}</b>

{product.description}

<b>Цена:</b> {format_price(product.price)}
<b>В наличии:</b> {product.stock} шт.
"""
    
    if product.sizes:
        import json
        sizes = json.loads(product.sizes)
        text += f"\n<b>Размеры:</b> {', '.join(sizes)}"
    
    return text.strip()


async def get_or_create_user_from_telegram(telegram_user: TelegramUser) -> User:
    """Get or create user from Telegram user object"""
    with get_db() as db:
        user = crud.get_or_create_user(
            db,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name
        )
        return user


def get_user_theme(db, telegram_id: int) -> str:
    """Get user's theme preference"""
    user = crud.get_user_by_telegram_id(db, telegram_id)
    return user.theme if user and user.theme else 'light'
