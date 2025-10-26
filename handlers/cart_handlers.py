from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session

from database.db import get_db
from database import crud
from utils.keyboards import get_cart_keyboard, get_back_button
from utils.helpers import format_price, get_user_theme, is_subscribed
from config import REQUIRED_CHANNEL_ID

router = Router()


class CheckoutStates(StatesGroup):
    waiting_phone = State()
    waiting_address = State()
    waiting_comment = State()


@router.callback_query(F.data == "cart")
async def show_cart(callback: CallbackQuery):
    """Show user's cart"""
    try:
        with get_db() as db:
            user = crud.get_or_create_user(
                db,
                callback.from_user.id,
                callback.from_user.username,
                callback.from_user.first_name,
                callback.from_user.last_name
            )
            
            cart_items = crud.get_cart_items(db, user.id)
            
            if not cart_items:
                await callback.message.edit_text(
                    "<b>🛒 Ваша корзина</b>\n\nКорзина пуста. Добавьте товары из каталога!",
                    reply_markup=get_back_button("main_menu")
                )
                await callback.answer()
                return
            
            total = sum(item.product.price * item.quantity for item in cart_items)
            
            text = "<b>🛒 Ваша корзина</b>\n\n"
            
            for item in cart_items:
                size_text = f" (Размер: {item.size})" if item.size else ""
                item_total = item.product.price * item.quantity
                text += f"<b>{item.product.name}</b>{size_text}\n"
                text += f"{item.quantity} × {format_price(item.product.price)} = {format_price(item_total)}\n\n"
            
            text += f"<b>Итого: {format_price(total)}</b>"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_cart_keyboard(cart_items, total)
            )
            await callback.answer()
    except Exception as e:
        await callback.answer("Произошла ошибка при загрузке корзины", show_alert=True)
        print(f"[ERROR] show_cart: {e}")


@router.callback_query(F.data.startswith("cart_increase_"))
async def increase_cart_item(callback: CallbackQuery):
    """Increase cart item quantity"""
    try:
        with get_db() as db:
            cart_item_id = int(callback.data.split("_")[-1])
            
            cart_item = crud.get_cart_item(db, cart_item_id)
            if not cart_item:
                await callback.answer("Товар не найден", show_alert=True)
                return
            
            if cart_item.quantity >= cart_item.product.stock:
                await callback.answer(f"Максимальное количество: {cart_item.product.stock}", show_alert=True)
                return
            
            crud.update_cart_item(db, cart_item_id, cart_item.quantity + 1)
            
            await callback.answer("Количество увеличено")
            await show_cart(callback)
    except Exception as e:
        await callback.answer("Ошибка при обновлении количества", show_alert=True)
        print(f"[ERROR] increase_cart_item: {e}")


@router.callback_query(F.data.startswith("cart_decrease_"))
async def decrease_cart_item(callback: CallbackQuery):
    """Decrease cart item quantity"""
    with get_db() as db:
        cart_item_id = int(callback.data.split("_")[-1])
        
        cart_item = crud.get_cart_item(db, cart_item_id)
        if not cart_item:
            await callback.answer("Товар не найден", show_alert=True)
            return
        
        if cart_item.quantity <= 1:
            crud.remove_cart_item(db, cart_item_id)
            await callback.answer("Товар удален из корзины")
        else:
            crud.update_cart_item(db, cart_item_id, cart_item.quantity - 1)
            await callback.answer("Количество уменьшено")
        
        await show_cart(callback)


@router.callback_query(F.data.startswith("cart_remove_"))
async def remove_cart_item(callback: CallbackQuery):
    """Remove item from cart"""
    with get_db() as db:
        cart_item_id = int(callback.data.split("_")[-1])
        
        crud.remove_cart_item(db, cart_item_id)
        
        await callback.answer("Товар удален из корзины")
        await show_cart(callback)


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery):
    """Clear entire cart"""
    with get_db() as db:
        user = crud.get_or_create_user(
            db,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name
        )
        
        crud.clear_cart(db, user.id)
        
        await callback.message.edit_text(
            "<b>🛒 Корзина очищена</b>\n\nВсе товары удалены из корзины.",
            reply_markup=get_back_button("main_menu")
        )
        await callback.answer("Корзина очищена")


@router.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    """Start checkout process"""
    try:
        with get_db() as db:
            if REQUIRED_CHANNEL_ID:
                subscribed = await is_subscribed(callback.bot, callback.from_user.id, REQUIRED_CHANNEL_ID)
                if not subscribed:
                    from utils.keyboards import get_subscription_keyboard
                    await callback.message.edit_text(
                        "<b>⚠️ Требуется подписка</b>\n\nДля оформления заказа необходимо подписаться на наш канал.",
                        reply_markup=get_subscription_keyboard()
                    )
                    await callback.answer()
                    return
            
            user = crud.get_or_create_user(
                db,
                callback.from_user.id,
                callback.from_user.username,
                callback.from_user.first_name,
                callback.from_user.last_name
            )
            
            cart_items = crud.get_cart_items(db, user.id)
            
            if not cart_items:
                await callback.answer("Корзина пуста", show_alert=True)
                return
            
            for item in cart_items:
                if item.product.stock < item.quantity:
                    await callback.answer(
                        f"Недостаточно товара {item.product.name} на складе (доступно: {item.product.stock})",
                        show_alert=True
                    )
                    return
            
            await callback.message.edit_text(
                "<b>📱 Оформление заказа</b>\n\nВведите ваш номер телефона для связи:",
                reply_markup=get_back_button("cart")
            )
            await state.set_state(CheckoutStates.waiting_phone)
            await callback.answer()
    except Exception as e:
        await callback.answer("Ошибка при оформлении заказа", show_alert=True)
        print(f"[ERROR] start_checkout: {e}")


@router.message(CheckoutStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext):
    """Process phone number"""
    phone = message.text.strip()
    
    await state.update_data(phone=phone)
    await message.answer(
        "<b>📍 Адрес доставки</b>\n\nВведите адрес доставки:",
        reply_markup=get_back_button("cart")
    )
    await state.set_state(CheckoutStates.waiting_address)


@router.message(CheckoutStates.waiting_address)
async def process_address(message: Message, state: FSMContext):
    """Process delivery address"""
    address = message.text.strip()
    
    await state.update_data(address=address)
    await message.answer(
        "<b>💬 Комментарий к заказу</b>\n\nВведите комментарий или нажмите /skip чтобы пропустить:",
        reply_markup=get_back_button("cart")
    )
    await state.set_state(CheckoutStates.waiting_comment)


@router.message(CheckoutStates.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    """Process order comment and create order"""
    with get_db() as db:
        comment = None if message.text == "/skip" else message.text.strip()
        
        data = await state.get_data()
        phone = data.get("phone")
        address = data.get("address")
        
        user = crud.get_or_create_user(
            db,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        
        cart_items = crud.get_cart_items(db, user.id)
        
        if not cart_items:
            await message.answer("Корзина пуста", reply_markup=get_back_button("main_menu"))
            await state.clear()
            return
        
        # Create order
        order = crud.create_order(
            db,
            user.id,
            cart_items,
            phone=phone,
            delivery_address=address,
            comment=comment
        )
        
        # Clear cart
        crud.clear_cart(db, user.id)
        
        # Build order summary
        text = f"""
<b>✅ Заказ #{order.id} создан!</b>

<b>📦 Товары:</b>
"""
        
        for item in order.items:
            size_text = f" ({item.size})" if item.size else ""
            text += f"• {item.product_name}{size_text} × {item.quantity} = {format_price(item.price * item.quantity)}\n"
        
        text += f"\n<b>💰 Итого: {format_price(order.total_amount)}</b>\n"
        text += f"\n<b>📱 Телефон:</b> {phone}"
        text += f"\n<b>📍 Адрес:</b> {address}"
        if comment:
            text += f"\n<b>💬 Комментарий:</b> {comment}"
        
        text += "\n\n<b>Для оплаты нажмите кнопку ниже:</b>"
        
        from utils.keyboards import get_checkout_keyboard
        await message.answer(text, reply_markup=get_checkout_keyboard(order.id))
        
        await state.clear()
