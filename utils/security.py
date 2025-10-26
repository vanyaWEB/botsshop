import re
import hashlib
import hmac
import time
from functools import wraps
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
_rate_limit_storage: Dict[str, list] = {}


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Limit length
    text = text[:max_length]
    
    # Remove potentially dangerous characters
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    return text.strip()


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number string
    
    Returns:
        bool: True if valid
    """
    # Remove spaces and special characters
    phone = re.sub(r'[^\d+]', '', phone)
    
    # Check if it matches common phone patterns
    pattern = r'^\+?[1-9]\d{9,14}$'
    return bool(re.match(pattern, phone))


def validate_price(price: str) -> Optional[float]:
    """
    Validate and parse price input
    
    Args:
        price: Price string
    
    Returns:
        float or None if invalid
    """
    try:
        price_float = float(price.replace(',', '.'))
        if price_float <= 0 or price_float > 1000000:
            return None
        return round(price_float, 2)
    except (ValueError, AttributeError):
        return None


def validate_quantity(quantity: str) -> Optional[int]:
    """
    Validate quantity input
    
    Args:
        quantity: Quantity string
    
    Returns:
        int or None if invalid
    """
    try:
        qty = int(quantity)
        if qty < 0 or qty > 10000:
            return None
        return qty
    except (ValueError, AttributeError):
        return None


def rate_limit(max_calls: int = 5, time_window: int = 60):
    """
    Rate limiting decorator
    
    Args:
        max_calls: Maximum calls allowed
        time_window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user ID from message or callback
            user_id = None
            for arg in args:
                if hasattr(arg, 'from_user'):
                    user_id = arg.from_user.id
                    break
            
            if not user_id:
                return await func(*args, **kwargs)
            
            key = f"{func.__name__}:{user_id}"
            current_time = time.time()
            
            # Initialize or clean old entries
            if key not in _rate_limit_storage:
                _rate_limit_storage[key] = []
            
            _rate_limit_storage[key] = [
                t for t in _rate_limit_storage[key]
                if current_time - t < time_window
            ]
            
            # Check rate limit
            if len(_rate_limit_storage[key]) >= max_calls:
                logger.warning(f"Rate limit exceeded for user {user_id} on {func.__name__}")
                
                # Try to answer if it's a callback
                for arg in args:
                    if hasattr(arg, 'answer'):
                        await arg.answer(
                            "Слишком много запросов. Подождите немного.",
                            show_alert=True
                        )
                        return
                
                return
            
            # Add current call
            _rate_limit_storage[key].append(current_time)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def verify_telegram_webapp_data(init_data: str, bot_token: str) -> bool:
    """
    Verify Telegram WebApp data authenticity
    
    Args:
        init_data: Init data from Telegram WebApp
        bot_token: Bot token
    
    Returns:
        bool: True if data is authentic
    """
    try:
        # Parse init data
        params = dict(param.split('=', 1) for param in init_data.split('&'))
        
        if 'hash' not in params:
            return False
        
        received_hash = params.pop('hash')
        
        # Create data check string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(params.items())
        )
        
        # Calculate hash
        secret_key = hashlib.sha256(bot_token.encode()).digest()
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == received_hash
    
    except Exception as e:
        logger.error(f"Error verifying webapp data: {e}")
        return False


def escape_html(text: str) -> str:
    """
    Escape HTML special characters
    
    Args:
        text: Text to escape
    
    Returns:
        Escaped text
    """
    if not text:
        return ""
    
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))


def validate_image_url(url: str) -> bool:
    """
    Validate image URL format
    
    Args:
        url: Image URL
    
    Returns:
        bool: True if valid
    """
    if not url:
        return False
    
    # Check if it's a Telegram file_id or valid URL
    if url.startswith('http://') or url.startswith('https://'):
        # Basic URL validation
        pattern = r'^https?://[^\s<>"{}|\\^`\[\]]+$'
        return bool(re.match(pattern, url))
    
    # Assume it's a Telegram file_id
    return len(url) > 10 and len(url) < 200
