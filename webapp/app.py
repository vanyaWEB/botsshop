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

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'webapp'
    })
