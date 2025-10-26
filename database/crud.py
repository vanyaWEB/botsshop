from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from database.models import User, Category, Product, CartItem, Order, OrderItem, Settings
from datetime import datetime, timedelta
from typing import List, Optional
import json
from utils.error_handler import db_error_handler
import logging

logger = logging.getLogger(__name__)


def transactional(func):
    """Decorator to ensure database operations are atomic"""
    def wrapper(db: Session, *args, **kwargs):
        try:
            result = func(db, *args, **kwargs)
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"Transaction failed in {func.__name__}: {e}")
            raise
    return wrapper


# User CRUD
@db_error_handler
@transactional
def get_or_create_user(db: Session, telegram_id: int, username: str = None, 
                       first_name: str = None, last_name: str = None) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        db.add(user)
        db.flush()
    else:
        user.last_activity = datetime.utcnow()
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
    return user


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def update_user_theme(db: Session, telegram_id: int, theme: str):
    user = get_user_by_telegram_id(db, telegram_id)
    if user:
        user.theme = theme
        db.commit()


def block_user(db: Session, user_id: int, blocked: bool = True):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_blocked = blocked
        db.commit()


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_total_users(db: Session) -> int:
    return db.query(func.count(User.id)).scalar()


def update_user_status(db: Session, user_id: int, is_active: bool):
    user = get_user(db, user_id)
    if user:
        user.is_active = is_active
        db.commit()
        db.refresh(user)
    return user


# Category CRUD
@db_error_handler
def create_category(db: Session, name: str, description: str = None, icon: str = None) -> Category:
    max_position = db.query(func.max(Category.position)).scalar() or 0
    category = Category(
        name=name,
        description=description,
        icon=icon,
        position=max_position + 1
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_categories(db: Session, active_only: bool = True) -> List[Category]:
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)
    return query.order_by(Category.position).all()


def get_category(db: Session, category_id: int) -> Optional[Category]:
    return db.query(Category).filter(Category.id == category_id).first()


def update_category(db: Session, category_id: int, **kwargs):
    category = get_category(db, category_id)
    if category:
        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
        db.commit()
        db.refresh(category)
    return category


def delete_category(db: Session, category_id: int):
    category = get_category(db, category_id)
    if category:
        db.delete(category)
        db.commit()
        return True
    return False


def get_category_by_name(db: Session, name: str) -> Optional[Category]:
    return db.query(Category).filter(Category.name == name).first()


def get_all_categories(db: Session) -> List[Category]:
    return db.query(Category).order_by(Category.position).all()


# Product CRUD
@db_error_handler
def create_product(db: Session, category_id: int, name: str, description: str,
                   price: float, stock: int = 0, sizes: str = None,
                   photos: str = None, size_chart: str = None) -> Product:
    """Create new product with photos as comma-separated string"""
    max_position = db.query(func.max(Product.position)).filter(
        Product.category_id == category_id
    ).scalar() or 0
    
    product = Product(
        category_id=category_id,
        name=name,
        description=description,
        price=price,
        stock=stock,
        sizes=sizes,
        photos=photos,
        size_chart=size_chart,
        position=max_position + 1
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_products(db: Session, category_id: int = None, active_only: bool = True) -> List[Product]:
    query = db.query(Product)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if active_only:
        query = query.filter(Product.is_active == True)
    return query.order_by(Product.position).all()


def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()


def update_product(db: Session, product_id: int, **kwargs):
    product = get_product(db, product_id)
    if product:
        for key, value in kwargs.items():
            if hasattr(product, key):
                if key == 'sizes' and isinstance(value, list):
                    setattr(product, key, json.dumps(value))
                else:
                    setattr(product, key, value)
        product.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(product)
    return product


def delete_product(db: Session, product_id: int):
    product = get_product(db, product_id)
    if product:
        db.delete(product)
        db.commit()
        return True
    return False


# Cart CRUD
@transactional
def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int = 1, size: str = None) -> CartItem:
    # Check if item already exists
    cart_item = db.query(CartItem).filter(
        and_(
            CartItem.user_id == user_id,
            CartItem.product_id == product_id,
            CartItem.size == size
        )
    ).first()
    
    if cart_item:
        new_quantity = cart_item.quantity + quantity
        product = db.query(Product).filter(Product.id == product_id).first()
        if new_quantity > product.stock:
            raise ValueError("Insufficient stock")
        cart_item.quantity = new_quantity
    else:
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            size=size
        )
        db.add(cart_item)
    
    db.flush()
    return cart_item


def get_cart_items(db: Session, user_id: int) -> List[CartItem]:
    return db.query(CartItem).filter(CartItem.user_id == user_id).all()


def update_cart_item(db: Session, cart_item_id: int, quantity: int):
    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if cart_item:
        if quantity <= 0:
            db.delete(cart_item)
        else:
            cart_item.quantity = quantity
        db.commit()
        return True
    return False


def clear_cart(db: Session, user_id: int):
    db.query(CartItem).filter(CartItem.user_id == user_id).delete()
    db.commit()


def get_cart_item(db: Session, cart_item_id: int) -> Optional[CartItem]:
    return db.query(CartItem).filter(CartItem.id == cart_item_id).first()


def remove_cart_item(db: Session, cart_item_id: int):
    cart_item = get_cart_item(db, cart_item_id)
    if cart_item:
        db.delete(cart_item)
        db.commit()
        return True
    return False


# Order CRUD
@db_error_handler
@transactional
def create_order(db: Session, user_id: int, cart_items: List[CartItem],
                 phone: str = None, delivery_address: str = None, comment: str = None) -> Order:
    """Create order from cart items with stock validation"""
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).with_for_update().first()
        if not product or product.stock < item.quantity:
            raise ValueError(f"Insufficient stock for {product.name if product else 'product'}")
    
    # Generate order number
    order_count = db.query(func.count(Order.id)).scalar()
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{order_count + 1:04d}"
    
    # Calculate total
    total_amount = sum(item.product.price * item.quantity for item in cart_items)
    
    order = Order(
        user_id=user_id,
        order_number=order_number,
        total_amount=total_amount,
        phone=phone,
        delivery_address=delivery_address,
        comment=comment
    )
    db.add(order)
    db.flush()
    
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            product_name=cart_item.product.name,
            price=cart_item.product.price,
            quantity=cart_item.quantity,
            size=cart_item.size
        )
        db.add(order_item)
        
        # Decrease stock
        product = db.query(Product).filter(Product.id == cart_item.product_id).first()
        product.stock -= cart_item.quantity
    
    return order


def get_orders(db: Session, user_id: int = None, skip: int = 0, limit: int = 100) -> List[Order]:
    query = db.query(Order)
    if user_id:
        query = query.filter(Order.user_id == user_id)
    return query.order_by(desc(Order.created_at)).offset(skip).limit(limit).all()


def get_order(db: Session, order_id: int) -> Optional[Order]:
    return db.query(Order).filter(Order.id == order_id).first()


def get_order_by_number(db: Session, order_number: str) -> Optional[Order]:
    return db.query(Order).filter(Order.order_number == order_number).first()


def update_order_status(db: Session, order_id: int, status: str, payment_id: str = None):
    order = get_order(db, order_id)
    if order:
        order.status = status
        if payment_id:
            order.payment_id = payment_id
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
    return order


def update_order_payment_status(db: Session, order_id: int, payment_status: str):
    order = get_order(db, order_id)
    if order:
        order.payment_status = payment_status
        if payment_status == 'succeeded':
            order.status = 'paid'
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
    return order


def get_recent_orders(db: Session, limit: int = 15) -> List[Order]:
    return db.query(Order).order_by(desc(Order.created_at)).limit(limit).all()


def get_orders_by_date_range(db: Session, start_date: datetime, end_date: datetime) -> List[Order]:
    return db.query(Order).filter(
        and_(
            Order.created_at >= start_date,
            Order.created_at <= end_date
        )
    ).all()


def get_top_products(db: Session, limit: int = 5):
    results = db.query(
        Product,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.status == 'completed'
    ).group_by(Product.id).order_by(desc('total_sold')).limit(limit).all()
    
    return results


def get_total_orders(db: Session) -> int:
    return db.query(func.count(Order.id)).scalar()


def get_total_revenue(db: Session) -> float:
    return db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == 'succeeded'
    ).scalar() or 0


def get_pending_orders_count(db: Session) -> int:
    return db.query(func.count(Order.id)).filter(
        Order.status == 'pending'
    ).scalar()


# Statistics
def get_statistics(db: Session, days: int = 30):
    start_date = datetime.utcnow() - timedelta(days=days)
    
    total_users = db.query(func.count(User.id)).scalar()
    new_users = db.query(func.count(User.id)).filter(User.created_at >= start_date).scalar()
    
    total_orders = db.query(func.count(Order.id)).scalar()
    period_orders = db.query(func.count(Order.id)).filter(Order.created_at >= start_date).scalar()
    
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == 'succeeded'
    ).scalar() or 0
    
    period_revenue = db.query(func.sum(Order.total_amount)).filter(
        and_(
            Order.created_at >= start_date,
            Order.payment_status == 'succeeded'
        )
    ).scalar() or 0
    
    pending_orders = db.query(func.count(Order.id)).filter(
        Order.status == 'pending'
    ).scalar()
    
    return {
        'total_users': total_users,
        'new_users': new_users,
        'total_orders': total_orders,
        'period_orders': period_orders,
        'total_revenue': total_revenue,
        'period_revenue': period_revenue,
        'pending_orders': pending_orders
    }
