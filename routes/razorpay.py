from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid
import hashlib
import hmac
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/razorpay", tags=["Razorpay"])

# MOCKED Razorpay Integration (for development/testing)
# In production, use actual Razorpay SDK: pip install razorpay

MOCKED_RAZORPAY_KEY = "rzp_test_mock_key_12345"
MOCKED_RAZORPAY_SECRET = "mock_secret_67890"

# Request/Response Models
class OrderCreateRequest(BaseModel):
    invoice_id: str
    amount: float = Field(ge=0)
    currency: str = Field(default="INR")

class OrderResponse(BaseModel):
    order_id: str
    amount: float
    currency: str
    status: str
    invoice_id: str
    razorpay_key: str

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    invoice_id: str

class PaymentWebhook(BaseModel):
    event: str
    payload: dict

# Helper Functions
def generate_mock_signature(order_id: str, payment_id: str) -> str:
    """Generate mock signature for testing (mimics Razorpay signature)"""
    message = f"{order_id}|{payment_id}"
    signature = hmac.new(
        MOCKED_RAZORPAY_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay payment signature (mocked)"""
    expected_signature = generate_mock_signature(order_id, payment_id)
    return hmac.compare_digest(expected_signature, signature)

# Routes
@router.post("/create-order", response_model=OrderResponse)
async def create_razorpay_order(
    order_request: OrderCreateRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create Razorpay order for invoice payment (MOCKED)"""
    user_id = current_user["user_id"]
    
    # Find user's organization
    org = await db.organizations.find_one(
        {"$or": [
            {"admin_user_id": user_id},
            {"team_members": user_id}
        ]},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for this user"
        )
    
    # Verify invoice exists and belongs to organization
    invoice = await db.invoices.find_one(
        {"id": order_request.invoice_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice["status"] == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already paid"
        )
    
    # MOCKED: Create Razorpay order
    # In production: use razorpay.Client.order.create()
    order_id = f"order_mock_{uuid.uuid4().hex[:16]}"
    amount_paise = int(order_request.amount * 100)  # Convert to paise
    
    order_data = {
        "order_id": order_id,
        "amount": order_request.amount,
        "amount_paise": amount_paise,
        "currency": order_request.currency,
        "status": "created",
        "invoice_id": order_request.invoice_id,
        "organization_id": org["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Store order in database
    await db.razorpay_orders.insert_one(order_data)
    
    return OrderResponse(
        order_id=order_id,
        amount=order_request.amount,
        currency=order_request.currency,
        status="created",
        invoice_id=order_request.invoice_id,
        razorpay_key=MOCKED_RAZORPAY_KEY
    )

@router.post("/verify-payment")
async def verify_razorpay_payment(
    payment_verify: PaymentVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Verify Razorpay payment and update invoice status (MOCKED)"""
    user_id = current_user["user_id"]
    
    # Find user's organization
    org = await db.organizations.find_one(
        {"$or": [
            {"admin_user_id": user_id},
            {"team_members": user_id}
        ]},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for this user"
        )
    
    # Verify signature (MOCKED)
    is_valid = verify_payment_signature(
        payment_verify.razorpay_order_id,
        payment_verify.razorpay_payment_id,
        payment_verify.razorpay_signature
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature"
        )
    
    # Update invoice status
    invoice = await db.invoices.find_one(
        {"id": payment_verify.invoice_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Update invoice as paid
    payment_details = {
        "method": "razorpay",
        "razorpay_order_id": payment_verify.razorpay_order_id,
        "razorpay_payment_id": payment_verify.razorpay_payment_id,
        "paid_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.invoices.update_one(
        {"id": payment_verify.invoice_id},
        {
            "$set": {
                "status": "paid",
                "payment_details": payment_details,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Update order status
    await db.razorpay_orders.update_one(
        {"order_id": payment_verify.razorpay_order_id},
        {
            "$set": {
                "status": "paid",
                "payment_id": payment_verify.razorpay_payment_id,
                "paid_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Payment verified and invoice marked as paid",
        "invoice_id": payment_verify.invoice_id,
        "payment_id": payment_verify.razorpay_payment_id,
        "status": "paid"
    }

@router.post("/webhook")
async def razorpay_webhook(webhook_data: PaymentWebhook, db = Depends(get_db)):
    """Handle Razorpay webhooks (MOCKED)"""
    # In production, verify webhook signature
    # webhook_signature = request.headers.get('X-Razorpay-Signature')
    
    event = webhook_data.event
    payload = webhook_data.payload
    
    # Handle different webhook events
    if event == "payment.captured":
        # Payment successful
        payment_id = payload.get("payment_id")
        order_id = payload.get("order_id")
        
        # Find and update order
        order = await db.razorpay_orders.find_one(
            {"order_id": order_id},
            {"_id": 0}
        )
        
        if order:
            # Update invoice
            await db.invoices.update_one(
                {"id": order["invoice_id"]},
                {
                    "$set": {
                        "status": "paid",
                        "payment_details": {
                            "method": "razorpay",
                            "razorpay_payment_id": payment_id,
                            "razorpay_order_id": order_id,
                            "paid_at": datetime.now(timezone.utc).isoformat()
                        },
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
    
    elif event == "payment.failed":
        # Payment failed
        payment_id = payload.get("payment_id")
        order_id = payload.get("order_id")
        
        # Update order status
        await db.razorpay_orders.update_one(
            {"order_id": order_id},
            {"$set": {"status": "failed"}}
        )
    
    return {"status": "ok", "event": event}

@router.get("/payment-methods")
async def get_payment_methods(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get available payment methods"""
    return {
        "payment_methods": [
            {
                "id": "razorpay",
                "name": "Razorpay",
                "description": "Pay using Cards, UPI, Netbanking, Wallets",
                "enabled": True,
                "mocked": True
            },
            {
                "id": "card",
                "name": "Credit/Debit Card",
                "description": "Direct card payment",
                "enabled": True,
                "mocked": True
            },
            {
                "id": "upi",
                "name": "UPI",
                "description": "Pay using UPI ID",
                "enabled": True,
                "mocked": True
            }
        ],
        "note": "All payment methods are currently mocked for development"
    }
