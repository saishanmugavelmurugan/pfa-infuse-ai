from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
import uuid

class ConsentCreate(BaseModel):
    patient_id: str
    consent_type: str = Field(..., pattern=r'^(treatment|data-sharing|telemedicine|research|marketing)$')
    consent_document_url: Optional[str] = None
    expiry_date: Optional[date] = None

class PatientConsent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    patient_id: str
    
    # Consent details
    consent_type: str  # treatment, data-sharing, telemedicine, research, marketing
    consent_given: bool = Field(default=True)
    consent_date: datetime = Field(default_factory=datetime.utcnow)
    consent_document_url: Optional[str] = None
    
    # Expiry
    expiry_date: Optional[date] = None
    is_expired: bool = Field(default=False)
    
    # Withdrawal
    withdrawn: bool = Field(default=False)
    withdrawn_date: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None
    
    # USP: Audit trail for compliance
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    digital_signature: Optional[str] = None
    
    # Version control
    consent_version: str = Field(default="1.0")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "uuid",
                "consent_type": "treatment",
                "consent_given": True
            }
        }
