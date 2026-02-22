from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
import uuid

class Vitals(BaseModel):
    blood_pressure_systolic: Optional[int] = Field(None, ge=70, le=250)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=150)
    heart_rate: Optional[int] = Field(None, ge=40, le=200)
    temperature: Optional[float] = Field(None, ge=95.0, le=108.0)  # Fahrenheit
    weight: Optional[float] = Field(None, ge=0.5, le=500)  # kg
    height: Optional[float] = Field(None, ge=30, le=250)  # cm
    bmi: Optional[float] = None
    blood_sugar: Optional[int] = Field(None, ge=20, le=600)  # mg/dL
    oxygen_saturation: Optional[int] = Field(None, ge=70, le=100)  # %
    respiratory_rate: Optional[int] = Field(None, ge=8, le=40)  # breaths/min
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

class MedicalRecordCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_id: str
    vitals: Optional[Vitals] = None
    chief_complaint: str = Field(..., min_length=5, max_length=500)
    symptoms: List[str] = Field(default_factory=list)
    diagnosis: str = Field(..., min_length=10, max_length=1000)
    treatment_plan: str = Field(..., min_length=10, max_length=2000)
    notes: Optional[str] = None
    follow_up_required: bool = Field(default=False)
    follow_up_days: Optional[int] = None

class MedicalRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    patient_id: str
    doctor_id: str
    appointment_id: str
    record_date: datetime = Field(default_factory=datetime.utcnow)
    
    # Clinical data
    vitals: Optional[Vitals] = None
    chief_complaint: str
    symptoms: List[str] = Field(default_factory=list)
    diagnosis: str
    diagnosis_codes: List[str] = Field(default_factory=list)  # ICD-10 codes
    treatment_plan: str
    notes: Optional[str] = None
    
    # Follow-up
    follow_up_required: bool = Field(default=False)
    follow_up_days: Optional[int] = None
    follow_up_scheduled: bool = Field(default=False)
    
    # USP: Data Privacy - Encryption status
    is_encrypted: bool = Field(default=True)
    encryption_key_id: Optional[str] = None
    
    # Attachments
    attachments: List[Dict] = Field(default_factory=list)  # {type, url, name}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "chief_complaint": "Persistent headache for 3 days",
                "symptoms": ["headache", "nausea", "sensitivity to light"],
                "diagnosis": "Migraine headache",
                "treatment_plan": "Prescribed sumatriptan, advised rest and hydration"
            }
        }
