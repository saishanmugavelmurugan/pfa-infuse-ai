from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import uuid

class InvoiceItem(BaseModel):
    service: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(..., ge=0)
    discount: float = Field(default=0.0, ge=0)
    tax_rate: float = Field(default=0.18)  # 18% GST
    amount: float = Field(..., ge=0)

class BillingInvoiceCreate(BaseModel):
    patient_id: str
    appointment_id: Optional[str] = None
    items: List[InvoiceItem]
    discount: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None

class BillingInvoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    patient_id: str
    appointment_id: Optional[str] = None
    
    invoice_number: str  # Auto-generated
    invoice_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: date
    
    # Items
    items: List[InvoiceItem]
    
    # Calculations - USP: Transparent pricing
    subtotal: float
    discount: float = Field(default=0.0)
    tax_amount: float  # GST 18%
    total_amount: float
    
    # Insurance split
    insurance_covered: float = Field(default=0.0)
    patient_responsibility: float
    
    # Payment
    payment_status: str = Field(default="unpaid")  # unpaid, partial, paid, refunded
    amount_paid: float = Field(default=0.0)
    balance_due: float
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None
    payment_transaction_id: Optional[str] = None
    
    # USP: Instant refund tracking
    refund_amount: float = Field(default=0.0)
    refund_status: Optional[str] = None
    refund_processed_at: Optional[datetime] = None
    refund_transaction_id: Optional[str] = None
    
    notes: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "service": "Consultation Fee",
                        "quantity": 1,
                        "unit_price": 500.0,
                        "amount": 500.0
                    }
                ],
                "subtotal": 500.0,
                "tax_amount": 90.0,
                "total_amount": 590.0
            }
        }
