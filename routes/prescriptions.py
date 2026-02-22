from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime, timezone, date, timedelta
import uuid
import random
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/prescriptions", tags=["HealthTrack - Prescriptions"])

def generate_prescription_number() -> str:
    return f"RX-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_prescription(
    prescription_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create prescription with USP: follow-up tracking"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Calculate estimated cost
    estimated_cost = 0.0
    if prescription_data.get("medications"):
        for med in prescription_data["medications"]:
            estimated_cost += med.get("quantity", 0) * 10  # Rough estimate
    
    prescription_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "prescription_number": generate_prescription_number(),
        "prescription_date": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "refill_count": 0,
        "max_refills": 0,
        "is_follow_up_prescription": False,
        "estimated_cost": estimated_cost,  # USP: Transparent pricing
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "doctor_signature": f"digital_sig_{user_id}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **prescription_data
    }
    
    # Set valid_until if not provided (30 days default)
    if not prescription_dict.get("valid_until"):
        prescription_dict["valid_until"] = (datetime.now() + timedelta(days=30)).date().isoformat()
    
    await db.healthtrack_prescriptions.insert_one(prescription_dict)
    prescription_dict.pop("_id", None)
    
    return {"message": "Prescription created", "prescription": prescription_dict}

@router.get("")
async def list_prescriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    patient_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List prescriptions"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"organization_id": org["id"]}
    if patient_id:
        query["patient_id"] = patient_id
    if status_filter:
        query["status"] = status_filter
    
    total = await db.healthtrack_prescriptions.count_documents(query)
    
    prescriptions = await db.healthtrack_prescriptions.find(
        query,
        {"_id": 0}
    ).sort("prescription_date", -1).skip(skip).limit(limit).to_list(limit)
    
    return {"total": total, "prescriptions": prescriptions}

@router.get("/{prescription_id}")
async def get_prescription(
    prescription_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get prescription details"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    prescription = await db.healthtrack_prescriptions.find_one(
        {"id": prescription_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not prescription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    
    return prescription

@router.put("/{prescription_id}")
async def update_prescription(
    prescription_id: str,
    prescription_update: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update prescription"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    prescription_update["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.healthtrack_prescriptions.update_one(
        {"id": prescription_id, "organization_id": org["id"]},
        {"$set": prescription_update}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    
    updated = await db.healthtrack_prescriptions.find_one({"id": prescription_id}, {"_id": 0})
    return {"message": "Prescription updated", "prescription": updated}

@router.get("/patient/{patient_id}")
async def get_patient_prescriptions(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all prescriptions for a patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    prescriptions = await db.healthtrack_prescriptions.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("prescription_date", -1).to_list(100)
    
    return {"patient_id": patient_id, "total": len(prescriptions), "prescriptions": prescriptions}

@router.post("/{prescription_id}/refill")
async def request_refill(
    prescription_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Request prescription refill - USP: Follow-up benefits"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    original = await db.healthtrack_prescriptions.find_one(
        {"id": prescription_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    
    if original["refill_count"] >= original["max_refills"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No refills remaining")
    
    # Increment refill count
    await db.healthtrack_prescriptions.update_one(
        {"id": prescription_id},
        {"$inc": {"refill_count": 1}}
    )
    
    return {"message": "Refill requested", "refills_remaining": original["max_refills"] - original["refill_count"] - 1}
