from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from database import crud
from utils.keyboards import (
    get_main_menu_keyboard, get_categories_keyboard, get_products_keyboard,
    get_product_keyboard, get_cart_keyboard, get_orders_keyboard,
    get_order_detail_keyboard, get_subscription_keyboard, get_back_button
)
from utils.helpers import (
    check_subscription, is_admin, format_price, format_order_details,
    format_product_details, get_or_create_user_from_telegram
)
from utils.error_handler import error_handler, ValidationError, validate_phone, sanitize_text
import json

router = Router()


class CheckoutStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_comment = State()


@router.message(CommandStart())
@error_handler
async def cmd_start(message: Message, state: FSMContext):
    """Start command handler"""
    await state.clear()
    
    user = await get_or_create_user_from_telegram(message.from_user)
    
    # Check if user is blocked
    if user.is_blocked:
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь к администратору.")
        return
    
    # Check subscription
    subscribed = await check_subscription(message.bot, message.from_user.id)
    if not subscribed:
        await message.answer(
            "👋 Добро пожаловать в наш магазин одежды!\n\n"
            "Для использования бота необходимо подписаться на наш канал:",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    welcome_text = f"""
👋 Добро пожаловать, {message.from_user.first_name}!

🛍 Это магазин стильной одежды.

Выберите действие из меню ниже:
"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(is_admin(message.from_user.id), user.theme)
    )


@router.callback_query(F.data == "check_subscription")
@error_handler
async def check_sub_callback(callback: CallbackQuery):
    """Check subscription callback"""
    subscribed = await check_subscription(callback.bot, callback.from_user.id)
    
    if subscribed:
        user = await get_or_create_user_from_telegram(callback.from_user)
        await callback.message.edit_text(
            "✅ Отлично! Вы подписаны на канал.\n\n"
            "Выберите действие из меню:",
            reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id), user.theme)
        )
    else:
        await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)


@router.callback_query(F.data == "main_menu")
@error_handler
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Main menu callback"""
    await state.clear()
    
    user = await get_or_create_user_from_telegram(callback.from_user)
    
    await callback.message.edit_text(
        "🏠 Главное меню\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id), user.theme)
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_theme")
@error_handler
async def toggle_theme_callback(callback: CallbackQuery):
    """Toggle theme callback"""
    with get_db() as db:
        user = crud.get_user_by_telegram_id(db, callback.from_user.id)
        new_theme = 'dark' if user.theme == 'light' else 'light'
        crud.update_user_theme(db, callback.from_user.id, new_theme)
        
        theme_name = "Темная" if new_theme == 'dark' else "Светлая"
        await callback.answer(f"✅ Тема изменена на: {theme_name}")
        
        await callback.message.edit_reply_markup(
            reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id), new_theme)
        )


@router.callback_query(F.data == "about")
async def about_callback(callback: CallbackQuery):
    """About callback"""
    about_text = """
ℹ️ <b>О магазине</b>

Мы предлагаем качественную и стильную одежду по доступным ценам.

🚚 Доставка по всей России
💳 Безопасная оплата через ЮKassa
✅ Гарантия качества

По всем вопросам обращайтесь к администратору.
"""
    
    await callback.message.edit_text(
        about_text,
        reply_markup=get_back_button("main_menu")
    )
    await callback.answer()


@router.callback_query(F.data == "catalog")
@error_handler
async def catalog_callback(callback: CallbackQuery):
    """Catalog callback"""
    with get_db() as db:
        categories = crud.get_categories(db, active_only=True)
        
        if not categories:
            await callback.answer("❌ Каталог пуст", show_alert=True)
            return
        
        await callback.message.edit_text(
            "📁 <b>Категории товаров</b>\n\nВыберите категорию:",
            reply_markup=get_categories_keyboard(categories)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("category_"))
@error_handler
async def category_callback(callback: CallbackQuery):
    """Category callback"""
    category_id = int(callback.data.split("_")[1])
    
    with get_db() as db:
        category = crud.get_category(db, category_id)
        if not category:
            await callback.answer("❌ Категория не найдена", show_alert=True)
            return
        
        products = crud.get_products(db, category_id=category_id, active_only=True)
        
        if not products:
            await callback.answer("❌ В этой категории пока нет товаров", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"🛍 <b>{category.name}</b>\n\n{category.description or 'Выберите товар:'}",
            reply_markup=get_products_keyboard(products, category_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("product_"))
@error_handler
async def product_callback(callback: CallbackQuery):
    """Product detail callback"""
    product_id = int(callback.data.split("_")[1])
    
    with get_db() as db:
        product = crud.get_product(db, product_id)
        if not product:
            await callback.answer("❌ Товар не найден", show_alert=True)
            return
        
        # Check if product is in cart
        user = crud.get_user_by_telegram_id(db, callback.from_user.id)
        cart_items = crud.get_cart_items(db, user.id)
        in_cart = any(item.product_id == product_id for item in cart_items)
        
        text = format_product_details(product)
        
        # Send photo if available
        if product.photos:
            photo_ids = product.photos.split(',')
            first_photo = photo_ids[0].strip()
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=first_photo,
                caption=text,
                reply_markup=get_product_keyboard(product, in_cart)
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=get_product_keyboard(product, in_cart)
            )
    
    await callback.answer()


@router.callback_query(F.data.startswith("size_chart_"))
async def size_chart_callback(callback: CallbackQuery):
    """Size chart callback"""
    product_id = int(callback.data.split("_")[2])
    
    with get_db() as db:
        product = crud.get_product(db, product_id)
        if not product or not product.size_chart:
            await callback.answer("❌ Размерная сетка недоступна", show_alert=True)
            return
        
        await callback.answer(product.size_chart, show_alert=True)


@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart_callback(callback: CallbackQuery):
    """Add to cart callback"""
    parts = callback.data.split("_")
    product_id = int(parts[3])
    size = parts[4] if parts[4] != "none" else None
    
    with get_db() as db:
        user = crud.get_user_by_telegram_id(db, callback.from_user.id)
        product = crud.get_product(db, product_id)
        
        if not product or product.stock <= 0:
            await callback.answer("❌ Товар недоступен", show_alert=True)
            return
        
        crud.add_to_cart(db, user.id, product_id, quantity=1, size=size)
        
        size_text = f" (размер {size})" if size else ""
        await callback.answer(f"✅ {product.name}{size_text} добавлен в корзину!")


@router.callback_query(F.data == "cart")
@error_handler
async def cart_callback(callback: CallbackQuery):
    """Cart callback"""
    with get_db() as db:
        user = crud.get_user_by_telegram_id(db, callback.from_user.id)
        cart_items = crud.get_cart_items(db, user.id)
        
        if not cart_items:
            await callback.message.edit_text(
                "🛒 Ваша корзина пуста\n\nДобавьте товары из каталога!",
                reply_markup=get_back_button("main_menu")
            )
            await callback.answer()
            return
        
        total = sum(item.product.price * item.quantity for item in cart_items)
        
        items_text = "\n".join([
            f"• {item.product.name} {f'({item.size})' if item.size else ''} x{item.quantity} - {format_price(item.product.price * item.quantity)}"
            for item in cart_items
        ])
        
        text = f"""
🛒 <b>Ваша корзина</b>

{items_text}

<b>Итого:</b> {format_price(total)}
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_cart_keyboard(cart_items, total)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cart_increase_"))
async def cart_increase_callback(callback: CallbackQuery):
    """Increase cart item quantity"""
    cart_item_id = int(callback.data.split("_")[2])
    
    with get_db() as db:
        cart_item = db.query(crud.CartItem).filter(crud.CartItem.id == cart_item_id).first()
        if cart_item and cart_item.product.stock > cart_item.quantity:
            crud.update_cart_item(db, cart_item_id, cart_item.quantity + 1)
            await callback.answer("✅ Количество увеличено")
        else:
            await callback.answer("❌ Недостаточно товара на складе", show_alert=True)
    
    # Refresh cart
    await cart_callback(callback)


@router.callback_query(F.data.startswith("cart_decrease_"))
async def cart_decrease_callback(callback: CallbackQuery):
    """Decrease cart item quantity"""
    cart_item_id = int(callback.data.split("_")[2])
    
    with get_db() as db:
        cart_item = db.query(crud.CartItem).filter(crud.CartItem.id == cart_item_id).first()
        if cart_item:
            new_quantity = cart_item.quantity - 1
            crud.update_cart_item(db, cart_item_id, new_quantity)
            await callback.answer("✅ Количество уменьшено" if new_quantity > 0 else "✅ Товар удален")
    
    # Refresh cart
    await cart_callback(callback)


@router.callback_query(F.data.startswith("cart_remove_"))
async def cart_remove_callback(callback: CallbackQuery):
    """Remove item from cart"""
    cart_item_id = int(callback.data.split("_")[2])
    
    with get_db() as db:
        crud.update_cart_item(db, cart_item_id, 0)
        await callback.answer("✅ Товар удален из корзины")
    
    # Refresh cart
    await cart_callback(callback)


@router.callback_query(F.data == "clear_cart")
async def clear_cart_callback(callback: CallbackQuery):
    """Clear cart callback"""
    with get_db() as db:
        user = crud.get_user_by_telegram_id(db, callback.from_user.id)
        crud.clear_cart(db, user.id)
        
        await callback.message.edit_text(
            "✅ Корзина очищена",
            reply_markup=get_back_button("main_menu")
        )
    await callback.answer()


@router.callback_query(F.data == "checkout")
@error_handler
async def checkout_callback(callback: CallbackQuery, state: FSMContext):
    """Checkout callback"""
    # Check subscription before checkout
    subscribed = await check_subscription(callback.bot, callback.from_user.id)
    if not subscribed:
        await callback.message.edit_text(
            "❌ Для оформления заказа необходимо подписаться на наш канал:",
            reply_markup=get_subscription_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📱 <b>Оформление заказа</b>\n\nВведите ваш номер телефона для связи:"
    )
    await state.set_state(CheckoutStates.waiting_for_phone)
    await callback.answer()


@router.message(CheckoutStates.waiting_for_phone)
@error_handler
async def process_phone(message: Message, state: FSMContext):
    """Process phone number"""
    try:
        phone = validate_phone(message.text)
        await state.update_data(phone=phone)
        await message.answer("📍 Введите адрес доставки:")
        await state.set_state(CheckoutStates.waiting_for_address)
    except ValidationError as e:
        await message.answer(f"❌ {str(e)}\n\nПопробуйте еще раз:")


@router.message(CheckoutStates.waiting_for_address)
@error_handler
async def process_address(message: Message, state: FSMContext):
    """Process delivery address"""
    address = sanitize_text(message.text, max_length=500)
    if len(address) < 10:
        await message.answer("❌ Адрес слишком короткий. Введите полный адрес доставки:")
        return
    
    await state.update_data(address=address)
    await message.answer(
        "💬 Введите комментарий к заказу (или отправьте '-' чтобы пропустить):"
    )
    await state.set_state(CheckoutStates.waiting_for_comment)


@router.message(CheckoutStates.waiting_for_comment)
@error_handler
async def process_comment(message: Message, state: FSMContext):
    """Process comment and create order"""
    data = await state.get_data()
    comment = None if message.text == '-' else sanitize_text(message.text, max_length=500)
    
    with get_db() as db:
        user = crud.get_user_by_telegram_id(db, message.from_user.id)
        cart_items = crud.get_cart_items(db, user.id)
        
        if not cart_items:
            await message.answer(
                "❌ Ваша корзина пуста!",
                reply_markup=get_back_button("main_menu")
            )
            await state.clear()
            return
        
        # Create order
        order = crud.create_order(
            db,
            user_id=user.id,
            cart_items=cart_items,
            phone=data['phone'],
            delivery_address=data['address'],
            comment=comment
        )
        
        # Clear cart
        crud.clear_cart(db, user.id)
        
        order_text = format_order_details(order)
        
        from utils.keyboards import get_checkout_keyboard
        await message.answer(
            f"✅ Заказ успешно создан!\n\n{order_text}",
            reply_markup=get_checkout_keyboard(order.id)
        )
    
    await state.clear()


@router.callback_query(F.data == "my_orders")
async def my_orders_callback(callback: CallbackQuery):
    """My orders callback"""
    with get_db() as db:
        user = crud.get_user_by_telegram_id(db, callback.from_user.id)
        orders = crud.get_orders(db, user_id=user.id, limit=10)
        
        if not orders:
            await callback.message.edit_text(
                "📦 У вас пока нет заказов",
                reply_markup=get_back_button("main_menu")
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            "📦 <b>Ваши заказы</b>\n\nВыберите заказ для просмотра:",
            reply_markup=get_orders_keyboard(orders)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("order_"))
async def order_detail_callback(callback: CallbackQuery):
    """Order detail callback"""
    order_id = int(callback.data.split("_")[1])
    
    with get_db() as db:
        order = crud.get_order(db, order_id)
        if not order:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        text = format_order_details(order)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_order_detail_keyboard(order)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_callback(callback: CallbackQuery):
    """Cancel order callback"""
    order_id = int(callback.data.split("_")[2])
    
    with get_db() as db:
        order = crud.update_order_status(db, order_id, 'cancelled')
        
        if order:
            await callback.answer("✅ Заказ отменен")
            await callback.message.edit_text(
                f"❌ Заказ {order.order_number} отменен",
                reply_markup=get_back_button("my_orders")
            )
        else:
            await callback.answer("❌ Ошибка отмены заказа", show_alert=True)


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """No operation callback"""
    await callback.answer()
