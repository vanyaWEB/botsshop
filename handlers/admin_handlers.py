from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import io

from database.db import get_db
from database import crud
from utils.keyboards import (
    get_admin_main_keyboard,
    get_admin_categories_keyboard,
    get_admin_products_keyboard,
    get_admin_users_keyboard,
    get_admin_orders_keyboard,
    get_admin_stats_keyboard,
    get_back_to_admin_keyboard,
    get_confirm_keyboard,
    get_admin_product_actions_keyboard,
    get_admin_category_actions_keyboard,
    get_admin_user_actions_keyboard,
    get_admin_order_actions_keyboard
)
from utils.helpers import is_admin, format_price, get_user_theme
from config import ADMIN_IDS
from utils.error_handler import error_handler, ValidationError, validate_price, validate_stock, sanitize_text

router = Router()


class AdminStates(StatesGroup):
    # Category states
    waiting_category_name = State()
    waiting_category_edit_name = State()
    
    # Product states
    waiting_product_category = State()
    waiting_product_name = State()
    waiting_product_description = State()
    waiting_product_price = State()
    waiting_product_sizes = State()
    waiting_product_stock = State()
    waiting_product_photos = State()
    
    # Edit product states
    editing_product_name = State()
    editing_product_description = State()
    editing_product_price = State()
    editing_product_sizes = State()
    editing_product_stock = State()
    editing_product_photos = State()
    
    # User management
    waiting_user_search = State()
    editing_user_balance = State()
    
    # Order management
    waiting_order_search = State()
    
    # Broadcast
    waiting_broadcast_message = State()


@router.message(Command("admin"))
@error_handler
async def admin_panel(message: Message, state: FSMContext):
    """Admin panel entry point"""
    with get_db() as db:
        if not is_admin(message.from_user.id):
            await message.answer("У вас нет доступа к админ-панели.")
            return
        
        await state.clear()
        
        # Get statistics
        total_users = crud.get_total_users(db)
        total_orders = crud.get_total_orders(db)
        total_revenue = crud.get_total_revenue(db)
        pending_orders = crud.get_pending_orders_count(db)
        
        theme = get_user_theme(db, message.from_user.id)
        
        text = f"""
<b>🎛 Панель администратора</b>

📊 <b>Статистика:</b>
👥 Пользователей: {total_users}
📦 Заказов: {total_orders}
💰 Выручка: {format_price(total_revenue)}
⏳ Ожидают обработки: {pending_orders}

Выберите действие:
"""
        
        await message.answer(
            text,
            reply_markup=get_admin_main_keyboard(theme)
        )


# ============= CATEGORIES MANAGEMENT =============

@router.callback_query(F.data == "admin_categories")
@error_handler
async def admin_categories(callback: CallbackQuery, state: FSMContext):
    """Show categories management"""
    with get_db() as db:
        if not is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        
        categories = crud.get_all_categories(db)
        theme = get_user_theme(db, callback.from_user.id)
        
        text = "<b>📂 Управление категориями</b>\n\n"
        
        if categories:
            text += "Доступные категории:\n"
            for cat in categories:
                product_count = len(cat.products)
                text += f"• {cat.name} ({product_count} товаров)\n"
        else:
            text += "Категории отсутствуют."
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_categories_keyboard(categories, theme)
        )
        await callback.answer()


@router.callback_query(F.data == "admin_add_category")
async def admin_add_category(callback: CallbackQuery, state: FSMContext):
    """Start adding new category"""
    with get_db() as db:
        theme = get_user_theme(db, callback.from_user.id)
        
        await callback.message.edit_text(
            "<b>➕ Добавление категории</b>\n\nВведите название новой категории:",
            reply_markup=get_back_to_admin_keyboard(theme)
        )
        await state.set_state(AdminStates.waiting_category_name)
        await callback.answer()


@router.message(AdminStates.waiting_category_name)
@error_handler
async def process_category_name(message: Message, state: FSMContext):
    """Process new category name"""
    category_name = sanitize_text(message.text, max_length=100)
    
    if len(category_name) < 2:
        await message.answer("❌ Название слишком короткое. Введите минимум 2 символа:")
        return
    
    with get_db() as db:
        # Check if category exists
        existing = crud.get_category_by_name(db, category_name)
        if existing:
            await message.answer("❌ Категория с таким названием уже существует. Введите другое название:")
            return
        
        # Create category
        crud.create_category(db, category_name)
        
        theme = get_user_theme(db, callback.from_user.id)
        categories = crud.get_all_categories(db)
        
        await message.answer(
            f"✅ Категория <b>{category_name}</b> успешно создана!",
            reply_markup=get_admin_categories_keyboard(categories, theme)
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin_edit_cat_"))
async def admin_edit_category(callback: CallbackQuery, state: FSMContext):
    """Edit category"""
    with get_db() as db:
        category_id = int(callback.data.split("_")[-1])
        
        category = crud.get_category(db, category_id)
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        
        theme = get_user_theme(db, callback.from_user.id)
        
        await callback.message.edit_text(
            f"<b>✏️ Редактирование категории</b>\n\nТекущее название: <b>{category.name}</b>\n\nВведите новое название:",
            reply_markup=get_back_to_admin_keyboard(theme)
        )
        await state.set_state(AdminStates.waiting_category_edit_name)
        await state.update_data(category_id=category_id)
        await callback.answer()


@router.message(AdminStates.waiting_category_edit_name)
@error_handler
async def process_category_edit_name(message: Message, state: FSMContext):
    """Process edited category name"""
    category_name = sanitize_text(message.text, max_length=100)
    
    if len(category_name) < 2:
        await message.answer("❌ Название слишком короткое. Введите минимум 2 символа:")
        return
    
    with get_db() as db:
        data = await state.get_data()
        category_id = data.get("category_id")
        
        new_name = category_name
        
        # Check if name is taken
        existing = crud.get_category_by_name(db, new_name)
        if existing and existing.id != category_id:
            await message.answer("❌ Категория с таким названием уже существует. Введите другое название:")
            return
        
        # Update category
        crud.update_category(db, category_id, new_name)
        
        theme = get_user_theme(db, callback.from_user.id)
        categories = crud.get_all_categories(db)
        
        await message.answer(
            f"✅ Категория успешно переименована в <b>{new_name}</b>!",
            reply_markup=get_admin_categories_keyboard(categories, theme)
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin_del_cat_"))
async def admin_delete_category(callback: CallbackQuery):
    """Delete category"""
    with get_db() as db:
        category_id = int(callback.data.split("_")[-1])
        
        category = crud.get_category(db, category_id)
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        
        # Check if category has products
        if category.products:
            await callback.answer(
                f"❌ Невозможно удалить категорию с товарами ({len(category.products)} шт). Сначала удалите товары.",
                show_alert=True
            )
            return
        
        crud.delete_category(db, category_id)
        
        theme = get_user_theme(db, callback.from_user.id)
        categories = crud.get_all_categories(db)
        
        await callback.message.edit_text(
            f"✅ Категория <b>{category.name}</b> удалена!",
            reply_markup=get_admin_categories_keyboard(categories, theme)
        )
        await callback.answer()


# ============= PRODUCTS MANAGEMENT =============

@router.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery):
    """Show products management"""
    with get_db() as db:
        if not is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        
        categories = crud.get_all_categories(db)
        theme = get_user_theme(db, callback.from_user.id)
        
        if not categories:
            await callback.message.edit_text(
                "<b>📦 Управление товарами</b>\n\n❌ Сначала создайте категории!",
                reply_markup=get_back_to_admin_keyboard(theme)
            )
            await callback.answer()
            return
        
        text = "<b>📦 Управление товарами</b>\n\nВыберите категорию:"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_products_keyboard(categories, theme)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_prod_cat_"))
async def admin_products_category(callback: CallbackQuery):
    """Show products in category"""
    with get_db() as db:
        category_id = int(callback.data.split("_")[-1])
        
        category = crud.get_category(db, category_id)
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        
        products = category.products
        theme = get_user_theme(db, callback.from_user.id)
        
        text = f"<b>📦 Товары в категории: {category.name}</b>\n\n"
        
        if products:
            for prod in products:
                text += f"• {prod.name} - {format_price(prod.price)}\n"
                text += f"  Остаток: {prod.stock} шт\n\n"
        else:
            text += "Товары отсутствуют."
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for prod in products:
            buttons.append([InlineKeyboardButton(
                text=f"✏️ {prod.name}",
                callback_data=f"admin_edit_prod_{prod.id}"
            )])
        
        buttons.append([InlineKeyboardButton(
            text="➕ Добавить товар",
            callback_data=f"admin_add_prod_{category_id}"
        )])
        buttons.append([InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="admin_products"
        )])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_add_prod_"))
async def admin_add_product(callback: CallbackQuery, state: FSMContext):
    """Start adding new product"""
    with get_db() as db:
        category_id = int(callback.data.split("_")[-1])
        
        category = crud.get_category(db, category_id)
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return
        
        theme = get_user_theme(db, callback.from_user.id)
        
        await callback.message.edit_text(
            f"<b>➕ Добавление товара в категорию: {category.name}</b>\n\nВведите название товара:",
            reply_markup=get_back_to_admin_keyboard(theme)
        )
        await state.set_state(AdminStates.waiting_product_name)
        await state.update_data(category_id=category_id)
        await callback.answer()


@router.message(AdminStates.waiting_product_name)
async def process_product_name(message: Message, state: FSMContext):
    """Process product name"""
    await state.update_data(product_name=message.text.strip())
    await message.answer("<b>📝 Описание товара</b>\n\nВведите описание товара:")
    await state.set_state(AdminStates.waiting_product_description)


@router.message(AdminStates.waiting_product_description)
async def process_product_description(message: Message, state: FSMContext):
    """Process product description"""
    await state.update_data(product_description=message.text.strip())
    await message.answer("<b>💰 Цена товара</b>\n\nВведите цену товара (в рублях, только число):")
    await state.set_state(AdminStates.waiting_product_price)


@router.message(AdminStates.waiting_product_price)
@error_handler
async def process_product_price(message: Message, state: FSMContext):
    """Process product price"""
    try:
        price = validate_price(message.text)
        await state.update_data(product_price=price)
        await message.answer(
            "<b>📏 Размеры товара</b>\n\nВведите доступные размеры через запятую (например: S, M, L, XL):"
        )
        await state.set_state(AdminStates.waiting_product_sizes)
    except ValidationError as e:
        await message.answer(f"❌ {str(e)}\n\nПопробуйте еще раз:")


@router.message(AdminStates.waiting_product_sizes)
async def process_product_sizes(message: Message, state: FSMContext):
    """Process product sizes"""
    sizes = [s.strip() for s in message.text.split(",")]
    await state.update_data(product_sizes=",".join(sizes))
    await message.answer("<b>📦 Количество на складе</b>\n\nВведите количество товара на складе:")
    await state.set_state(AdminStates.waiting_product_stock)


@router.message(AdminStates.waiting_product_stock)
@error_handler
async def process_product_stock(message: Message, state: FSMContext):
    """Process product stock"""
    try:
        stock = validate_stock(message.text)
        await state.update_data(product_stock=stock)
        await message.answer(
            "<b>📸 Фотографии товара</b>\n\nОтправьте фотографии товара (можно несколько). После отправки всех фото нажмите /done"
        )
        await state.update_data(product_photos=[])
        await state.set_state(AdminStates.waiting_product_photos)
    except ValidationError as e:
        await message.answer(f"❌ {str(e)}\n\nПопробуйте еще раз:")


@router.message(AdminStates.waiting_product_photos, F.photo)
async def process_product_photo(message: Message, state: FSMContext):
    """Process product photos"""
    data = await state.get_data()
    photos = data.get("product_photos", [])
    
    # Get the largest photo
    photo = message.photo[-1]
    photos.append(photo.file_id)
    
    await state.update_data(product_photos=photos)
    await message.answer(f"✅ Фото {len(photos)} добавлено. Отправьте еще или нажмите /done для завершения.")


@router.message(AdminStates.waiting_product_photos, Command("done"))
async def finish_product_creation(message: Message, state: FSMContext):
    """Finish product creation"""
    with get_db() as db:
        data = await state.get_data()
        
        photos = data.get("product_photos", [])
        if not photos:
            await message.answer("❌ Добавьте хотя бы одну фотографию товара!")
            return
        
        # Create product
        product = crud.create_product(
            db=db,
            name=data["product_name"],
            description=data["product_description"],
            price=data["product_price"],
            category_id=data["category_id"],
            sizes=data["product_sizes"],
            stock=data["product_stock"],
            photos=",".join(photos)
        )
        
        theme = get_user_theme(db, message.from_user.id)
        
        await message.answer(
            f"✅ Товар <b>{product.name}</b> успешно создан!",
            reply_markup=get_back_to_admin_keyboard(theme)
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin_edit_prod_"))
async def admin_edit_product(callback: CallbackQuery):
    """Show product edit menu"""
    with get_db() as db:
        product_id = int(callback.data.split("_")[-1])
        
        product = crud.get_product(db, product_id)
        if not product:
            await callback.answer("Товар не найден", show_alert=True)
            return
        
        theme = get_user_theme(db, callback.from_user.id)
        
        photo_count = len(product.photos.split(',')) if product.photos else 0
        
        text = f"""
<b>✏️ Редактирование товара</b>

<b>Название:</b> {product.name}
<b>Описание:</b> {product.description}
<b>Цена:</b> {format_price(product.price)}
<b>Размеры:</b> {product.sizes}
<b>Остаток:</b> {product.stock} шт
<b>Фотографий:</b> {photo_count}

Выберите что изменить:
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_product_actions_keyboard(product_id, theme)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_del_prod_"))
async def admin_delete_product(callback: CallbackQuery):
    """Delete product"""
    with get_db() as db:
        product_id = int(callback.data.split("_")[-1])
        
        product = crud.get_product(db, product_id)
        if not product:
            await callback.answer("Товар не найден", show_alert=True)
            return
        
        category_id = product.category_id
        product_name = product.name
        
        crud.delete_product(db, product_id)
        
        await callback.answer(f"✅ Товар {product_name} удален!", show_alert=True)
        
        # Return to category products list
        await admin_products_category(callback)


# ============= USERS MANAGEMENT =============

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Show users management"""
    with get_db() as db:
        if not is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        
        users = crud.get_all_users(db, limit=20)
        theme = get_user_theme(db, callback.from_user.id)
        
        text = "<b>👥 Управление пользователями</b>\n\n"
        text += f"Всего пользователей: {crud.get_total_users(db)}\n\n"
        text += "Последние 20 пользователей:\n\n"
        
        for user in users:
            status = "🟢" if user.is_active else "🔴"
            text += f"{status} {user.username or user.telegram_id}\n"
            text += f"   ID: {user.telegram_id}\n"
            text += f"   Заказов: {len(user.orders)}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_users_keyboard(users, theme)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_details(callback: CallbackQuery):
    """Show user details"""
    with get_db() as db:
        user_id = int(callback.data.split("_")[-1])
        
        user = crud.get_user(db, user_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        theme = get_user_theme(db, callback.from_user.id)
        
        total_spent = sum(order.total_amount for order in user.orders if order.status == "completed")
        
        text = f"""
<b>👤 Информация о пользователе</b>

<b>ID:</b> {user.telegram_id}
<b>Username:</b> @{user.username or 'не указан'}
<b>Имя:</b> {user.first_name or 'не указано'}
<b>Статус:</b> {'🟢 Активен' if user.is_active else '🔴 Заблокирован'}
<b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}

<b>📊 Статистика:</b>
• Заказов: {len(user.orders)}
• Потрачено: {format_price(total_spent)}

Выберите действие:
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_user_actions_keyboard(user_id, user.is_active, theme)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_block_user_"))
async def admin_block_user(callback: CallbackQuery):
    """Block/unblock user"""
    with get_db() as db:
        user_id = int(callback.data.split("_")[-1])
        
        user = crud.get_user(db, user_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Toggle active status
        crud.update_user_status(db, user_id, not user.is_active)
        
        status_text = "разблокирован" if not user.is_active else "заблокирован"
        await callback.answer(f"✅ Пользователь {status_text}!", show_alert=True)
        
        # Refresh user details
        await admin_user_details(callback)


# ============= ORDERS MANAGEMENT =============

@router.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    """Show orders management"""
    with get_db() as db:
        if not is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        
        orders = crud.get_recent_orders(db, limit=15)
        theme = get_user_theme(db, callback.from_user.id)
        
        text = "<b>📦 Управление заказами</b>\n\n"
        text += f"Всего заказов: {crud.get_total_orders(db)}\n"
        text += f"Ожидают обработки: {crud.get_pending_orders_count(db)}\n\n"
        text += "Последние 15 заказов:\n\n"
        
        for order in orders:
            status_emoji = {
                "pending": "⏳",
                "processing": "🔄",
                "completed": "✅",
                "cancelled": "❌"
            }.get(order.status, "❓")
            
            text += f"{status_emoji} Заказ #{order.id}\n"
            text += f"   {format_price(order.total_amount)} • {order.created_at.strftime('%d.%m %H:%M')}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_orders_keyboard(orders, theme)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_order_"))
async def admin_order_details(callback: CallbackQuery):
    """Show order details"""
    with get_db() as db:
        order_id = int(callback.data.split("_")[-1])
        
        order = crud.get_order(db, order_id)
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        theme = get_user_theme(db, callback.from_user.id)
        
        status_text = {
            "pending": "⏳ Ожидает оплаты",
            "processing": "🔄 В обработке",
            "completed": "✅ Завершен",
            "cancelled": "❌ Отменен"
        }.get(order.status, "❓ Неизвестно")
        
        text = f"""
<b>📦 Заказ #{order.id}</b>

<b>Статус:</b> {status_text}
<b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}
<b>Сумма:</b> {format_price(order.total_amount)}

<b>👤 Покупатель:</b>
ID: {order.user.telegram_id}
Username: @{order.user.username or 'не указан'}

<b>📋 Товары:</b>
"""
        
        for item in order.items:
            text += f"• {item.product.name}\n"
            text += f"  {item.quantity} шт × {format_price(item.price)} = {format_price(item.quantity * item.price)}\n"
        
        if order.delivery_address:
            text += f"\n<b>📍 Адрес доставки:</b>\n{order.delivery_address}"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_order_actions_keyboard(order_id, order.status, theme)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_order_status_"))
async def admin_change_order_status(callback: CallbackQuery):
    """Change order status"""
    with get_db() as db:
        parts = callback.data.split("_")
        order_id = int(parts[-2])
        new_status = parts[-1]
        
        order = crud.get_order(db, order_id)
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        crud.update_order_status(db, order_id, new_status)
        
        status_text = {
            "processing": "в обработку",
            "completed": "завершен",
            "cancelled": "отменен"
        }.get(new_status, new_status)
        
        await callback.answer(f"✅ Заказ переведен в статус: {status_text}!", show_alert=True)
        
        # Refresh order details
        await admin_order_details(callback)


# ============= STATISTICS =============

@router.callback_query(F.data == "admin_stats")
async def admin_statistics(callback: CallbackQuery):
    """Show detailed statistics"""
    with get_db() as db:
        if not is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return
        
        theme = get_user_theme(db, callback.from_user.id)
        
        # Get statistics
        total_users = crud.get_total_users(db)
        total_orders = crud.get_total_orders(db)
        total_revenue = crud.get_total_revenue(db)
        pending_orders = crud.get_pending_orders_count(db)
        
        # Today's stats
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_orders = crud.get_orders_by_date_range(db, today_start, datetime.now())
        today_revenue = sum(o.total_amount for o in today_orders if o.status == "completed")
        
        # Week stats
        week_start = datetime.now() - timedelta(days=7)
        week_orders = crud.get_orders_by_date_range(db, week_start, datetime.now())
        week_revenue = sum(o.total_amount for o in week_orders if o.status == "completed")
        
        # Month stats
        month_start = datetime.now() - timedelta(days=30)
        month_orders = crud.get_orders_by_date_range(db, month_start, datetime.now())
        month_revenue = sum(o.total_amount for o in month_orders if o.status == "completed")
        
        # Top products
        top_products = crud.get_top_products(db, limit=5)
        
        text = f"""
<b>📊 Детальная статистика</b>

<b>👥 Пользователи:</b>
Всего: {total_users}

<b>📦 Заказы:</b>
Всего: {total_orders}
Ожидают: {pending_orders}

<b>💰 Выручка:</b>
Всего: {format_price(total_revenue)}
За сегодня: {format_price(today_revenue)} ({len(today_orders)} заказов)
За неделю: {format_price(week_revenue)} ({len(week_orders)} заказов)
За месяц: {format_price(month_revenue)} ({len(month_orders)} заказов)

<b>🔥 Топ-5 товаров:</b>
"""
        
        for i, (product, count) in enumerate(top_products, 1):
            text += f"{i}. {product.name} - {count} продаж\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_stats_keyboard(theme)
        )
        await callback.answer()


# ============= BROADCAST =============

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast message"""
    with get_db() as db:
        theme = get_user_theme(db, callback.from_user.id)
        
        await callback.message.edit_text(
            "<b>📢 Рассылка сообщений</b>\n\nВведите текст сообщения для рассылки всем пользователям:",
            reply_markup=get_back_to_admin_keyboard(theme)
        )
        await state.set_state(AdminStates.waiting_broadcast_message)
        await callback.answer()


@router.message(AdminStates.waiting_broadcast_message)
@error_handler
async def process_broadcast(message: Message, state: FSMContext):
    """Process and send broadcast"""
    broadcast_text = sanitize_text(message.text, max_length=4000)
    
    if len(broadcast_text) < 5:
        await message.answer("❌ Сообщение слишком короткое. Введите минимум 5 символов:")
        return
    
    with get_db() as db:
        users = crud.get_all_users(db)
        
        sent = 0
        failed = 0
        blocked = 0
        
        status_msg = await message.answer(f"📤 Отправка... 0/{len(users)}")
        
        for i, user in enumerate(users, 1):
            try:
                await message.bot.send_message(user.telegram_id, broadcast_text)
                sent += 1
            except Exception as e:
                if "blocked" in str(e).lower():
                    blocked += 1
                failed += 1
            
            if i % 5 == 0:
                try:
                    await status_msg.edit_text(f"📤 Отправка... {i}/{len(users)}")
                except:
                    pass
        
        theme = get_user_theme(db, message.from_user.id)
        
        await status_msg.edit_text(
            f"✅ Рассылка завершена!\n\n"
            f"Отправлено: {sent}\n"
            f"Заблокировали бота: {blocked}\n"
            f"Не доставлено: {failed - blocked}",
            reply_markup=get_back_to_admin_keyboard(theme)
        )
        await state.clear()


# ============= NAVIGATION =============

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    """Return to admin main menu"""
    await state.clear()
    
    # Create a fake message to reuse admin_panel function
    fake_message = callback.message
    fake_message.from_user = callback.from_user
    fake_message.answer = callback.message.edit_text
    
    await admin_panel(fake_message, state)
    await callback.answer()
