from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_db
from database import crud
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from datetime import datetime
import config

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = config.SECRET_KEY

Talisman(app, 
    force_https=False,
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://telegram.org"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https:", "blob:"],
    }
)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/catalog')
def catalog():
    """Catalog page"""
    return render_template('catalog.html')

@app.route('/admin')
def admin_panel():
    """Admin panel page"""
    return render_template('admin.html')

@app.route('/admin/categories')
def admin_categories():
    """Admin categories management page"""
    return render_template('admin_categories.html')

@app.route('/admin/products')
def admin_products():
    """Admin products management page"""
    return render_template('admin_products.html')

@app.route('/api/categories')
@limiter.limit("30 per minute")
def get_categories():
    """Get all categories"""
    try:
        with get_db() as db:
            categories = crud.get_categories(db, active_only=True)
            
            return jsonify([{
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'icon': cat.icon,
                'product_count': len([p for p in cat.products if p.is_active])
            } for cat in categories])
    except Exception as e:
        app.logger.error(f"Error fetching categories: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/products')
@limiter.limit("30 per minute")
def get_products():
    """Get products by category"""
    try:
        category_id = request.args.get('category_id', type=int)
        with get_db() as db:
            products = crud.get_products(db, category_id=category_id, active_only=True)
            
            return jsonify([{
                'id': prod.id,
                'name': prod.name,
                'description': prod.description,
                'price': prod.price,
                'stock': prod.stock,
                'sizes': prod.sizes,
                'photos': prod.photos.split(',') if prod.photos else [],
                'category_id': prod.category_id
            } for prod in products])
    except Exception as e:
        app.logger.error(f"Error fetching products: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/product/<int:product_id>')
@limiter.limit("60 per minute")
def get_product(product_id):
    """Get single product"""
    try:
        with get_db() as db:
            product = crud.get_product(db, product_id)
            
            if not product:
                return jsonify({'error': 'Product not found'}), 404
            
            return jsonify({
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': product.price,
                'stock': product.stock,
                'sizes': product.sizes,
                'size_chart': product.size_chart,
                'photos': product.photos.split(',') if product.photos else [],
                'category_id': product.category_id,
                'category_name': product.category.name
            })
    except Exception as e:
        app.logger.error(f"Error fetching product {product_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/search')
@limiter.limit("20 per minute")
def search_products():
    """Search products"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        query = query[:100]  # Limit length
        
        with get_db() as db:
            from database.models import Product
            products = db.query(Product).filter(
                Product.is_active == True,
                (Product.name.ilike(f'%{query}%') | Product.description.ilike(f'%{query}%'))
            ).limit(20).all()
            
            return jsonify([{
                'id': prod.id,
                'name': prod.name,
                'description': prod.description,
                'price': prod.price,
                'stock': prod.stock,
                'photos': prod.photos.split(',') if prod.photos else [],
                'category_id': prod.category_id,
                'category_name': prod.category.name
            } for prod in products])
    except Exception as e:
        app.logger.error(f"Error searching products: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin/categories', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
def admin_categories_api():
    """Get all categories or create new one"""
    try:
        if request.method == 'GET':
            with get_db() as db:
                categories = crud.get_all_categories(db)
                return jsonify([{
                    'id': cat.id,
                    'name': cat.name,
                    'description': cat.description,
                    'icon': cat.icon,
                    'position': cat.position,
                    'is_active': cat.is_active,
                    'product_count': len(cat.products)
                } for cat in categories])
        
        elif request.method == 'POST':
            data = request.json
            with get_db() as db:
                category = crud.create_category(
                    db,
                    name=data['name'],
                    description=data.get('description'),
                    icon=data.get('icon')
                )
                return jsonify({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'icon': category.icon,
                    'position': category.position,
                    'is_active': category.is_active
                }), 201
    except Exception as e:
        app.logger.error(f"Error in admin categories API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/categories/<int:category_id>', methods=['PUT', 'DELETE'])
@limiter.limit("30 per minute")
def admin_category_detail(category_id):
    """Update or delete category"""
    try:
        with get_db() as db:
            if request.method == 'PUT':
                data = request.json
                category = crud.update_category(db, category_id, **data)
                if not category:
                    return jsonify({'error': 'Category not found'}), 404
                return jsonify({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'icon': category.icon,
                    'position': category.position,
                    'is_active': category.is_active
                })
            
            elif request.method == 'DELETE':
                success = crud.delete_category(db, category_id)
                if not success:
                    return jsonify({'error': 'Category not found'}), 404
                return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error in admin category detail: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/products', methods=['GET', 'POST'])
@limiter.limit("30 per minute")
def admin_products_api():
    """Get all products or create new one"""
    try:
        if request.method == 'GET':
            category_id = request.args.get('category_id', type=int)
            with get_db() as db:
                products = crud.get_products(db, category_id=category_id, active_only=False)
                return jsonify([{
                    'id': prod.id,
                    'name': prod.name,
                    'description': prod.description,
                    'price': prod.price,
                    'stock': prod.stock,
                    'brand': prod.brand,
                    'sizes': prod.sizes,
                    'size_stock': prod.size_stock,
                    'photos': prod.photos.split(',') if prod.photos else [],
                    'category_id': prod.category_id,
                    'category_name': prod.category.name,
                    'is_active': prod.is_active,
                    'position': prod.position
                } for prod in products])
        
        elif request.method == 'POST':
            data = request.json
            with get_db() as db:
                product = crud.create_product(
                    db,
                    category_id=data['category_id'],
                    name=data['name'],
                    description=data.get('description', ''),
                    price=float(data['price']),
                    stock=int(data.get('stock', 0)),
                    sizes=data.get('sizes'),
                    photos=data.get('photos'),
                    size_chart=data.get('size_chart')
                )
                # Update brand and size_stock if provided
                if 'brand' in data:
                    product.brand = data['brand']
                if 'size_stock' in data:
                    product.size_stock = data['size_stock']
                db.commit()
                db.refresh(product)
                
                return jsonify({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'stock': product.stock,
                    'brand': product.brand,
                    'sizes': product.sizes,
                    'size_stock': product.size_stock,
                    'photos': product.photos.split(',') if product.photos else [],
                    'category_id': product.category_id,
                    'is_active': product.is_active
                }), 201
    except Exception as e:
        app.logger.error(f"Error in admin products API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/products/<int:product_id>', methods=['PUT', 'DELETE'])
@limiter.limit("30 per minute")
def admin_product_detail(product_id):
    """Update or delete product"""
    try:
        with get_db() as db:
            if request.method == 'PUT':
                data = request.json
                product = crud.update_product(db, product_id, **data)
                if not product:
                    return jsonify({'error': 'Product not found'}), 404
                return jsonify({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'stock': product.stock,
                    'brand': product.brand,
                    'sizes': product.sizes,
                    'size_stock': product.size_stock,
                    'photos': product.photos.split(',') if product.photos else [],
                    'category_id': product.category_id,
                    'is_active': product.is_active
                })
            
            elif request.method == 'DELETE':
                success = crud.delete_product(db, product_id)
                if not success:
                    return jsonify({'error': 'Product not found'}), 404
                return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error in admin product detail: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats')
@limiter.limit("10 per minute")
def admin_stats():
    """Get admin statistics"""
    try:
        with get_db() as db:
            from database.models import Order, User, Product
            
            total_orders = db.query(Order).count()
            total_revenue = db.query(Order).filter(Order.payment_status == 'succeeded').with_entities(
                db.func.sum(Order.total_amount)
            ).scalar() or 0
            total_users = db.query(User).count()
            total_products = db.query(Product).filter(Product.is_active == True).count()
            
            return jsonify({
                'total_orders': total_orders,
                'total_revenue': int(total_revenue),
                'total_users': total_users,
                'total_products': total_products
            })
    except Exception as e:
        app.logger.error(f"Error fetching admin stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/admin/orders')
@limiter.limit("10 per minute")
def admin_orders():
    """Get recent orders for admin"""
    try:
        limit = request.args.get('limit', 10, type=int)
        with get_db() as db:
            from database.models import Order
            
            orders = db.query(Order).order_by(Order.created_at.desc()).limit(limit).all()
            
            return jsonify([{
                'id': order.id,
                'user_name': order.user.username if order.user else None,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at.isoformat()
            } for order in orders])
    except Exception as e:
        app.logger.error(f"Error fetching admin orders: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'webapp'
    })
