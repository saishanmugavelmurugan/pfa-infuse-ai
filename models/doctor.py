from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime, time
from bson import ObjectId
from models.user import PyObjectId

class DoctorSpecialization(BaseModel):
    primary: str
    secondary: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

class DoctorAvailability(BaseModel):
    day: str  # Monday, Tuesday, etc.
    start_time: str  # "09:00"
    end_time: str  # "17:00"
    slots_per_hour: int = Field(default=4)

class DoctorProfile(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str  # Reference to User model
    specialization: DoctorSpecialization
    qualification: str
    experience_years: int = Field(ge=0)
    license_number: str
    hospital_affiliation: Optional[str] = None
    country: str
    city: str
    languages: List[str]
    consultation_fee: float = Field(ge=0)
    currency: str = Field(default="INR")
    availability: List[DoctorAvailability]
    rating: float = Field(default=0.0, ge=0, le=5)
    total_reviews: int = Field(default=0, ge=0)
    total_consultations: int = Field(default=0, ge=0)
    patients_count: int = Field(default=0, ge=0)
    revenue_generated: float = Field(default=0.0, ge=0)
    is_verified: bool = Field(default=False)
    verification_documents: List[str] = Field(default_factory=list)
    join_date: datetime = Field(default_factory=datetime.utcnow)
    is_accepting_patients: bool = Field(default=True)
    telemedicine_enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class DoctorReview(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    doctor_id: str
    patient_id: str
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None
    consultation_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}