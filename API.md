# API Documentation

## Database Models

### User
- `id`: Integer (Primary Key)
- `telegram_id`: Integer (Unique)
- `username`: String
- `first_name`: String
- `last_name`: String
- `phone`: String
- `is_active`: Boolean
- `is_blocked`: Boolean
- `theme`: String ('light' or 'dark')
- `created_at`: DateTime
- `last_activity`: DateTime

### Category
- `id`: Integer (Primary Key)
- `name`: String
- `description`: Text
- `icon`: String
- `position`: Integer
- `is_active`: Boolean
- `created_at`: DateTime

### Product
- `id`: Integer (Primary Key)
- `category_id`: Integer (Foreign Key)
- `name`: String
- `description`: Text
- `price`: Float
- `photos`: Text (comma-separated file_ids)
- `stock`: Integer
- `sizes`: String (JSON array)
- `size_chart`: Text
- `is_active`: Boolean
- `position`: Integer
- `created_at`: DateTime
- `updated_at`: DateTime

### Order
- `id`: Integer (Primary Key)
- `user_id`: Integer (Foreign Key)
- `order_number`: String (Unique)
- `total_amount`: Float
- `status`: String (pending/processing/completed/cancelled)
- `payment_id`: String
- `payment_status`: String
- `delivery_address`: Text
- `phone`: String
- `comment`: Text
- `created_at`: DateTime
- `updated_at`: DateTime

### OrderItem
- `id`: Integer (Primary Key)
- `order_id`: Integer (Foreign Key)
- `product_id`: Integer (Foreign Key)
- `product_name`: String
- `price`: Float
- `quantity`: Integer
- `size`: String

### CartItem
- `id`: Integer (Primary Key)
- `user_id`: Integer (Foreign Key)
- `product_id`: Integer (Foreign Key)
- `quantity`: Integer
- `size`: String
- `created_at`: DateTime

## CRUD Operations

### User Operations

\`\`\`python
# Get or create user
user = crud.get_or_create_user(db, telegram_id, username, first_name, last_name)

# Get user by telegram ID
user = crud.get_user_by_telegram_id(db, telegram_id)

# Update user theme
crud.update_user_theme(db, telegram_id, 'dark')

# Block/unblock user
crud.update_user_status(db, user_id, is_active=False)
\`\`\`

### Category Operations

\`\`\`python
# Create category
category = crud.create_category(db, name="T-Shirts", icon="👕")

# Get all categories
categories = crud.get_all_categories(db)

# Get active categories
categories = crud.get_categories(db, active_only=True)

# Update category
crud.update_category(db, category_id, name="New Name")

# Delete category
crud.delete_category(db, category_id)
\`\`\`

### Product Operations

\`\`\`python
# Create product
product = crud.create_product(
    db,
    category_id=1,
    name="Cool T-Shirt",
    description="Very cool shirt",
    price=1999.99,
    stock=10,
    sizes="S,M,L,XL",
    photos="file_id_1,file_id_2"
)

# Get products by category
products = crud.get_products(db, category_id=1)

# Update product
crud.update_product(db, product_id, price=1499.99, stock=5)

# Delete product
crud.delete_product(db, product_id)
\`\`\`

### Cart Operations

\`\`\`python
# Add to cart
cart_item = crud.add_to_cart(db, user_id, product_id, quantity=1, size="M")

# Get cart items
cart_items = crud.get_cart_items(db, user_id)

# Update cart item quantity
crud.update_cart_item(db, cart_item_id, quantity=2)

# Remove from cart
crud.remove_cart_item(db, cart_item_id)

# Clear cart
crud.clear_cart(db, user_id)
\`\`\`

### Order Operations

\`\`\`python
# Create order
order = crud.create_order(
    db,
    user_id=user_id,
    cart_items=cart_items,
    phone="+79991234567",
    delivery_address="Moscow, Red Square, 1",
    comment="Please call before delivery"
)

# Get user orders
orders = crud.get_orders(db, user_id=user_id)

# Get order by ID
order = crud.get_order(db, order_id)

# Update order status
crud.update_order_status(db, order_id, 'processing')

# Update payment status
crud.update_order_payment_status(db, order_id, 'succeeded')
\`\`\`

### Statistics

\`\`\`python
# Get statistics
stats = crud.get_statistics(db, days=30)
# Returns: {
#     'total_users': int,
#     'new_users': int,
#     'total_orders': int,
#     'period_orders': int,
#     'total_revenue': float,
#     'period_revenue': float,
#     'pending_orders': int
# }

# Get top products
top_products = crud.get_top_products(db, limit=5)
\`\`\`

## WebApp API Endpoints

### GET /api/categories
Returns all active categories.

**Response:**
\`\`\`json
[
  {
    "id": 1,
    "name": "T-Shirts",
    "description": "Cool t-shirts",
    "icon": "👕",
    "product_count": 5
  }
]
\`\`\`

### GET /api/products?category_id=1
Returns products in category.

**Response:**
\`\`\`json
[
  {
    "id": 1,
    "name": "Cool T-Shirt",
    "description": "Very cool",
    "price": 1999.99,
    "stock": 10,
    "sizes": "S,M,L,XL",
    "photos": ["file_id_1", "file_id_2"],
    "category_id": 1
  }
]
\`\`\`

### GET /api/product/{product_id}
Returns single product details.

**Response:**
\`\`\`json
{
  "id": 1,
  "name": "Cool T-Shirt",
  "description": "Very cool",
  "price": 1999.99,
  "stock": 10,
  "sizes": "S,M,L,XL",
  "size_chart": "S: 46-48, M: 48-50...",
  "photos": ["file_id_1", "file_id_2"],
  "category_id": 1,
  "category_name": "T-Shirts"
}
\`\`\`

## Payment Integration

### Create Payment

\`\`\`python
from utils.payment import create_payment

payment = create_payment(
    amount=1999.99,
    order_id=123,
    description="Order #123",
    return_url="https://t.me/yourbot"
)

# Returns:
# {
#     'id': 'payment_id',
#     'status': 'pending',
#     'confirmation_url': 'https://yookassa.ru/...',
#     'amount': 1999.99,
#     'currency': 'RUB'
# }
\`\`\`

### Check Payment Status

\`\`\`python
from utils.payment import check_payment_status

status = check_payment_status('payment_id')

# Returns:
# {
#     'id': 'payment_id',
#     'status': 'succeeded',
#     'paid': True,
#     'amount': 1999.99,
#     'currency': 'RUB',
#     'metadata': {'order_id': 123}
# }
\`\`\`

## Bot Commands

### User Commands
- `/start` - Start bot and show main menu
- `/help` - Show help message

### Admin Commands
- `/admin` - Open admin panel

### Callback Data Format

- `category_{id}` - View category
- `product_{id}` - View product
- `add_to_cart_{product_id}_{size}` - Add to cart
- `cart_increase_{cart_item_id}` - Increase quantity
- `cart_decrease_{cart_item_id}` - Decrease quantity
- `cart_remove_{cart_item_id}` - Remove from cart
- `order_{id}` - View order
- `pay_order_{id}` - Pay for order
- `admin_*` - Admin actions
