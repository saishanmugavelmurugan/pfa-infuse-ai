from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/billing", tags=["HealthTrack - Billing"])

GST_RATE = 0.18

@router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create billing invoice - USP: Transparent pricing with GST"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Calculate amounts
    subtotal = sum(item["amount"] for item in invoice_data.get("items", []))
    discount = invoice_data.get("discount", 0)
    subtotal_after_discount = subtotal - discount
    tax_amount = subtotal_after_discount * GST_RATE
    total_amount = subtotal_after_discount + tax_amount
    insurance_covered = invoice_data.get("insurance_covered", 0)
    patient_responsibility = total_amount - insurance_covered
    
    invoice_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "invoice_number": f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "invoice_date": datetime.now(timezone.utc).isoformat(),
        "due_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
        "subtotal": subtotal,
        "discount": discount,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
        "insurance_covered": insurance_covered,
        "patient_responsibility": patient_responsibility,
        "payment_status": "unpaid",
        "amount_paid": 0.0,
        "balance_due": patient_responsibility,
        "refund_amount": 0.0,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **invoice_data
    }
    
    await db.healthtrack_invoices.insert_one(invoice_dict)
    invoice_dict.pop("_id", None)
    
    return {"message": "Invoice created", "invoice": invoice_dict}

@router.get("/invoices")
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    patient_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List billing invoices"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"organization_id": org["id"]}
    if patient_id:
        query["patient_id"] = patient_id
    if status_filter:
        query["payment_status"] = status_filter
    
    total = await db.healthtrack_invoices.count_documents(query)
    invoices = await db.healthtrack_invoices.find(query, {"_id": 0}).sort("invoice_date", -1).skip(skip).limit(limit).to_list(limit)
    
    return {"total": total, "invoices": invoices}

@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get invoice details"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    invoice = await db.healthtrack_invoices.find_one({"id": invoice_id, "organization_id": org["id"]}, {"_id": 0})
    
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    return invoice

@router.post("/payments")
async def process_payment(
    payment_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Process payment for invoice - USP: Instant refund capability"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    invoice_id = payment_data.get("invoice_id")
    amount = payment_data.get("amount")
    
    invoice = await db.healthtrack_invoices.find_one(
        {"id": invoice_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    new_amount_paid = invoice["amount_paid"] + amount
    new_balance = invoice["balance_due"] - amount
    new_status = "paid" if new_balance <= 0 else "partial"
    
    await db.healthtrack_invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "amount_paid": new_amount_paid,
            "balance_due": max(0, new_balance),
            "payment_status": new_status,
            "payment_date": datetime.now(timezone.utc).isoformat(),
            "payment_method": payment_data.get("payment_method"),
            "payment_transaction_id": payment_data.get("transaction_id"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Payment processed", "new_balance": max(0, new_balance), "status": new_status}

@router.get("/outstanding")
async def get_outstanding_bills(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all outstanding bills"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    outstanding = await db.healthtrack_invoices.find(
        {
            "organization_id": org["id"],
            "payment_status": {"$in": ["unpaid", "partial"]}
        },
        {"_id": 0}
    ).to_list(100)
    
    total_due = sum(inv["balance_due"] for inv in outstanding)
    
    return {"total_invoices": len(outstanding), "total_amount_due": total_due, "invoices": outstanding}

@router.get("/reports")
async def get_billing_reports(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get billing reports"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"organization_id": org["id"]}
    
    all_invoices = await db.healthtrack_invoices.find(query, {"_id": 0}).to_list(1000)
    
    total_billed = sum(inv["total_amount"] for inv in all_invoices)
    total_collected = sum(inv["amount_paid"] for inv in all_invoices)
    total_outstanding = sum(inv["balance_due"] for inv in all_invoices if inv["payment_status"] != "paid")
    
    return {
        "total_invoices": len(all_invoices),
        "total_billed": total_billed,
        "total_collected": total_collected,
        "total_outstanding": total_outstanding,
        "collection_rate": (total_collected / total_billed * 100) if total_billed > 0 else 0
    }
