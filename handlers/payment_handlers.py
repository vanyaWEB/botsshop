from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy.orm import Session
import logging

from database.db import get_db
from database import crud
from utils.payment import create_payment, check_payment_status
from utils.keyboards import get_back_button
from utils.helpers import format_price
from config import ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("pay_order_"))
async def initiate_payment(callback: CallbackQuery):
    """Initiate payment for order"""
    with get_db() as db:
        order_id = int(callback.data.split("_")[-1])
        
        order = crud.get_order(db, order_id)
        
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        # Check if user owns this order
        user = crud.get_or_create_user(
            db,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name
        )
        
        if order.user_id != user.id:
            await callback.answer("Это не ваш заказ", show_alert=True)
            return
        
        if order.status == 'completed':
            await callback.answer("Заказ уже оплачен", show_alert=True)
            return
        
        if order.status == 'cancelled':
            await callback.answer("Заказ отменен", show_alert=True)
            return
        
        # Create payment
        payment_data = create_payment(
            amount=order.total_amount,
            order_id=order.id,
            description=f"Оплата заказа #{order.id}",
            return_url=f"https://t.me/{(await callback.bot.get_me()).username}"
        )
        
        if not payment_data:
            await callback.answer("Ошибка создания платежа. Попробуйте позже.", show_alert=True)
            return
        
        # Update order with payment ID
        crud.update_order_status(db, order.id, 'pending', payment_id=payment_data['id'])
        
        # Send payment link
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_data['confirmation_url'])],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment_{order.id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="my_orders")]
        ])
        
        text = f"""
<b>💳 Оплата заказа #{order.id}</b>

<b>Сумма:</b> {format_price(order.total_amount)}

Нажмите кнопку "Оплатить" для перехода на страницу оплаты.
После оплаты нажмите "Проверить оплату" для обновления статуса.
"""
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery):
    """Check payment status"""
    with get_db() as db:
        order_id = int(callback.data.split("_")[-1])
        
        order = crud.get_order(db, order_id)
        
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        if not order.payment_id:
            await callback.answer("Платеж не найден", show_alert=True)
            return
        
        # Check payment status
        payment_status = check_payment_status(order.payment_id)
        
        if not payment_status:
            await callback.answer("Ошибка проверки платежа", show_alert=True)
            return
        
        if payment_status['status'] == 'succeeded' and payment_status['paid']:
            # Update order status
            crud.update_order_status(db, order.id, 'completed')
            
            # Notify admins
            await notify_admins_about_order(callback.bot, order)
            
            await callback.message.edit_text(
                f"""
<b>✅ Оплата успешна!</b>

Заказ #{order.id} оплачен и принят в обработку.
Мы свяжемся с вами в ближайшее время.

<b>Сумма:</b> {format_price(order.total_amount)}
""",
                reply_markup=get_back_button("my_orders")
            )
            await callback.answer("Оплата подтверждена!", show_alert=True)
        
        elif payment_status['status'] == 'canceled':
            crud.update_order_status(db, order.id, 'cancelled')
            await callback.answer("Платеж отменен", show_alert=True)
            await callback.message.edit_text(
                f"❌ Платеж отменен.\n\nЗаказ #{order.id} отменен.",
                reply_markup=get_back_button("my_orders")
            )
        
        else:
            await callback.answer(
                f"Статус платежа: {payment_status['status']}\nОжидаем оплату...",
                show_alert=True
            )


async def notify_admins_about_order(bot, order):
    """Notify admins about new paid order"""
    text = f"""
🔔 <b>Новый заказ #{order.id}</b>

<b>👤 Покупатель:</b>
ID: {order.user.telegram_id}
Username: @{order.user.username or 'не указан'}
Имя: {order.user.first_name or 'не указано'}

<b>📦 Товары:</b>
"""
    
    for item in order.items:
        size_text = f" ({item.size})" if item.size else ""
        text += f"• {item.product_name}{size_text} × {item.quantity}\n"
    
    text += f"\n<b>💰 Сумма:</b> {format_price(order.total_amount)}"
    
    if order.phone:
        text += f"\n<b>📱 Телефон:</b> {order.phone}"
    if order.delivery_address:
        text += f"\n<b>📍 Адрес:</b> {order.delivery_address}"
    if order.comment:
        text += f"\n<b>💬 Комментарий:</b> {order.comment}"
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Управление заказом", callback_data=f"admin_order_{order.id}")]
    ])
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
