from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid

class NotificationCreate(BaseModel):
    user_id: str
    notification_type: str = Field(..., pattern=r'^(appointment|prescription|lab|payment|general|reminder)$')
    title: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10, max_length=1000)
    delivery_method: List[str] = Field(default=["in-app"])  # in-app, email, sms, whatsapp
    scheduled_time: Optional[datetime] = None
    action_url: Optional[str] = None
    priority: str = Field(default="normal", pattern=r'^(low|normal|high|urgent)$')

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: str
    
    # Content
    notification_type: str  # appointment, prescription, lab, payment, general, reminder
    title: str
    message: str
    
    # Delivery
    delivery_method: List[str] = Field(default=["in-app"])
    
    # Status
    status: str = Field(default="pending")  # pending, sent, delivered, failed, read
    
    # Timing - USP: Reliable notifications
    scheduled_time: Optional[datetime] = None
    sent_time: Optional[datetime] = None
    delivered_time: Optional[datetime] = None
    read_time: Optional[datetime] = None
    
    # Read status
    read: bool = Field(default=False)
    
    # Action
    action_url: Optional[str] = None
    action_taken: bool = Field(default=False)
    
    # Priority
    priority: str = Field(default="normal")  # low, normal, high, urgent
    
    # Delivery attempts
    delivery_attempts: int = Field(default=0)
    last_attempt_time: Optional[datetime] = None
    delivery_error: Optional[str] = None
    
    # Related entity
    related_entity_type: Optional[str] = None  # appointment, prescription, etc.
    related_entity_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "uuid",
                "notification_type": "appointment",
                "title": "Appointment Reminder",
                "message": "Your appointment with Dr. Smith is tomorrow at 10:00 AM",
                "delivery_method": ["in-app", "sms"]
            }
        }

class NotificationPreferences(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: str
    
    # USP: Granular notification control
    appointment_reminders: bool = Field(default=True)
    appointment_reminder_hours: int = Field(default=24)  # Hours before appointment
    
    prescription_refill_reminders: bool = Field(default=True)
    lab_result_notifications: bool = Field(default=True)
    payment_reminders: bool = Field(default=True)
    promotional_notifications: bool = Field(default=False)
    
    # Delivery preferences
    email_notifications: bool = Field(default=True)
    sms_notifications: bool = Field(default=True)
    push_notifications: bool = Field(default=True)
    whatsapp_notifications: bool = Field(default=False)
    
    # Quiet hours
    quiet_hours_enabled: bool = Field(default=False)
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
