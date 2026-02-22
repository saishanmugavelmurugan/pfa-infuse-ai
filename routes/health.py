from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/health", tags=["HealthTrack Pro"])

# Models
class HealthUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class HealthUserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    phone: Optional[str] = None
    address: Optional[str] = None

class HealthRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    health_score: int = Field(..., ge=0, le=100)
    conditions: List[str] = []
    medications: List[str] = []
    last_checkup: str
    notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class HealthRecordCreate(BaseModel):
    user_id: str
    health_score: int = Field(..., ge=0, le=100)
    conditions: List[str] = []
    medications: List[str] = []
    last_checkup: str
    notes: Optional[str] = None

class Doctor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    specialization: str
    practice_type: str = Field(..., pattern="^(ayurvedic|allopathic|both)$")
    email: EmailStr
    phone: str
    license_number: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=2)
    specialization: str
    practice_type: str = Field(..., pattern="^(ayurvedic|allopathic|both)$")
    email: EmailStr
    phone: str
    license_number: str

class BillingRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float = Field(..., ge=0)
    service: str
    status: str = Field(default="pending", pattern="^(pending|paid|cancelled)$")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class BillingRecordCreate(BaseModel):
    user_id: str
    amount: float = Field(..., ge=0)
    service: str
    status: str = Field(default="pending", pattern="^(pending|paid|cancelled)$")

class Medicine(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str = Field(..., pattern="^(ayurvedic|allopathic)$")
    stock: int = Field(..., ge=0)
    price: float = Field(..., ge=0)
    description: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class MedicineCreate(BaseModel):
    name: str = Field(..., min_length=2)
    type: str = Field(..., pattern="^(ayurvedic|allopathic)$")
    stock: int = Field(..., ge=0)
    price: float = Field(..., ge=0)
    description: Optional[str] = None

# Health Users Endpoints
@router.post("/users", response_model=HealthUser, status_code=status.HTTP_201_CREATED)
async def create_health_user(
    user_data: HealthUserCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new health user/patient"""
    user_dict = HealthUser(**user_data.model_dump()).model_dump()
    await db.health_users.insert_one(user_dict)
    return user_dict

@router.get("/users", response_model=List[HealthUser])
async def get_health_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all health users/patients"""
    users = await db.health_users.find({}, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return users

@router.get("/users/{user_id}", response_model=HealthUser)
async def get_health_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific health user/patient"""
    user = await db.health_users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=HealthUser)
async def update_health_user(
    user_id: str,
    user_data: HealthUserCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update a health user/patient"""
    existing_user = await db.health_users.find_one({"id": user_id}, {"_id": 0})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_data = user_data.model_dump()
    updated_data["id"] = user_id
    updated_data["created_at"] = existing_user["created_at"]
    
    await db.health_users.update_one({"id": user_id}, {"$set": updated_data})
    return updated_data

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a health user/patient"""
    result = await db.health_users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

# Health Records Endpoints
@router.post("/records", response_model=HealthRecord, status_code=status.HTTP_201_CREATED)
async def create_health_record(
    record_data: HealthRecordCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new health record"""
    record_dict = HealthRecord(**record_data.model_dump()).model_dump()
    await db.health_records.insert_one(record_dict)
    return record_dict

@router.get("/records")
async def get_health_records(
    user_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get health records, optionally filtered by user_id"""
    query = {"user_id": user_id} if user_id else {}
    records = await db.health_records.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return {"records": records, "count": len(records)}

@router.get("/records/{record_id}", response_model=HealthRecord)
async def get_health_record(
    record_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific health record"""
    record = await db.health_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

# Doctors Endpoints
@router.post("/doctors", response_model=Doctor, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    doctor_data: DoctorCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new doctor"""
    doctor_dict = Doctor(**doctor_data.model_dump()).model_dump()
    await db.doctors.insert_one(doctor_dict)
    return doctor_dict

@router.get("/doctors", response_model=List[Doctor])
async def get_doctors(
    practice_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all doctors, optionally filtered by practice type"""
    query = {"practice_type": practice_type} if practice_type else {}
    doctors = await db.doctors.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return doctors

@router.get("/doctors/{doctor_id}", response_model=Doctor)
async def get_doctor(
    doctor_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific doctor"""
    doctor = await db.doctors.find_one({"id": doctor_id}, {"_id": 0})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

# Billing Endpoints
@router.post("/billing", response_model=BillingRecord, status_code=status.HTTP_201_CREATED)
async def create_billing_record(
    billing_data: BillingRecordCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new billing record"""
    billing_dict = BillingRecord(**billing_data.model_dump()).model_dump()
    await db.billing_records.insert_one(billing_dict)
    return billing_dict

@router.get("/billing", response_model=List[BillingRecord])
async def get_billing_records(
    user_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get billing records"""
    query = {}
    if user_id:
        query["user_id"] = user_id
    if status_filter:
        query["status"] = status_filter
    
    records = await db.billing_records.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return records

class BillingStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|paid|cancelled)$")

@router.put("/billing/{billing_id}/status", response_model=BillingRecord)
async def update_billing_status(
    billing_id: str,
    status_data: BillingStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update billing record status"""
    result = await db.billing_records.update_one(
        {"id": billing_id},
        {"$set": {"status": status_data.status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Billing record not found")
    
    updated_record = await db.billing_records.find_one({"id": billing_id}, {"_id": 0})
    return updated_record

# Medicine Inventory Endpoints
@router.post("/medicines", response_model=Medicine, status_code=status.HTTP_201_CREATED)
async def create_medicine(
    medicine_data: MedicineCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Add a new medicine to inventory"""
    medicine_dict = Medicine(**medicine_data.model_dump()).model_dump()
    await db.medicines.insert_one(medicine_dict)
    return medicine_dict

@router.get("/medicines", response_model=List[Medicine])
async def get_medicines(
    type_filter: Optional[str] = Query(None, alias="type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get medicine inventory"""
    query = {"type": type_filter} if type_filter else {}
    medicines = await db.medicines.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return medicines

class MedicineStockUpdate(BaseModel):
    stock: int = Field(..., ge=0)

@router.put("/medicines/{medicine_id}/stock", response_model=Medicine)
async def update_medicine_stock(
    medicine_id: str,
    stock_data: MedicineStockUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update medicine stock"""
    result = await db.medicines.update_one(
        {"id": medicine_id},
        {"$set": {"stock": stock_data.stock}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    updated_medicine = await db.medicines.find_one({"id": medicine_id}, {"_id": 0})
    return updated_medicine
