import uuid
from yookassa import Configuration, Payment
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, BOT_URL
import logging

logger = logging.getLogger(__name__)

# Configure YooKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


def create_payment(amount: float, order_id: int, description: str, return_url: str = None) -> dict:
    """
    Create YooKassa payment
    
    Args:
        amount: Payment amount in rubles
        order_id: Order ID for tracking
        description: Payment description
        return_url: URL to return after payment
    
    Returns:
        dict with payment info including confirmation_url
    """
    try:
        idempotence_key = str(uuid.uuid4())
        
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or f"{BOT_URL}/payment/success"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "order_id": order_id
            }
        }
        
        payment = Payment.create(payment_data, idempotence_key)
        
        return {
            "id": payment.id,
            "status": payment.status,
            "confirmation_url": payment.confirmation.confirmation_url,
            "amount": amount,
            "currency": "RUB"
        }
    
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return None


def check_payment_status(payment_id: str) -> dict:
    """
    Check payment status
    
    Args:
        payment_id: YooKassa payment ID
    
    Returns:
        dict with payment status info
    """
    try:
        payment = Payment.find_one(payment_id)
        
        return {
            "id": payment.id,
            "status": payment.status,
            "paid": payment.paid,
            "amount": float(payment.amount.value),
            "currency": payment.amount.currency,
            "metadata": payment.metadata
        }
    
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        return None


def cancel_payment(payment_id: str) -> bool:
    """
    Cancel payment
    
    Args:
        payment_id: YooKassa payment ID
    
    Returns:
        bool: True if cancelled successfully
    """
    try:
        payment = Payment.find_one(payment_id)
        
        if payment.status == "pending":
            Payment.cancel(payment_id)
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}")
        return False


def refund_payment(payment_id: str, amount: float = None) -> bool:
    """
    Refund payment
    
    Args:
        payment_id: YooKassa payment ID
        amount: Amount to refund (None for full refund)
    
    Returns:
        bool: True if refunded successfully
    """
    try:
        from yookassa import Refund
        
        payment = Payment.find_one(payment_id)
        
        if payment.status != "succeeded":
            return False
        
        refund_amount = amount or float(payment.amount.value)
        
        idempotence_key = str(uuid.uuid4())
        
        refund = Refund.create({
            "amount": {
                "value": f"{refund_amount:.2f}",
                "currency": "RUB"
            },
            "payment_id": payment_id
        }, idempotence_key)
        
        return refund.status == "succeeded"
    
    except Exception as e:
        logger.error(f"Error refunding payment: {e}")
        return False
