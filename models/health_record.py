from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class VitalSigns(BaseModel):
    blood_pressure_systolic: Optional[int] = Field(None, ge=60, le=250)
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=150)
    heart_rate: Optional[int] = Field(None, ge=30, le=220)
    temperature: Optional[float] = Field(None, ge=35.0, le=42.0)
    respiratory_rate: Optional[int] = Field(None, ge=8, le=40)
    oxygen_saturation: Optional[int] = Field(None, ge=70, le=100)
    blood_glucose: Optional[float] = Field(None, ge=20, le=600)
    weight: Optional[float] = Field(None, ge=20, le=300)
    height: Optional[float] = Field(None, ge=50, le=250)

class HealthRiskPrediction(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    risk_category: str  # Cardiovascular, Diabetes, Respiratory, etc.
    risk_level: str = Field(..., regex=r'^(Low|Medium|High|Critical)$')
    probability: float = Field(..., ge=0, le=100)
    timeframe: str  # "6-9 months", "12-18 months"
    recommendations: List[str]
    ai_confidence: float = Field(..., ge=0, le=100)
    ai_model_version: str = Field(default="gpt-4")
    input_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class HealthRecord(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    record_type: str  # Lab Report, Prescription, Imaging, etc.
    date: datetime
    facility: Optional[str] = None
    doctor_id: Optional[str] = None
    diagnosis: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    medications: List[Dict[str, str]] = Field(default_factory=list)
    vital_signs: Optional[VitalSigns] = None
    lab_results: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)
    abdm_synced: bool = Field(default=False)
    abdm_record_id: Optional[str] = None
    privacy_level: str = Field(default="private")  # private, shared, public
    shared_with: List[str] = Field(default_factory=list)  # list of user_ids
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}