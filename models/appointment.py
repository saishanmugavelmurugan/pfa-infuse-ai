from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, date, time
import uuid

class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_date: date
    appointment_time: str  # HH:MM format
    duration_minutes: int = Field(default=30, ge=15, le=120)
    appointment_type: str = Field(..., pattern=r'^(consultation|follow-up|emergency|check-up)$')
    reason: str = Field(..., min_length=10, max_length=500)
    notes: Optional[str] = None
    is_telemedicine: bool = Field(default=False)

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    doctor_notes: Optional[str] = None

class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    patient_id: str
    doctor_id: str
    appointment_date: date
    appointment_time: str
    duration_minutes: int
    appointment_type: str
    status: str = Field(default="scheduled")  # scheduled, confirmed, in-progress, completed, cancelled, no-show
    reason: str
    notes: Optional[str] = None
    doctor_notes: Optional[str] = None
    is_telemedicine: bool = Field(default=False)
    telemedicine_room_id: Optional[str] = None
    
    # USP: Appointment Guarantee System
    doctor_confirmed: bool = Field(default=False)
    doctor_confirmed_at: Optional[datetime] = None
    backup_doctor_id: Optional[str] = None
    guarantee_status: str = Field(default="pending")  # pending, guaranteed, cancelled-refunded
    
    # USP: Smart Matching Score
    match_score: Optional[float] = None  # AI matching confidence 0-1
    match_reasons: list = Field(default_factory=list)
    
    # Reminder tracking
    reminder_sent: bool = Field(default=False)
    reminder_sent_at: Optional[datetime] = None
    
    # Payment tracking
    payment_status: str = Field(default="pending")  # pending, paid, refunded
    payment_amount: float = Field(default=0.0)
    refund_amount: Optional[float] = None
    refund_reason: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    cancelled_by: Optional[str] = None
    cancellation_reason: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "uuid",
                "doctor_id": "uuid",
                "appointment_date": "2024-12-15",
                "appointment_time": "10:30",
                "appointment_type": "consultation",
                "reason": "Regular checkup for diabetes"
            }
        }
