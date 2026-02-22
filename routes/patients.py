from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization, verify_organization_access

router = APIRouter(prefix="/healthtrack/patients", tags=["HealthTrack - Patients"])

# Helper function to generate patient number
def generate_patient_number(org_id: str) -> str:
    """Generate unique patient number: ORG-PAT-XXXXXX"""
    import random
    return f"PAT-{random.randint(100000, 999999)}"

@router.post("", status_code=status.HTTP_201_CREATED)
async def register_patient(
    patient_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Register a new patient"""
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
    existing = await db.healthtrack_patients.find_one(
        {"organization_id": org_id, "email": patient_data["email"]},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient with this email already exists"
        )
    
    # Create patient
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
    
    await db.healthtrack_patients.insert_one(patient_dict)
    
    # Remove MongoDB _id
    patient_dict.pop("_id", None)
    
    return {
        "message": "Patient registered successfully",
        "patient": patient_dict
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
    """List all patients in organization"""
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
    
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"patient_number": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.healthtrack_patients.count_documents(query)
    
    # Get patients
    patients = await db.healthtrack_patients.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "patients": patients
    }

@router.get("/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get patient details"""
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
    
    return patient

@router.put("/{patient_id}")
async def update_patient(
    patient_id: str,
    patient_update: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update patient details"""
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
    
    # Update patient
    patient_update["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.healthtrack_patients.update_one(
        {"id": patient_id},
        {"$set": patient_update}
    )
    
    # Get updated patient
    updated_patient = await db.healthtrack_patients.find_one(
        {"id": patient_id},
        {"_id": 0}
    )
    
    return {"message": "Patient updated successfully", "patient": updated_patient}

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
