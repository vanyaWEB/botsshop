from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from database.models import Category, Product, Order
import config
import json


def get_main_menu_keyboard(is_admin: bool = False, theme: str = 'light') -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    colors = config.THEMES[theme]
    
    builder.row(
        InlineKeyboardButton(text="🛍 Каталог", web_app=WebAppInfo(url=f"{config.WEBAPP_URL}/catalog")),
    )
    builder.row(
        InlineKeyboardButton(text="🛒 Корзина", callback_data="cart"),
        InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ О магазине", callback_data="about"),
        InlineKeyboardButton(text="🎨 Тема", callback_data="toggle_theme")
    )
    
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")
        )
    
    return builder.as_markup()


def get_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Back button"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data))
    return builder.as_markup()


def get_categories_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    """Categories keyboard"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        icon = category.icon or "📁"
        builder.row(
            InlineKeyboardButton(
                text=f"{icon} {category.name}",
                callback_data=f"category_{category.id}"
            )
        )
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def get_products_keyboard(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    """Products keyboard"""
    builder = InlineKeyboardBuilder()
    
    for product in products:
        builder.row(
            InlineKeyboardButton(
                text=f"{product.name} - {product.price}₽",
                callback_data=f"product_{product.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ К категориям", callback_data="catalog")
    )
    return builder.as_markup()


def get_product_keyboard(product: Product, in_cart: bool = False) -> InlineKeyboardMarkup:
    """Product detail keyboard"""
    builder = InlineKeyboardBuilder()
    
    if product.stock > 0:
        if product.sizes:
            sizes = json.loads(product.sizes)
            for size in sizes:
                builder.add(
                    InlineKeyboardButton(
                        text=f"Размер {size}",
                        callback_data=f"add_to_cart_{product.id}_{size}"
                    )
                )
            builder.adjust(3)
        else:
            builder.row(
                InlineKeyboardButton(
                    text="➕ Добавить в корзину",
                    callback_data=f"add_to_cart_{product.id}_none"
                )
            )
    else:
        builder.row(
            InlineKeyboardButton(text="❌ Нет в наличии", callback_data="noop")
        )
    
    if product.size_chart:
        builder.row(
            InlineKeyboardButton(text="📏 Размерная сетка", callback_data=f"size_chart_{product.id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=f"category_{product.category_id}")
    )
    
    return builder.as_markup()


def get_cart_keyboard(cart_items: List, total: float) -> InlineKeyboardMarkup:
    """Cart keyboard"""
    builder = InlineKeyboardBuilder()
    
    if cart_items:
        for item in cart_items:
            size_text = f" ({item.size})" if item.size else ""
            builder.row(
                InlineKeyboardButton(
                    text=f"➖",
                    callback_data=f"cart_decrease_{item.id}"
                ),
                InlineKeyboardButton(
                    text=f"{item.product.name}{size_text} x{item.quantity}",
                    callback_data="noop"
                ),
                InlineKeyboardButton(
                    text=f"➕",
                    callback_data=f"cart_increase_{item.id}"
                ),
                InlineKeyboardButton(
                    text=f"🗑",
                    callback_data=f"cart_remove_{item.id}"
                )
            )
        
        builder.row(
            InlineKeyboardButton(text=f"✅ Оформить заказ ({total}₽)", callback_data="checkout")
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_checkout_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Checkout keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_order_{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{order_id}")
    )
    
    return builder.as_markup()


def get_orders_keyboard(orders: List[Order]) -> InlineKeyboardMarkup:
    """Orders list keyboard"""
    builder = InlineKeyboardBuilder()
    
    for order in orders:
        status_emoji = {
            'pending': '⏳',
            'paid': '✅',
            'processing': '📦',
            'shipped': '🚚',
            'delivered': '✅',
            'cancelled': '❌'
        }.get(order.status, '❓')
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {order.order_number} - {order.total_amount}₽",
                callback_data=f"order_{order.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_order_detail_keyboard(order: Order) -> InlineKeyboardMarkup:
    """Order detail keyboard"""
    builder = InlineKeyboardBuilder()
    
    if order.status == 'pending' and order.payment_status != 'succeeded':
        builder.row(
            InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_order_{order.id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ К заказам", callback_data="my_orders")
    )
    
    return builder.as_markup()


# Admin keyboards
def get_admin_panel_keyboard(theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin panel main menu with modern design"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")
    )
    builder.row(
        InlineKeyboardButton(text="📂 Категории", callback_data="admin_categories"),
        InlineKeyboardButton(text="🛍 Товары", callback_data="admin_products")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()


def get_admin_main_keyboard(theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin panel main menu - alias for get_admin_panel_keyboard"""
    return get_admin_panel_keyboard(theme)


def get_admin_categories_keyboard(categories: List[Category], theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin categories management"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📂 {category.name}",
                callback_data=f"admin_cat_view_{category.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin_add_category")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="back_to_admin")
    )
    
    return builder.as_markup()


def get_admin_category_actions_keyboard(category_id: int, theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin category actions"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"admin_edit_cat_{category_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin_del_cat_{category_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_categories")
    )
    
    return builder.as_markup()


def get_admin_products_keyboard(categories: List[Category], theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin products management - select category"""
    builder = InlineKeyboardBuilder()
    
    for category in categories:
        product_count = len(category.products)
        builder.row(
            InlineKeyboardButton(
                text=f"📂 {category.name} ({product_count})",
                callback_data=f"admin_prod_cat_{category.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="back_to_admin")
    )
    
    return builder.as_markup()


def get_admin_product_actions_keyboard(product_id: int, theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin product actions"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✏️ Название", callback_data=f"admin_edit_prod_name_{product_id}"),
        InlineKeyboardButton(text="📝 Описание", callback_data=f"admin_edit_prod_desc_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Цена", callback_data=f"admin_edit_prod_price_{product_id}"),
        InlineKeyboardButton(text="📏 Размеры", callback_data=f"admin_edit_prod_sizes_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Остаток", callback_data=f"admin_edit_prod_stock_{product_id}"),
        InlineKeyboardButton(text="📸 Фото", callback_data=f"admin_edit_prod_photos_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"admin_del_prod_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_products")
    )
    
    return builder.as_markup()


def get_admin_orders_keyboard(orders: List[Order], theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin orders management"""
    builder = InlineKeyboardBuilder()
    
    for order in orders:
        status_emoji = {
            'pending': '⏳',
            'processing': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }.get(order.status, '❓')
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} #{order.id} • {order.total_amount}₽",
                callback_data=f"admin_order_{order.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="back_to_admin")
    )
    
    return builder.as_markup()


def get_admin_order_actions_keyboard(order_id: int, status: str, theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin order actions"""
    builder = InlineKeyboardBuilder()
    
    if status == 'pending':
        builder.row(
            InlineKeyboardButton(text="🔄 В обработку", callback_data=f"admin_order_status_{order_id}_processing")
        )
    elif status == 'processing':
        builder.row(
            InlineKeyboardButton(text="✅ Завершить", callback_data=f"admin_order_status_{order_id}_completed")
        )
    
    if status != 'cancelled':
        builder.row(
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_order_status_{order_id}_cancelled")
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_orders")
    )
    
    return builder.as_markup()


def get_admin_users_keyboard(users: List, theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin users management"""
    builder = InlineKeyboardBuilder()
    
    for user in users:
        status = "🟢" if user.is_active else "🔴"
        name = user.username or f"ID{user.telegram_id}"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} @{name}",
                callback_data=f"admin_user_{user.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="back_to_admin")
    )
    
    return builder.as_markup()


def get_admin_user_actions_keyboard(user_id: int, is_active: bool, theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin user actions"""
    builder = InlineKeyboardBuilder()
    
    block_text = "🟢 Разблокировать" if not is_active else "🔴 Заблокировать"
    builder.row(
        InlineKeyboardButton(text=block_text, callback_data=f"admin_block_user_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")
    )
    
    return builder.as_markup()


def get_admin_stats_keyboard(theme: str = 'light') -> InlineKeyboardMarkup:
    """Admin statistics keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="back_to_admin")
    )
    
    return builder.as_markup()


def get_back_to_admin_keyboard(theme: str = 'light') -> InlineKeyboardMarkup:
    """Back to admin panel button"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Админ-панель", callback_data="back_to_admin")
    )
    return builder.as_markup()


def get_confirm_keyboard(action: str, item_id: int, theme: str = 'light') -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}")
    )
    
    return builder.as_markup()


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Subscription check keyboard"""
    builder = InlineKeyboardBuilder()
    
    if config.REQUIRED_CHANNEL_URL:
        builder.row(
            InlineKeyboardButton(text="📢 Подписаться", url=config.REQUIRED_CHANNEL_URL)
        )
    builder.row(
        InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")
    )
    
    return builder.as_markup()
