from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime, timezone, date
import uuid
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/consents", tags=["HealthTrack - Consent Management"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def record_consent(
    consent_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Record patient consent - USP: Audit trail for compliance"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    consent_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "consent_date": datetime.now(timezone.utc).isoformat(),
        "consent_given": True,
        "withdrawn": False,
        "is_expired": False,
        "consent_version": "1.0",
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **consent_data
    }
    
    await db.healthtrack_consents.insert_one(consent_dict)
    consent_dict.pop("_id", None)
    
    return {"message": "Consent recorded", "consent": consent_dict}

@router.get("/patient/{patient_id}")
async def get_patient_consents(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all consents for a patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    consents = await db.healthtrack_consents.find(
        {"patient_id": patient_id, "organization_id": org["id"]},
        {"_id": 0}
    ).sort("consent_date", -1).to_list(100)
    
    return {"patient_id": patient_id, "total": len(consents), "consents": consents}

@router.put("/{consent_id}/withdraw")
async def withdraw_consent(
    consent_id: str,
    withdrawal_reason: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Withdraw patient consent - USP: Patient data control"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    result = await db.healthtrack_consents.update_one(
        {"id": consent_id, "organization_id": org["id"]},
        {"$set": {
            "withdrawn": True,
            "withdrawn_date": datetime.now(timezone.utc).isoformat(),
            "withdrawal_reason": withdrawal_reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    
    return {"message": "Consent withdrawn successfully"}

@router.get("/forms")
async def get_consent_forms(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get available consent forms"""
    forms = [
        {"type": "treatment", "name": "Treatment Consent", "description": "General treatment consent"},
        {"type": "data-sharing", "name": "Data Sharing Consent", "description": "Consent for sharing medical data"},
        {"type": "telemedicine", "name": "Telemedicine Consent", "description": "Consent for video consultations"},
        {"type": "research", "name": "Research Consent", "description": "Consent for research purposes"},
        {"type": "marketing", "name": "Marketing Consent", "description": "Consent for promotional communications"}
    ]
    return {"forms": forms}

@router.get("/{consent_id}/pdf")
async def download_consent_pdf(
    consent_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Download consent as PDF"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    consent = await db.healthtrack_consents.find_one(
        {"id": consent_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent not found")
    
    return {"message": "PDF generation not implemented", "consent": consent}
