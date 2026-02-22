from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import uuid

class InsuranceClaimCreate(BaseModel):
    patient_id: str
    appointment_id: str
    insurance_provider: str
    policy_number: str
    claim_amount: float = Field(..., gt=0)
    documents: List[Dict] = Field(default_factory=list)

class InsuranceClaim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    patient_id: str
    appointment_id: str
    
    # Insurance details
    insurance_provider: str
    policy_number: str
    group_number: Optional[str] = None
    
    # Claim details
    claim_number: str  # Auto-generated
    claim_amount: float
    approved_amount: Optional[float] = None
    patient_copay: float = Field(default=0.0)
    
    # Status
    claim_status: str = Field(default="submitted")  # submitted, under-review, approved, rejected, pending
    
    # Dates
    submitted_date: datetime = Field(default_factory=datetime.utcnow)
    processed_date: Optional[datetime] = None
    
    # Rejection details
    rejection_reason: Optional[str] = None
    
    # Documents
    documents: List[Dict] = Field(default_factory=list)  # {type, url, name}
    
    # USP: Transparent tracking
    status_history: List[Dict] = Field(default_factory=list)  # {status, timestamp, note}
    
    # ICD-10 and CPT codes for claim
    diagnosis_codes: List[str] = Field(default_factory=list)
    procedure_codes: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "insurance_provider": "Star Health Insurance",
                "policy_number": "SH123456789",
                "claim_amount": 5000.0
            }
        }
