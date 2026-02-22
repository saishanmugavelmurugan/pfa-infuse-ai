from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class BillingItem(BaseModel):
    service_name: str
    description: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(ge=0)
    tax_rate: float = Field(default=0.0, ge=0, le=100)
    total: float = Field(ge=0)

class PaymentDetails(BaseModel):
    method: str  # card, upi, netbanking, wallet
    transaction_id: Optional[str] = None
    payment_gateway: Optional[str] = None
    paid_at: Optional[datetime] = None

class BillingRecord(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    consultation_id: Optional[str] = None
    items: List[BillingItem]
    subtotal: float = Field(ge=0)
    tax_amount: float = Field(default=0.0, ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    total_amount: float = Field(ge=0)
    currency: str = Field(default="INR")
    status: str = Field(default="pending")  # pending, paid, failed, refunded
    payment_details: Optional[PaymentDetails] = None
    invoice_number: str
    invoice_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

class Consultation(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    patient_id: str
    doctor_id: str
    appointment_date: datetime
    appointment_type: str  # in-person, telemedicine
    status: str = Field(default="scheduled")  # scheduled, completed, cancelled, no-show
    reason: str
    symptoms: List[str] = Field(default_factory=list)
    diagnosis: Optional[str] = None
    prescription: Optional[Dict] = None
    notes: Optional[str] = None
    duration_minutes: int = Field(default=30, ge=15)
    consultation_fee: float = Field(ge=0)
    billing_id: Optional[str] = None
    video_room_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}