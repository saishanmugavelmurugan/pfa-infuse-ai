"""
Video Consent Management System for HealthTrack Pro
Comprehensive video-based patient consent recording for legal protection

Supports all major consent types used globally:
- Informed Consent (Surgery, Procedures, Treatment)
- Anesthesia Consent
- Blood Transfusion Consent
- High-Risk Procedure Consent
- LAMA (Leaving Against Medical Advice)
- DNR/DNAR (Do Not Resuscitate)
- Organ Donation Consent
- Clinical Trial Consent
- Photography/Recording Consent
- Data Sharing Consent
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4
import os
import base64

from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/video-consent", tags=["HealthTrack - Video Consent"])

# Consent Types - Comprehensive list covering global healthcare standards
CONSENT_TYPES = {
    # Surgical & Procedural Consents
    "surgical": {
        "name": "Surgical Consent",
        "description": "Consent for surgical procedures including risks, benefits, and alternatives",
        "category": "procedural",
        "required_elements": ["procedure_name", "risks", "benefits", "alternatives", "anesthesia_type"],
        "witness_required": True,
        "video_recommended": True
    },
    "anesthesia": {
        "name": "Anesthesia Consent",
        "description": "Consent for administration of anesthesia (general, regional, local)",
        "category": "procedural",
        "required_elements": ["anesthesia_type", "risks", "pre_op_instructions"],
        "witness_required": True,
        "video_recommended": True
    },
    "blood_transfusion": {
        "name": "Blood Transfusion Consent",
        "description": "Consent for blood and blood product transfusion",
        "category": "procedural",
        "required_elements": ["blood_products", "risks", "alternatives", "religious_considerations"],
        "witness_required": True,
        "video_recommended": True
    },
    "invasive_procedure": {
        "name": "Invasive Procedure Consent",
        "description": "Consent for invasive diagnostic or therapeutic procedures",
        "category": "procedural",
        "required_elements": ["procedure_name", "risks", "sedation_type"],
        "witness_required": True,
        "video_recommended": True
    },
    
    # High-Risk Consents
    "high_risk_surgery": {
        "name": "High-Risk Surgery Consent",
        "description": "Enhanced consent for high-risk surgeries with detailed risk disclosure",
        "category": "high_risk",
        "required_elements": ["procedure_name", "mortality_risk", "complication_risks", "alternative_treatments", "second_opinion_offered"],
        "witness_required": True,
        "video_recommended": True
    },
    "experimental_treatment": {
        "name": "Experimental/Off-Label Treatment Consent",
        "description": "Consent for experimental or off-label use of treatments",
        "category": "high_risk",
        "required_elements": ["treatment_name", "experimental_nature", "known_risks", "unknown_risks", "alternative_approved_treatments"],
        "witness_required": True,
        "video_recommended": True
    },
    
    # Emergency & Critical Care Consents
    "emergency_treatment": {
        "name": "Emergency Treatment Consent",
        "description": "Consent for emergency medical treatment",
        "category": "emergency",
        "required_elements": ["emergency_nature", "immediate_risks", "treatment_plan"],
        "witness_required": True,
        "video_recommended": True
    },
    "icu_admission": {
        "name": "ICU Admission Consent",
        "description": "Consent for intensive care unit admission and interventions",
        "category": "critical_care",
        "required_elements": ["icu_interventions", "ventilator_support", "monitoring_procedures"],
        "witness_required": True,
        "video_recommended": True
    },
    "dnr_dnar": {
        "name": "DNR/DNAR Consent",
        "description": "Do Not Resuscitate / Do Not Attempt Resuscitation directive",
        "category": "end_of_life",
        "required_elements": ["patient_wishes", "family_consultation", "physician_discussion", "mental_capacity_assessment"],
        "witness_required": True,
        "video_recommended": True
    },
    "palliative_care": {
        "name": "Palliative Care Consent",
        "description": "Consent for palliative/comfort care measures",
        "category": "end_of_life",
        "required_elements": ["care_goals", "pain_management", "life_sustaining_treatment_preferences"],
        "witness_required": True,
        "video_recommended": True
    },
    
    # Discharge & Refusal Consents
    "lama": {
        "name": "LAMA - Leaving Against Medical Advice",
        "description": "Documentation when patient leaves against medical advice",
        "category": "discharge",
        "required_elements": ["reason_for_leaving", "risks_explained", "follow_up_instructions", "mental_capacity_assessment"],
        "witness_required": True,
        "video_recommended": True
    },
    "treatment_refusal": {
        "name": "Treatment Refusal Consent",
        "description": "Documentation of patient's informed refusal of treatment",
        "category": "refusal",
        "required_elements": ["refused_treatment", "risks_of_refusal", "alternatives_offered", "mental_capacity_assessment"],
        "witness_required": True,
        "video_recommended": True
    },
    "discharge": {
        "name": "Discharge Consent",
        "description": "Consent and acknowledgment at discharge",
        "category": "discharge",
        "required_elements": ["discharge_instructions", "medications", "follow_up_appointments", "warning_signs"],
        "witness_required": False,
        "video_recommended": False
    },
    
    # Specialty Consents
    "maternity": {
        "name": "Maternity/Delivery Consent",
        "description": "Consent for labor, delivery, and potential interventions",
        "category": "specialty",
        "required_elements": ["delivery_plan", "cesarean_consent", "epidural_consent", "emergency_interventions"],
        "witness_required": True,
        "video_recommended": True
    },
    "pediatric": {
        "name": "Pediatric Treatment Consent",
        "description": "Consent for treatment of minors (requires guardian)",
        "category": "specialty",
        "required_elements": ["guardian_relationship", "treatment_plan", "child_assent_if_applicable"],
        "witness_required": True,
        "video_recommended": True
    },
    "psychiatric": {
        "name": "Psychiatric Treatment Consent",
        "description": "Consent for psychiatric treatments including medications and therapy",
        "category": "specialty",
        "required_elements": ["treatment_type", "medications", "side_effects", "ect_if_applicable"],
        "witness_required": True,
        "video_recommended": True
    },
    "organ_donation": {
        "name": "Organ Donation Consent",
        "description": "Consent for organ and tissue donation",
        "category": "specialty",
        "required_elements": ["donation_type", "organs_tissues", "family_wishes"],
        "witness_required": True,
        "video_recommended": True
    },
    
    # Research & Clinical Trials
    "clinical_trial": {
        "name": "Clinical Trial Consent",
        "description": "Informed consent for participation in clinical research",
        "category": "research",
        "required_elements": ["study_purpose", "procedures", "risks", "benefits", "compensation", "withdrawal_rights", "confidentiality"],
        "witness_required": True,
        "video_recommended": True
    },
    "research_participation": {
        "name": "Research Participation Consent",
        "description": "Consent for participation in medical research studies",
        "category": "research",
        "required_elements": ["research_purpose", "data_usage", "privacy_protections"],
        "witness_required": True,
        "video_recommended": False
    },
    
    # Data & Privacy Consents
    "data_sharing": {
        "name": "Data Sharing Consent",
        "description": "Consent for sharing medical data with other providers/systems",
        "category": "privacy",
        "required_elements": ["data_types", "recipients", "purpose", "duration"],
        "witness_required": True,
        "video_recommended": True
    },
    "photography_recording": {
        "name": "Medical Photography/Recording Consent",
        "description": "Consent for medical photography, video, or audio recording",
        "category": "privacy",
        "required_elements": ["recording_type", "purpose", "storage_duration", "usage_scope"],
        "witness_required": True,
        "video_recommended": True
    },
    "telemedicine": {
        "name": "Telemedicine Consent",
        "description": "Consent for receiving healthcare via telemedicine",
        "category": "privacy",
        "required_elements": ["technology_limitations", "privacy_measures", "emergency_protocols"],
        "witness_required": True,
        "video_recommended": True
    },
    
    # General Consents
    "general_treatment": {
        "name": "General Treatment Consent",
        "description": "General consent for routine medical treatment",
        "category": "general",
        "required_elements": ["treatment_scope", "patient_rights", "billing_authorization"],
        "witness_required": True,
        "video_recommended": True
    },
    "admission": {
        "name": "Hospital Admission Consent",
        "description": "Consent upon hospital admission",
        "category": "general",
        "required_elements": ["admission_reason", "treatment_team", "patient_rights", "valuables_policy"],
        "witness_required": True,
        "video_recommended": True
    }
}

# Models
class VideoConsentCreate(BaseModel):
    patient_id: str
    consent_type: str = Field(..., description="Type of consent from CONSENT_TYPES")
    procedure_name: Optional[str] = None
    procedure_date: Optional[str] = None
    attending_physician: str
    witness_name: Optional[str] = None
    witness_relationship: Optional[str] = None
    interpreter_used: bool = False
    interpreter_language: Optional[str] = None
    patient_language: str = "English"
    mental_capacity_confirmed: bool = True
    risks_explained: List[str] = []
    benefits_explained: List[str] = []
    alternatives_explained: List[str] = []
    questions_answered: bool = True
    patient_questions: Optional[str] = None
    additional_notes: Optional[str] = None

class VideoConsentResponse(BaseModel):
    id: str
    patient_id: str
    consent_type: str
    consent_type_details: dict
    status: str
    video_url: Optional[str]
    created_at: str

@router.get("/types")
async def get_consent_types():
    """Get all available consent types with their requirements"""
    categories = {}
    for key, value in CONSENT_TYPES.items():
        cat = value["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "type": key,
            **value
        })
    
    return {
        "total_types": len(CONSENT_TYPES),
        "categories": categories,
        "consent_types": CONSENT_TYPES
    }

@router.get("/types/{consent_type}")
async def get_consent_type_details(consent_type: str):
    """Get detailed requirements for a specific consent type"""
    if consent_type not in CONSENT_TYPES:
        raise HTTPException(status_code=404, detail=f"Consent type '{consent_type}' not found")
    
    return {
        "type": consent_type,
        **CONSENT_TYPES[consent_type]
    }

@router.post("/record")
async def record_video_consent(
    consent_data: VideoConsentCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new video consent record (video to be uploaded separately)"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    if consent_data.consent_type not in CONSENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid consent type: {consent_data.consent_type}")
    
    consent_type_info = CONSENT_TYPES[consent_data.consent_type]
    
    # Generate unique consent ID
    consent_id = f"VCS-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    consent_record = {
        "id": consent_id,
        "organization_id": org["id"],
        "patient_id": consent_data.patient_id,
        "consent_type": consent_data.consent_type,
        "consent_type_name": consent_type_info["name"],
        "consent_type_category": consent_type_info["category"],
        "procedure_name": consent_data.procedure_name,
        "procedure_date": consent_data.procedure_date,
        "attending_physician": consent_data.attending_physician,
        "witness_name": consent_data.witness_name,
        "witness_relationship": consent_data.witness_relationship,
        "interpreter_used": consent_data.interpreter_used,
        "interpreter_language": consent_data.interpreter_language,
        "patient_language": consent_data.patient_language,
        "mental_capacity_confirmed": consent_data.mental_capacity_confirmed,
        "risks_explained": consent_data.risks_explained,
        "benefits_explained": consent_data.benefits_explained,
        "alternatives_explained": consent_data.alternatives_explained,
        "questions_answered": consent_data.questions_answered,
        "patient_questions": consent_data.patient_questions,
        "additional_notes": consent_data.additional_notes,
        "video_recorded": False,
        "video_url": None,
        "video_duration_seconds": None,
        "video_file_size": None,
        "video_recorded_at": None,
        "status": "pending_video",
        "legally_valid": False,
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.video_consents.insert_one(consent_record)
    consent_record.pop("_id", None)
    
    return {
        "message": "Consent record created. Please upload video to complete.",
        "consent_id": consent_id,
        "consent": consent_record,
        "next_step": f"POST /api/healthtrack/video-consent/{consent_id}/upload-video"
    }

@router.post("/{consent_id}/upload-video")
async def upload_consent_video(
    consent_id: str,
    video: UploadFile = File(...),
    duration_seconds: int = Form(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Upload video recording for a consent record"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    # Find consent record
    consent = await db.video_consents.find_one({
        "id": consent_id,
        "organization_id": org["id"]
    })
    
    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")
    
    # Read video content
    video_content = await video.read()
    video_size = len(video_content)
    
    # Store video (in production, use cloud storage like S3)
    # For now, store as base64 in database (not recommended for production)
    video_b64 = base64.b64encode(video_content).decode('utf-8')
    
    # Create video storage record
    video_storage = {
        "id": str(uuid4()),
        "consent_id": consent_id,
        "organization_id": org["id"],
        "filename": video.filename,
        "content_type": video.content_type,
        "size_bytes": video_size,
        "video_data": video_b64,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.consent_videos.insert_one(video_storage)
    
    # Update consent record
    await db.video_consents.update_one(
        {"id": consent_id},
        {"$set": {
            "video_recorded": True,
            "video_url": f"/api/healthtrack/video-consent/{consent_id}/video",
            "video_duration_seconds": duration_seconds,
            "video_file_size": video_size,
            "video_filename": video.filename,
            "video_recorded_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "legally_valid": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Video consent recorded successfully",
        "consent_id": consent_id,
        "video_size_mb": round(video_size / (1024 * 1024), 2),
        "duration_seconds": duration_seconds,
        "status": "completed",
        "legally_valid": True
    }

@router.get("/{consent_id}/video")
async def get_consent_video(
    consent_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Stream consent video"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    video_record = await db.consent_videos.find_one({
        "consent_id": consent_id,
        "organization_id": org["id"]
    })
    
    if not video_record:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_data = base64.b64decode(video_record["video_data"])
    
    def video_stream():
        yield video_data
    
    return StreamingResponse(
        video_stream(),
        media_type=video_record.get("content_type", "video/webm"),
        headers={
            "Content-Disposition": f"inline; filename={video_record.get('filename', 'consent_video.webm')}"
        }
    )

@router.get("/patient/{patient_id}")
async def get_patient_video_consents(
    patient_id: str,
    consent_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all video consents for a patient"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    query = {
        "patient_id": patient_id,
        "organization_id": org["id"]
    }
    
    if consent_type:
        query["consent_type"] = consent_type
    if status:
        query["status"] = status
    
    consents = await db.video_consents.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "patient_id": patient_id,
        "total": len(consents),
        "consents": consents
    }

@router.get("/{consent_id}")
async def get_video_consent(
    consent_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific video consent record"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    consent = await db.video_consents.find_one(
        {"id": consent_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    
    # Add consent type details
    consent["consent_type_details"] = CONSENT_TYPES.get(consent["consent_type"], {})
    
    return consent

@router.get("/")
async def list_video_consents(
    status: Optional[str] = None,
    consent_type: Optional[str] = None,
    from_date: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all video consents for the organization"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    query = {"organization_id": org["id"]}
    
    if status:
        query["status"] = status
    if consent_type:
        query["consent_type"] = consent_type
    if from_date:
        query["created_at"] = {"$gte": from_date}
    
    consents = await db.video_consents.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Get statistics
    total_count = await db.video_consents.count_documents({"organization_id": org["id"]})
    pending_count = await db.video_consents.count_documents({"organization_id": org["id"], "status": "pending_video"})
    completed_count = await db.video_consents.count_documents({"organization_id": org["id"], "status": "completed"})
    
    return {
        "total": len(consents),
        "statistics": {
            "total_consents": total_count,
            "pending_video": pending_count,
            "completed": completed_count
        },
        "consents": consents
    }

@router.delete("/{consent_id}")
async def delete_video_consent(
    consent_id: str,
    reason: str = Query(..., description="Reason for deletion"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a video consent record (for administrative purposes only)"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    # Soft delete - mark as deleted but keep for audit
    result = await db.video_consents.update_one(
        {"id": consent_id, "organization_id": org["id"]},
        {"$set": {
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": user_id,
            "deletion_reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Consent not found")
    
    return {"message": "Consent record marked as deleted", "consent_id": consent_id}

@router.post("/{consent_id}/verify")
async def verify_video_consent(
    consent_id: str,
    verification_notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Mark a video consent as verified by medical/legal team"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="No organization found")
    
    result = await db.video_consents.update_one(
        {"id": consent_id, "organization_id": org["id"], "status": "completed"},
        {"$set": {
            "verified": True,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "verified_by": user_id,
            "verification_notes": verification_notes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Consent not found or not in completed status")
    
    return {"message": "Consent verified successfully", "consent_id": consent_id}
