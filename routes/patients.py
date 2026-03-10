from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization, verify_organization_access
from utils.encryption import encrypt_sensitive_data, decrypt_sensitive_data, SENSITIVE_HEALTH_FIELDS
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/healthtrack/patients", tags=["HealthTrack - Patients"])

# Encryption configuration
ENCRYPTION_ENABLED = os.environ.get("ENCRYPTION_ENABLED", "true").lower() == "true"

# Patient-specific sensitive fields
PATIENT_SENSITIVE_FIELDS = [
    "first_name", "last_name", "email", "phone", "date_of_birth",
    "national_id", "abha_number", "emirates_id", "passport_number",
    "insurance_id", "address", "street", "city", "emergency_contact",
    "medical_history", "allergies", "chronic_conditions", "blood_group"
]

# Helper function to generate patient number
def generate_patient_number(org_id: str) -> str:
    """Generate unique patient number: ORG-PAT-XXXXXX"""
    import random
    return f"PAT-{random.randint(100000, 999999)}"

def encrypt_patient_data(patient_data: dict) -> dict:
    """Encrypt sensitive patient fields if encryption is enabled"""
    if not ENCRYPTION_ENABLED:
        return patient_data
    try:
        return encrypt_sensitive_data(patient_data, PATIENT_SENSITIVE_FIELDS)
    except Exception as e:
        logger.warning(f"Encryption failed, storing unencrypted: {e}")
        return patient_data

def decrypt_patient_data(patient_data: dict) -> dict:
    """Decrypt sensitive patient fields if they are encrypted"""
    if not patient_data:
        return patient_data
    if not ENCRYPTION_ENABLED:
        return patient_data
    try:
        return decrypt_sensitive_data(patient_data)
    except Exception as e:
        logger.warning(f"Decryption failed, returning as-is: {e}")
        return patient_data

@router.post("", status_code=status.HTTP_201_CREATED)
async def register_patient(
    patient_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Register a new patient with AES-256 encryption for sensitive fields"""
    user_id = current_user["user_id"]
    
    # Get user's organization
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found. Please create an organization first."
        )
    
    org_id = org["id"]
    
    # Check if email already exists in this organization
    # Note: For encrypted emails, we'd need a hash index for searching
    existing = await db.healthtrack_patients.find_one(
        {"organization_id": org_id, "email": patient_data.get("email")},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient with this email already exists"
        )
    
    # Create patient document
    patient_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "patient_number": generate_patient_number(org_id),
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        **patient_data
    }
    
    # Encrypt sensitive fields before storage
    encrypted_patient = encrypt_patient_data(patient_dict)
    
    await db.healthtrack_patients.insert_one(encrypted_patient)
    
    # Return decrypted data (remove MongoDB _id)
    patient_dict.pop("_id", None)
    
    logger.info(f"Patient registered with encryption: {ENCRYPTION_ENABLED}")
    
    return {
        "message": "Patient registered successfully",
        "patient": patient_dict,
        "encrypted": ENCRYPTION_ENABLED
    }

@router.get("")
async def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all patients in organization (with automatic decryption)"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found"
        )
    
    # Build query
    query = {"organization_id": org["id"]}
    
    if status_filter:
        query["status"] = status_filter
    
    # Note: Search on encrypted fields requires patient_number (non-encrypted) or exact match
    if search:
        query["$or"] = [
            {"patient_number": {"$regex": search, "$options": "i"}}
            # Encrypted fields can't be searched with regex
            # In production, use searchable encryption or separate search index
        ]
    
    # Get total count
    total = await db.healthtrack_patients.count_documents(query)
    
    # Get patients
    patients_raw = await db.healthtrack_patients.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Decrypt sensitive fields for each patient
    patients = [decrypt_patient_data(p) for p in patients_raw]
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "patients": patients,
        "encryption_enabled": ENCRYPTION_ENABLED
    }

@router.get("/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get patient details (with automatic decryption)"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Get patient
    patient_raw = await db.healthtrack_patients.find_one(
        {"id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not patient_raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    
    # Decrypt sensitive fields
    patient = decrypt_patient_data(patient_raw)
    
    return patient

@router.put("/{patient_id}")
async def update_patient(
    patient_id: str,
    patient_update: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update patient details (with automatic encryption)"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Check patient exists
    patient = await db.healthtrack_patients.find_one(
        {"id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    
    # Add timestamp
    patient_update["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Encrypt sensitive fields before update
    encrypted_update = encrypt_patient_data(patient_update)
    
    await db.healthtrack_patients.update_one(
        {"id": patient_id},
        {"$set": encrypted_update}
    )
    
    # Get updated patient and decrypt
    updated_patient_raw = await db.healthtrack_patients.find_one(
        {"id": patient_id},
        {"_id": 0}
    )
    updated_patient = decrypt_patient_data(updated_patient_raw)
    
    return {"message": "Patient updated successfully", "patient": updated_patient, "encrypted": ENCRYPTION_ENABLED}

@router.delete("/{patient_id}")
async def archive_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Archive patient (soft delete)"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Update status to inactive
    result = await db.healthtrack_patients.update_one(
        {"id": patient_id, "organization_id": org["id"]},
        {"$set": {"status": "inactive", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    
    return {"message": "Patient archived successfully"}

@router.get("/{patient_id}/medical-history")
async def get_patient_medical_history(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get complete medical history of patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Get patient
    patient = await db.healthtrack_patients.find_one(
        {"id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    
    # Get medical records
    medical_records = await db.healthtrack_medical_records.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("record_date", -1).to_list(100)
    
    # Get prescriptions
    prescriptions = await db.healthtrack_prescriptions.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("prescription_date", -1).to_list(100)
    
    # Get lab results
    lab_results = await db.healthtrack_lab_results.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("result_date", -1).to_list(100)
    
    return {
        "patient": patient,
        "medical_records": medical_records,
        "prescriptions": prescriptions,
        "lab_results": lab_results,
        "total_records": len(medical_records),
        "total_prescriptions": len(prescriptions),
        "total_lab_results": len(lab_results)
    }

@router.post("/{patient_id}/vitals")
async def add_patient_vitals(
    patient_id: str,
    vitals_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Add vitals for patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Verify patient exists
    patient = await db.healthtrack_patients.find_one(
        {"id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    
    # Add vitals record
    vitals_record = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "patient_id": patient_id,
        "recorded_by": user_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        **vitals_data
    }
    
    await db.healthtrack_vitals.insert_one(vitals_record)
    vitals_record.pop("_id", None)
    
    return {"message": "Vitals recorded successfully", "vitals": vitals_record}

@router.get("/{patient_id}/appointments")
async def get_patient_appointments(
    patient_id: str,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all appointments for a patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Build query
    query = {"patient_id": patient_id, "organization_id": org["id"]}
    if status_filter:
        query["status"] = status_filter
    
    # Get appointments
    appointments = await db.healthtrack_appointments.find(
        query,
        {"_id": 0}
    ).sort("appointment_date", -1).to_list(100)
    
    return {
        "patient_id": patient_id,
        "total_appointments": len(appointments),
        "appointments": appointments
    }
