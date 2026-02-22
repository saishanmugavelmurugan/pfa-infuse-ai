from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid

class TelemedicineSessionCreate(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str

class ChatMessage(BaseModel):
    sender_id: str
    sender_type: str  # doctor, patient
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: str = Field(default="text")  # text, file, image
    file_url: Optional[str] = None

class TelemedicineSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    appointment_id: str
    patient_id: str
    doctor_id: str
    
    # Session details
    video_room_id: str  # For video conferencing
    session_token: Optional[str] = None
    
    # Timing
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    scheduled_duration: int = Field(default=30)
    
    # Status
    status: str = Field(default="scheduled")  # scheduled, waiting, in-progress, completed, cancelled
    
    # USP: Recording (with consent)
    recording_enabled: bool = Field(default=False)
    recording_consent_given: bool = Field(default=False)
    recording_url: Optional[str] = None
    
    # Chat
    chat_enabled: bool = Field(default=True)
    chat_transcript: List[ChatMessage] = Field(default_factory=list)
    
    # Files shared
    shared_files: List[Dict] = Field(default_factory=list)  # {name, url, shared_by, timestamp}
    
    # Quality metrics
    connection_quality: Optional[str] = None  # excellent, good, fair, poor
    patient_rating: Optional[int] = Field(None, ge=1, le=5)
    doctor_rating: Optional[int] = Field(None, ge=1, le=5)
    
    # Session notes
    session_notes: Optional[str] = None
    technical_issues: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "appointment_id": "uuid",
                "patient_id": "uuid",
                "doctor_id": "uuid",
                "video_room_id": "room_abc123"
            }
        }
