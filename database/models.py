from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    theme = Column(String(10), default='light')
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)
    
    orders = relationship('Order', back_populates='user', cascade='all, delete-orphan')
    cart_items = relationship('CartItem', back_populates='user', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_user_active_created', 'is_active', 'created_at'),
        Index('idx_user_telegram_active', 'telegram_id', 'is_active'),
    )


class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    icon = Column(String(50))
    position = Column(Integer, default=0, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship('Product', back_populates='category', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_category_active_position', 'is_active', 'position'),
    )


class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    price = Column(Float, nullable=False, index=True)
    photos = Column(Text)
    stock = Column(Integer, default=0, index=True)
    sizes = Column(String(255))
    size_chart = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    category = relationship('Category', back_populates='products')
    cart_items = relationship('CartItem', back_populates='product', cascade='all, delete-orphan')
    order_items = relationship('OrderItem', back_populates='product')
    
    __table_args__ = (
        Index('idx_product_category_active', 'category_id', 'is_active', 'position'),
        Index('idx_product_active_price', 'is_active', 'price'),
        Index('idx_product_active_stock', 'is_active', 'stock'),
    )


class CartItem(Base):
    __tablename__ = 'cart_items'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True)
    quantity = Column(Integer, default=1)
    size = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='cart_items')
    product = relationship('Product', back_populates='cart_items')
    
    __table_args__ = (
        Index('idx_cart_user_product', 'user_id', 'product_id', 'size', unique=True),
    )


class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default='pending', index=True)
    payment_id = Column(String(255), index=True)
    payment_status = Column(String(50), default='pending', index=True)
    delivery_address = Column(Text)
    phone = Column(String(20))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_order_user_created', 'user_id', 'created_at'),
        Index('idx_order_status_created', 'status', 'created_at'),
        Index('idx_order_payment_status', 'payment_status', 'created_at'),
    )


class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='SET NULL'), index=True)
    product_name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    size = Column(String(10))
    
    order = relationship('Order', back_populates='items')
    product = relationship('Product', back_populates='order_items')


class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
