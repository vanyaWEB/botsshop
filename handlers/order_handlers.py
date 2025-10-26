from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.orm import Session

from database.db import get_db
from database import crud
from utils.keyboards import get_orders_keyboard, get_order_detail_keyboard, get_back_button
from utils.helpers import format_price, get_user_theme

router = Router()


@router.callback_query(F.data == "my_orders")
async def show_orders(callback: CallbackQuery):
    """Show user's orders"""
    try:
        with get_db() as db:
            user = crud.get_or_create_user(
                db,
                callback.from_user.id,
                callback.from_user.username,
                callback.from_user.first_name,
                callback.from_user.last_name
            )
            
            orders = crud.get_orders(db, user_id=user.id, limit=20)
            
            if not orders:
                await callback.message.edit_text(
                    "<b>📦 Мои заказы</b>\n\nУ вас пока нет заказов.",
                    reply_markup=get_back_button("main_menu")
                )
                await callback.answer()
                return
            
            text = "<b>📦 Мои заказы</b>\n\nВыберите заказ для просмотра деталей:\n\n"
            
            for order in orders[:10]:
                status_text = {
                    'pending': '⏳ Ожидает оплаты',
                    'processing': '🔄 В обработке',
                    'completed': '✅ Завершен',
                    'cancelled': '❌ Отменен'
                }.get(order.status, '❓ Неизвестно')
                
                text += f"Заказ #{order.id} • {format_price(order.total_amount)}\n"
                text += f"{status_text} • {order.created_at.strftime('%d.%m.%Y')}\n\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_orders_keyboard(orders)
            )
            await callback.answer()
    except Exception as e:
        await callback.answer("Ошибка при загрузке заказов", show_alert=True)
        print(f"[ERROR] show_orders: {e}")


@router.callback_query(F.data.startswith("order_"))
async def show_order_details(callback: CallbackQuery):
    """Show order details"""
    try:
        with get_db() as db:
            order_id = int(callback.data.split("_")[-1])
            
            order = crud.get_order(db, order_id)
            
            if not order:
                await callback.answer("Заказ не найден", show_alert=True)
                return
            
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
            
            status_text = {
                'pending': '⏳ Ожидает оплаты',
                'processing': '🔄 В обработке',
                'completed': '✅ Завершен',
                'cancelled': '❌ Отменен'
            }.get(order.status, '❓ Неизвестно')
            
            text = f"""
<b>📦 Заказ #{order.id}</b>

<b>Статус:</b> {status_text}
<b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}

<b>📋 Товары:</b>
"""
            
            for item in order.items:
                size_text = f" ({item.size})" if item.size else ""
                text += f"• {item.product_name}{size_text}\n"
                text += f"  {item.quantity} × {format_price(item.price)} = {format_price(item.quantity * item.price)}\n"
            
            text += f"\n<b>💰 Итого: {format_price(order.total_amount)}</b>"
            
            if order.phone:
                text += f"\n\n<b>📱 Телефон:</b> {order.phone}"
            if order.delivery_address:
                text += f"\n<b>📍 Адрес:</b> {order.delivery_address}"
            if order.comment:
                text += f"\n<b>💬 Комментарий:</b> {order.comment}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_order_detail_keyboard(order)
            )
            await callback.answer()
    except Exception as e:
        await callback.answer("Ошибка при загрузке заказа", show_alert=True)
        print(f"[ERROR] show_order_details: {e}")


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery):
    """Cancel order"""
    try:
        with get_db() as db:
            order_id = int(callback.data.split("_")[-1])
            
            order = crud.get_order(db, order_id)
            
            if not order:
                await callback.answer("Заказ не найден", show_alert=True)
                return
            
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
            
            if order.status != 'pending':
                await callback.answer("Этот заказ нельзя отменить", show_alert=True)
                return
            
            crud.update_order_status(db, order_id, 'cancelled')
            
            await callback.answer("Заказ отменен", show_alert=True)
            await show_orders(callback)
    except Exception as e:
        await callback.answer("Ошибка при отмене заказа", show_alert=True)
        print(f"[ERROR] cancel_order: {e}")
