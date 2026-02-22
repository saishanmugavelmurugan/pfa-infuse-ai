from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import uuid

class Medication(BaseModel):
    drug_id: Optional[str] = None
    drug_name: str = Field(..., min_length=2, max_length=200)
    generic_name: Optional[str] = None
    dosage: str = Field(..., min_length=2, max_length=100)  # e.g., "500mg"
    frequency: str = Field(..., min_length=2, max_length=100)  # e.g., "twice daily"
    duration: str = Field(..., min_length=2, max_length=100)  # e.g., "7 days"
    quantity: int = Field(..., ge=1)
    instructions: str = Field(..., min_length=5, max_length=500)  # e.g., "Take after meals"
    form: Optional[str] = None  # tablet, syrup, injection, etc.

class PrescriptionCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_id: str
    medical_record_id: Optional[str] = None
    medications: List[Medication]
    diagnosis: str
    notes: Optional[str] = None
    valid_until: Optional[date] = None

class Prescription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    patient_id: str
    doctor_id: str
    appointment_id: str
    medical_record_id: Optional[str] = None
    prescription_number: str  # Auto-generated unique number
    
    prescription_date: datetime = Field(default_factory=datetime.utcnow)
    medications: List[Medication]
    diagnosis: str
    notes: Optional[str] = None
    
    # USP: Follow-up tracking
    valid_until: Optional[date] = None
    is_follow_up_prescription: bool = Field(default=False)
    original_prescription_id: Optional[str] = None
    refill_count: int = Field(default=0)
    max_refills: int = Field(default=0)
    
    status: str = Field(default="active")  # active, completed, cancelled, expired
    
    # Digital signature
    doctor_signature: Optional[str] = None  # Digital signature hash
    signed_at: Optional[datetime] = None
    
    # USP: Transparent pricing
    estimated_cost: Optional[float] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "medications": [
                    {
                        "drug_name": "Paracetamol",
                        "dosage": "500mg",
                        "frequency": "Three times daily",
                        "duration": "5 days",
                        "quantity": 15,
                        "instructions": "Take after meals with water"
                    }
                ],
                "diagnosis": "Viral fever"
            }
        }
