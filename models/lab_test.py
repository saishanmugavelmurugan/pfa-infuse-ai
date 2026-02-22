from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import uuid

class LabTest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    test_name: str = Field(..., min_length=2, max_length=200)
    test_code: str  # Unique identifier
    category: str  # Blood Test, Urine Test, Imaging, etc.
    description: str
    
    # Test requirements
    preparation_required: Optional[str] = None  # e.g., "Fasting for 12 hours"
    sample_type: str  # Blood, Urine, Saliva, etc.
    
    # Normal ranges
    normal_range: Dict = Field(default_factory=dict)  # {male: {min, max, unit}, female: {min, max, unit}}
    
    # USP: Transparent pricing
    price: float = Field(..., ge=0)
    discounted_price: Optional[float] = None
    
    # Timing
    duration_hours: int = Field(default=24)  # Time to get results
    
    # Metadata
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TestItem(BaseModel):
    test_id: str
    test_name: str
    test_code: str
    urgency: str = Field(default="routine", pattern=r'^(routine|urgent|stat)$')
    special_instructions: Optional[str] = None

class LabOrderCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_id: Optional[str] = None
    tests: List[TestItem]
    clinical_notes: Optional[str] = None
    preferred_lab: Optional[str] = None

class LabOrder(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    order_number: str  # Auto-generated
    patient_id: str
    doctor_id: str
    appointment_id: Optional[str] = None
    
    order_date: datetime = Field(default_factory=datetime.utcnow)
    tests: List[TestItem]
    clinical_notes: Optional[str] = None
    
    # Lab details
    lab_name: Optional[str] = None
    preferred_lab: Optional[str] = None
    
    # Status tracking
    status: str = Field(default="ordered")  # ordered, sample-collected, in-progress, completed, cancelled
    sample_collected_at: Optional[datetime] = None
    results_available_at: Optional[datetime] = None
    
    # USP: Transparent pricing
    total_amount: float = Field(default=0.0)
    discount_applied: float = Field(default=0.0)
    final_amount: float = Field(default=0.0)
    payment_status: str = Field(default="pending")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LabResultValue(BaseModel):
    parameter: str
    value: str
    unit: str
    reference_range: str
    status: str = Field(pattern=r'^(normal|abnormal|critical)$')  # normal, abnormal, critical
    remarks: Optional[str] = None

class LabResultCreate(BaseModel):
    lab_order_id: str
    test_id: str
    test_name: str
    results: List[LabResultValue]
    overall_remarks: Optional[str] = None
    technician_name: Optional[str] = None
    verified_by: Optional[str] = None

class LabResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    lab_order_id: str
    patient_id: str
    test_id: str
    test_name: str
    
    result_date: datetime = Field(default_factory=datetime.utcnow)
    results: List[LabResultValue]
    overall_remarks: Optional[str] = None
    
    # Lab information
    lab_name: Optional[str] = None
    technician_name: Optional[str] = None
    verified_by: Optional[str] = None
    
    # Document
    report_url: Optional[str] = None
    
    # USP: Data privacy
    is_encrypted: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
