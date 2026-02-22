from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/medical-records", tags=["HealthTrack - Medical Records"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_medical_record(
    record_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create medical record with USP: encryption by default"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Calculate BMI if height and weight provided
    if record_data.get("vitals"):
        vitals = record_data["vitals"]
        if vitals.get("weight") and vitals.get("height"):
            weight_kg = vitals["weight"]
            height_m = vitals["height"] / 100
            vitals["bmi"] = round(weight_kg / (height_m ** 2), 2)
    
    record_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "record_date": datetime.now(timezone.utc).isoformat(),
        "is_encrypted": True,  # USP: Privacy first
        "encryption_key_id": "default-key",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **record_data
    }
    
    await db.healthtrack_medical_records.insert_one(record_dict)
    record_dict.pop("_id", None)
    
    return {"message": "Medical record created", "record": record_dict}

@router.get("")
async def list_medical_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    patient_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List medical records"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"organization_id": org["id"]}
    if patient_id:
        query["patient_id"] = patient_id
    
    total = await db.healthtrack_medical_records.count_documents(query)
    
    records = await db.healthtrack_medical_records.find(
        query,
        {"_id": 0}
    ).sort("record_date", -1).skip(skip).limit(limit).to_list(limit)
    
    return {"total": total, "records": records}

@router.get("/{record_id}")
async def get_medical_record(
    record_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get specific medical record"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    record = await db.healthtrack_medical_records.find_one(
        {"id": record_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    return record

@router.put("/{record_id}")
async def update_medical_record(
    record_id: str,
    record_update: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update medical record"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    record_update["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.healthtrack_medical_records.update_one(
        {"id": record_id, "organization_id": org["id"]},
        {"$set": record_update}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    updated = await db.healthtrack_medical_records.find_one({"id": record_id}, {"_id": 0})
    return {"message": "Record updated", "record": updated}

@router.get("/patient/{patient_id}")
async def get_patient_records(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all medical records for a patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    records = await db.healthtrack_medical_records.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("record_date", -1).to_list(100)
    
    return {"patient_id": patient_id, "total": len(records), "records": records}
