from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
import uuid
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/billing", tags=["Billing"])

# GST Rate (India)
GST_RATE = 0.18  # 18% GST

# Request/Response Models
class InvoiceItem(BaseModel):
    description: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    amount: float = Field(ge=0)

class InvoiceCreate(BaseModel):
    items: List[InvoiceItem]
    notes: Optional[str] = None

class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    organization_id: str
    organization_name: str
    billing_email: str
    items: List[Dict]
    subtotal: float
    gst_amount: float
    gst_rate: float
    total_amount: float
    currency: str
    status: str
    invoice_date: str
    due_date: str
    payment_details: Optional[Dict]
    notes: Optional[str]

class PaymentRequest(BaseModel):
    invoice_id: str
    payment_method: str = Field(..., pattern="^(razorpay|card|upi|netbanking|wallet)$")
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_signature: Optional[str] = None

# Helper Functions
def generate_invoice_number():
    """Generate unique invoice number"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"INV-{timestamp}"

def calculate_gst(subtotal: float) -> tuple:
    """Calculate GST amount"""
    gst_amount = subtotal * GST_RATE
    total = subtotal + gst_amount
    return gst_amount, total

# Routes
@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new invoice for organization - admin only"""
    user_id = current_user["user_id"]
    
    # Find user's organization (must be admin)
    org = await db.organizations.find_one(
        {"admin_user_id": user_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin can create invoices"
        )
    
    # Calculate amounts
    items = [item.model_dump() for item in invoice_data.items]
    subtotal = sum(item["amount"] for item in items)
    gst_amount, total_amount = calculate_gst(subtotal)
    
    # Create invoice
    invoice_dict = {
        "id": str(uuid.uuid4()),
        "invoice_number": generate_invoice_number(),
        "organization_id": org["id"],
        "organization_name": org["company_name"],
        "billing_email": org["billing_email"],
        "items": items,
        "subtotal": subtotal,
        "gst_amount": gst_amount,
        "gst_rate": GST_RATE,
        "total_amount": total_amount,
        "currency": "INR",
        "status": "pending",
        "invoice_date": datetime.now(timezone.utc).isoformat(),
        "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "payment_details": None,
        "notes": invoice_data.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.invoices.insert_one(invoice_dict)
    
    return InvoiceResponse(**invoice_dict)

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all invoices for user's organization"""
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
    
    # Build query
    query = {"organization_id": org["id"]}
    if status_filter:
        query["status"] = status_filter
    
    # Get invoices
    invoices = await db.invoices.find(query, {"_id": 0}).sort("invoice_date", -1).to_list(100)
    
    return [InvoiceResponse(**inv) for inv in invoices]

@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get specific invoice by ID"""
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
    
    # Get invoice
    invoice = await db.invoices.find_one(
        {"id": invoice_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return InvoiceResponse(**invoice)

@router.post("/subscription-invoice")
async def create_subscription_invoice(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Auto-generate invoice for current subscription"""
    user_id = current_user["user_id"]
    
    # Find user's organization (must be admin)
    org = await db.organizations.find_one(
        {"admin_user_id": user_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin can generate subscription invoices"
        )
    
    # Get subscription details
    from routes.subscription import SUBSCRIPTION_TIERS
    
    tier = org.get("subscription_tier", "basic")
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["basic"])
    
    total_users = len(org.get("team_members", []))
    price_per_user = tier_info["price_per_user"]
    subtotal = price_per_user * total_users
    
    # Create invoice item
    items = [{
        "description": f"{tier_info['name']} Plan - {total_users} user(s)",
        "quantity": total_users,
        "unit_price": price_per_user,
        "amount": subtotal
    }]
    
    # Calculate GST
    gst_amount, total_amount = calculate_gst(subtotal)
    
    # Create invoice
    invoice_dict = {
        "id": str(uuid.uuid4()),
        "invoice_number": generate_invoice_number(),
        "organization_id": org["id"],
        "organization_name": org["company_name"],
        "billing_email": org["billing_email"],
        "items": items,
        "subtotal": subtotal,
        "gst_amount": gst_amount,
        "gst_rate": GST_RATE,
        "total_amount": total_amount,
        "currency": "INR",
        "status": "pending",
        "invoice_date": datetime.now(timezone.utc).isoformat(),
        "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "payment_details": None,
        "notes": f"Monthly subscription for {tier_info['name']} plan",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.invoices.insert_one(invoice_dict)
    
    return InvoiceResponse(**invoice_dict)

@router.get("/dashboard")
async def get_billing_dashboard(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get billing dashboard stats for organization"""
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
    
    # Get invoice stats
    all_invoices = await db.invoices.find(
        {"organization_id": org["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    total_invoices = len(all_invoices)
    pending_invoices = len([inv for inv in all_invoices if inv["status"] == "pending"])
    paid_invoices = len([inv for inv in all_invoices if inv["status"] == "paid"])
    
    total_amount_due = sum(inv["total_amount"] for inv in all_invoices if inv["status"] == "pending")
    total_amount_paid = sum(inv["total_amount"] for inv in all_invoices if inv["status"] == "paid")
    
    # Get subscription info
    from routes.subscription import SUBSCRIPTION_TIERS
    tier = org.get("subscription_tier", "basic")
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["basic"])
    
    total_users = len(org.get("team_members", []))
    monthly_subscription_cost = tier_info["price_per_user"] * total_users
    
    return {
        "organization_id": org["id"],
        "organization_name": org["company_name"],
        "subscription": {
            "tier": tier,
            "monthly_cost": monthly_subscription_cost,
            "total_users": total_users
        },
        "invoices": {
            "total": total_invoices,
            "pending": pending_invoices,
            "paid": paid_invoices,
            "total_amount_due": total_amount_due,
            "total_amount_paid": total_amount_paid
        },
        "recent_invoices": sorted(all_invoices, key=lambda x: x["invoice_date"], reverse=True)[:5]
    }
