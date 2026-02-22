from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime, date
from bson import ObjectId
from models.user import PyObjectId

class MedicineInventory(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(..., min_length=2)
    generic_name: Optional[str] = None
    category: str  # Allopathic, Ayurvedic, Homeopathic
    subcategory: Optional[str] = None  # Cardiovascular, Diabetes, etc.
    manufacturer: str
    supplier: str
    description: Optional[str] = None
    dosage_form: str  # Tablet, Capsule, Syrup, Injection, etc.
    strength: str  # "500mg", "10ml", etc.
    stock_quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=100, ge=0)
    unit_price: float = Field(ge=0)
    selling_price: float = Field(ge=0)
    currency: str = Field(default="INR")
    batch_number: str
    manufacturing_date: date
    expiry_date: date
    storage_location: Optional[str] = None
    requires_prescription: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('expiry_date')
    def expiry_must_be_future(cls, v, values):
        if 'manufacturing_date' in values and v <= values['manufacturing_date']:
            raise ValueError('Expiry date must be after manufacturing date')
        return v
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, date: lambda v: v.isoformat()}

class Prescription(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    patient_id: str
    doctor_id: str
    consultation_id: Optional[str] = None
    medications: List[Dict] = Field(default_factory=list)  # {medicine_id, dosage, frequency, duration}
    diagnosis: str
    instructions: Optional[str] = None
    prescribed_date: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    is_filled: bool = Field(default=False)
    pharmacy_id: Optional[str] = None
    filled_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

class MedicineOrder(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    prescription_id: Optional[str] = None
    patient_id: str
    items: List[Dict]  # {medicine_id, quantity, price}
    total_amount: float = Field(ge=0)
    delivery_address: str
    delivery_status: str = Field(default="pending")  # pending, processing, shipped, delivered
    payment_status: str = Field(default="pending")  # pending, paid, failed
    order_date: datetime = Field(default_factory=datetime.utcnow)
    estimated_delivery: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}