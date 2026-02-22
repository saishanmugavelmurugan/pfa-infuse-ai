from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import uuid

class EmergencyContact(BaseModel):
    name: str
    relationship: str
    phone: str
    email: Optional[EmailStr] = None

class InsuranceInfo(BaseModel):
    provider: str
    policy_number: str
    group_number: Optional[str] = None
    coverage_type: str  # primary, secondary
    valid_from: date
    valid_until: date
    copay_amount: Optional[float] = None

class MedicalHistory(BaseModel):
    chronic_conditions: List[str] = Field(default_factory=list)
    past_surgeries: List[Dict] = Field(default_factory=list)  # {surgery, date, hospital}
    allergies: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    family_history: Dict = Field(default_factory=dict)
    blood_group: Optional[str] = None
    smoking_status: Optional[str] = None
    alcohol_consumption: Optional[str] = None

class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    date_of_birth: date
    gender: str = Field(..., pattern=r'^(male|female|other)$')
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = Field(default="India")
    postal_code: Optional[str] = None

class PatientCreate(PatientBase):
    organization_id: str
    emergency_contact: EmergencyContact
    insurance_info: Optional[InsuranceInfo] = None
    medical_history: Optional[MedicalHistory] = None

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    emergency_contact: Optional[EmergencyContact] = None
    insurance_info: Optional[InsuranceInfo] = None

class Patient(PatientBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    user_id: Optional[str] = None  # Link to users table if patient has login
    patient_number: str  # Auto-generated unique number
    emergency_contact: EmergencyContact
    insurance_info: Optional[InsuranceInfo] = None
    medical_history: MedicalHistory = Field(default_factory=MedicalHistory)
    status: str = Field(default="active")  # active, inactive, deceased
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # user_id of creator
    
    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+919876543210",
                "date_of_birth": "1990-01-15",
                "gender": "male",
                "blood_group": "O+"
            }
        }

class PatientResponse(Patient):
    full_name: str = ""
    age: int = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        self.full_name = f"{self.first_name} {self.last_name}"
        today = datetime.now().date()
        self.age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
