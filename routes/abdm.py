"""ABDM (Ayushman Bharat Digital Mission) Integration Module

This module provides integration with India's national digital health ecosystem:
- ABHA (Ayushman Bharat Health Account) ID creation/verification
- Health Information Exchange
- Consent Management
- FHIR-based data standards
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone
from uuid import uuid4
import os
import httpx

router = APIRouter(prefix="/abdm", tags=["ABDM Integration"])

# Database dependency
async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'test_database')]

# ABDM Configuration
ABDM_SANDBOX_URL = "https://dev.abdm.gov.in/api"
ABDM_PRODUCTION_URL = "https://healthidsbx.abdm.gov.in/api"

# Use sandbox by default
ABDM_BASE_URL = os.environ.get('ABDM_BASE_URL', ABDM_SANDBOX_URL)
ABDM_CLIENT_ID = os.environ.get('ABDM_CLIENT_ID', '')
ABDM_CLIENT_SECRET = os.environ.get('ABDM_CLIENT_SECRET', '')

# Pydantic Models
class ABHARegistrationRequest(BaseModel):
    first_name: str = Field(..., min_length=1)
    middle_name: Optional[str] = None
    last_name: str = Field(..., min_length=1)
    date_of_birth: str  # YYYY-MM-DD format
    gender: str  # M, F, O
    mobile: str = Field(..., pattern=r'^[6-9]\d{9}$')
    email: Optional[str] = None
    address: Optional[Dict] = None
    aadhaar_number: Optional[str] = None  # Last 4 digits only for verification

class ABHAVerificationRequest(BaseModel):
    abha_number: str
    otp: str
    txn_id: str

class ABHALinkRequest(BaseModel):
    patient_id: str
    abha_number: str
    abha_address: str  # e.g., user@abdm

class ConsentRequest(BaseModel):
    patient_id: str
    purpose: str  # CAREMGT, BTG, PUBHLTH, etc.
    hi_types: List[str]  # OPConsultation, Prescription, DiagnosticReport, etc.
    date_range_from: str
    date_range_to: str
    requester_name: str
    requester_type: str  # HIP, HIU

class HealthRecordPush(BaseModel):
    patient_id: str
    record_type: str  # OPConsultation, Prescription, DiagnosticReport
    record_data: Dict
    consent_id: Optional[str] = None

# Helper functions
async def get_abdm_access_token():
    """Get access token from ABDM gateway"""
    if not ABDM_CLIENT_ID or not ABDM_CLIENT_SECRET:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ABDM_BASE_URL}/v1/auth/cert",
                json={
                    "clientId": ABDM_CLIENT_ID,
                    "clientSecret": ABDM_CLIENT_SECRET
                }
            )
            if response.status_code == 200:
                return response.json().get('accessToken')
    except Exception as e:
        print(f"ABDM auth error: {e}")
    return None

# API Endpoints

@router.get("/status")
async def get_abdm_status():
    """Check ABDM integration status"""
    has_credentials = bool(ABDM_CLIENT_ID and ABDM_CLIENT_SECRET)
    
    return {
        "abdm_enabled": has_credentials,
        "environment": "sandbox" if "dev" in ABDM_BASE_URL else "production",
        "features": {
            "abha_registration": True,
            "abha_verification": True,
            "health_records": True,
            "consent_management": True,
            "data_exchange": True
        },
        "supported_hi_types": [
            "OPConsultation",
            "Prescription",
            "DiagnosticReport",
            "DischargeSummary",
            "ImmunizationRecord",
            "HealthDocumentRecord",
            "WellnessRecord"
        ]
    }

@router.post("/abha/generate-otp")
async def generate_abha_otp(mobile: str = Query(..., pattern=r'^[6-9]\d{9}$')):
    """Generate OTP for ABHA registration/verification"""
    # In production, this would call ABDM API
    # For demo, we simulate the response
    txn_id = str(uuid4())
    
    return {
        "txn_id": txn_id,
        "message": "OTP sent successfully to mobile number",
        "otp_valid_minutes": 10,
        "demo_mode": True,
        "demo_otp": "123456"  # Only for demo/sandbox
    }

@router.post("/abha/verify-otp")
async def verify_abha_otp(mobile: str, otp: str, txn_id: str):
    """Verify OTP for ABHA operations"""
    # Demo mode verification
    if otp == "123456":
        return {
            "verified": True,
            "txn_id": txn_id,
            "message": "OTP verified successfully"
        }
    
    raise HTTPException(status_code=400, detail="Invalid OTP")

@router.post("/abha/register")
async def register_abha(request: ABHARegistrationRequest):
    """Register a new ABHA (Ayushman Bharat Health Account)"""
    db = await get_db()
    
    # Generate demo ABHA number (14 digits)
    abha_number = f"91-{request.mobile[:4]}-{request.mobile[4:8]}-{str(uuid4())[:4]}"
    abha_address = f"{request.first_name.lower()}{request.mobile[-4:]}@abdm"
    
    abha_record = {
        "id": str(uuid4()),
        "abha_number": abha_number,
        "abha_address": abha_address,
        "first_name": request.first_name,
        "middle_name": request.middle_name,
        "last_name": request.last_name,
        "full_name": f"{request.first_name} {request.middle_name or ''} {request.last_name}".strip(),
        "date_of_birth": request.date_of_birth,
        "gender": request.gender,
        "mobile": request.mobile,
        "email": request.email,
        "address": request.address,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "kycVerified": False,
        "profile_photo": None
    }
    
    await db.abdm_abha_records.insert_one(abha_record)
    
    return {
        "success": True,
        "abha_number": abha_number,
        "abha_address": abha_address,
        "message": "ABHA created successfully",
        "profile": {
            "name": abha_record["full_name"],
            "dob": request.date_of_birth,
            "gender": request.gender
        }
    }

@router.get("/abha/search")
async def search_abha(
    mobile: Optional[str] = None,
    abha_number: Optional[str] = None,
    abha_address: Optional[str] = None
):
    """Search for ABHA by mobile, number, or address"""
    db = await get_db()
    
    query = {}
    if mobile:
        query["mobile"] = mobile
    elif abha_number:
        query["abha_number"] = abha_number
    elif abha_address:
        query["abha_address"] = abha_address
    else:
        raise HTTPException(status_code=400, detail="Provide mobile, abha_number, or abha_address")
    
    record = await db.abdm_abha_records.find_one(query, {"_id": 0})
    
    if not record:
        return {"found": False, "message": "No ABHA found with provided details"}
    
    return {
        "found": True,
        "abha": {
            "abha_number": record["abha_number"],
            "abha_address": record["abha_address"],
            "name": record["full_name"],
            "gender": record["gender"],
            "status": record["status"]
        }
    }

@router.post("/abha/link-patient")
async def link_abha_to_patient(request: ABHALinkRequest):
    """Link ABHA to a patient record in the system"""
    db = await get_db()
    
    # Update patient record
    result = await db.healthtrack_patients.update_one(
        {"id": request.patient_id},
        {
            "$set": {
                "abha_number": request.abha_number,
                "abha_address": request.abha_address,
                "abdm_linked": True,
                "abdm_linked_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Create link record
    link_record = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "abha_number": request.abha_number,
        "abha_address": request.abha_address,
        "linked_at": datetime.now(timezone.utc).isoformat(),
        "status": "active"
    }
    await db.abdm_patient_links.insert_one(link_record)
    
    return {
        "success": True,
        "message": "ABHA linked to patient successfully",
        "link_id": link_record["id"]
    }

@router.get("/abha/patient/{patient_id}")
async def get_patient_abha(patient_id: str):
    """Get ABHA details for a patient"""
    db = await get_db()
    
    patient = await db.healthtrack_patients.find_one(
        {"id": patient_id},
        {"_id": 0, "abha_number": 1, "abha_address": 1, "abdm_linked": 1}
    )
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    if not patient.get("abdm_linked"):
        return {"linked": False, "message": "No ABHA linked to this patient"}
    
    # Get full ABHA details
    abha = await db.abdm_abha_records.find_one(
        {"abha_number": patient["abha_number"]},
        {"_id": 0}
    )
    
    return {
        "linked": True,
        "abha_number": patient["abha_number"],
        "abha_address": patient["abha_address"],
        "details": abha
    }

# Consent Management

@router.post("/consent/request")
async def create_consent_request(request: ConsentRequest):
    """Create a consent request for health data access"""
    db = await get_db()
    
    consent_record = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "purpose": request.purpose,
        "hi_types": request.hi_types,
        "date_range": {
            "from": request.date_range_from,
            "to": request.date_range_to
        },
        "requester": {
            "name": request.requester_name,
            "type": request.requester_type
        },
        "status": "REQUESTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
        "granted_at": None,
        "revoked_at": None
    }
    
    await db.abdm_consent_requests.insert_one(consent_record)
    
    return {
        "consent_id": consent_record["id"],
        "status": "REQUESTED",
        "message": "Consent request created. Awaiting patient approval."
    }

@router.get("/consent/patient/{patient_id}")
async def get_patient_consents(patient_id: str):
    """Get all consent requests for a patient"""
    db = await get_db()
    
    consents = await db.abdm_consent_requests.find(
        {"patient_id": patient_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {
        "patient_id": patient_id,
        "total": len(consents),
        "consents": consents
    }

@router.post("/consent/{consent_id}/approve")
async def approve_consent(consent_id: str):
    """Approve a consent request (patient action)"""
    db = await get_db()
    
    result = await db.abdm_consent_requests.update_one(
        {"id": consent_id, "status": "REQUESTED"},
        {
            "$set": {
                "status": "GRANTED",
                "granted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Consent request not found or already processed")
    
    return {"success": True, "status": "GRANTED", "message": "Consent approved"}

@router.post("/consent/{consent_id}/deny")
async def deny_consent(consent_id: str):
    """Deny a consent request (patient action)"""
    db = await get_db()
    
    result = await db.abdm_consent_requests.update_one(
        {"id": consent_id, "status": "REQUESTED"},
        {
            "$set": {
                "status": "DENIED",
                "denied_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Consent request not found or already processed")
    
    return {"success": True, "status": "DENIED", "message": "Consent denied"}

@router.post("/consent/{consent_id}/revoke")
async def revoke_consent(consent_id: str):
    """Revoke a previously granted consent (patient action)"""
    db = await get_db()
    
    result = await db.abdm_consent_requests.update_one(
        {"id": consent_id, "status": "GRANTED"},
        {
            "$set": {
                "status": "REVOKED",
                "revoked_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Active consent not found")
    
    return {"success": True, "status": "REVOKED", "message": "Consent revoked"}

# Health Records (FHIR-based)

@router.post("/health-records/push")
async def push_health_record(request: HealthRecordPush):
    """Push health record to ABDM (HIP flow)"""
    db = await get_db()
    
    # Verify patient has linked ABHA
    patient = await db.healthtrack_patients.find_one(
        {"id": request.patient_id, "abdm_linked": True}
    )
    
    if not patient:
        raise HTTPException(status_code=400, detail="Patient not linked to ABDM")
    
    # Create FHIR bundle
    fhir_bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": [
            {
                "resource": {
                    "resourceType": map_record_type_to_fhir(request.record_type),
                    "id": str(uuid4()),
                    "status": "final",
                    "subject": {
                        "reference": f"Patient/{request.patient_id}",
                        "display": f"{patient.get('first_name', '')} {patient.get('last_name', '')}"
                    },
                    **request.record_data
                }
            }
        ]
    }
    
    # Store record
    record = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "abha_number": patient["abha_number"],
        "record_type": request.record_type,
        "fhir_bundle": fhir_bundle,
        "consent_id": request.consent_id,
        "pushed_at": datetime.now(timezone.utc).isoformat(),
        "status": "pushed"
    }
    
    await db.abdm_health_records.insert_one(record)
    
    return {
        "success": True,
        "record_id": record["id"],
        "fhir_bundle_id": fhir_bundle["id"],
        "message": "Health record pushed to ABDM successfully"
    }

@router.get("/health-records/patient/{patient_id}")
async def get_patient_health_records(
    patient_id: str,
    record_type: Optional[str] = None
):
    """Get health records for a patient from ABDM"""
    db = await get_db()
    
    query = {"patient_id": patient_id}
    if record_type:
        query["record_type"] = record_type
    
    records = await db.abdm_health_records.find(
        query,
        {"_id": 0, "fhir_bundle": 0}  # Exclude large FHIR bundles from list
    ).sort("pushed_at", -1).to_list(100)
    
    return {
        "patient_id": patient_id,
        "total": len(records),
        "records": records
    }

@router.get("/health-records/{record_id}")
async def get_health_record(record_id: str):
    """Get full health record including FHIR bundle"""
    db = await get_db()
    
    record = await db.abdm_health_records.find_one(
        {"id": record_id},
        {"_id": 0}
    )
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return record

# Helper function
def map_record_type_to_fhir(record_type: str) -> str:
    """Map internal record types to FHIR resource types"""
    mapping = {
        "OPConsultation": "Encounter",
        "Prescription": "MedicationRequest",
        "DiagnosticReport": "DiagnosticReport",
        "DischargeSummary": "Composition",
        "ImmunizationRecord": "Immunization",
        "HealthDocumentRecord": "DocumentReference",
        "WellnessRecord": "Observation"
    }
    return mapping.get(record_type, "DocumentReference")

# Facility Registration

@router.get("/facility/info")
async def get_facility_info():
    """Get HIP (Health Information Provider) facility information"""
    return {
        "facility_id": "INFUSE-AI-HIP-001",
        "name": "Infuse-AI HealthTrack Pro",
        "type": "HIP",  # Health Information Provider
        "address": {
            "line": "Digital Healthcare Platform",
            "city": "Pan India",
            "state": "All States",
            "country": "India"
        },
        "capabilities": [
            "ABHA_CREATION",
            "ABHA_LINKING",
            "CONSENT_MANAGEMENT",
            "HEALTH_RECORD_PUSH",
            "FHIR_R4_SUPPORT"
        ],
        "supported_hi_types": [
            "OPConsultation",
            "Prescription",
            "DiagnosticReport",
            "DischargeSummary",
            "ImmunizationRecord",
            "HealthDocumentRecord",
            "WellnessRecord"
        ],
        "abdm_registered": True
    }

# =====================================================
# PHASE 2B: National Health Records & Ayushman Bharat
# =====================================================

# Pydantic Models for Phase 2B
class HealthRecordFetchRequest(BaseModel):
    patient_id: str
    abha_number: str
    consent_id: str
    hi_types: List[str] = ["OPConsultation", "Prescription", "DiagnosticReport"]
    date_from: Optional[str] = None
    date_to: Optional[str] = None

class EligibilityCheckRequest(BaseModel):
    patient_id: str
    abha_number: Optional[str] = None
    scheme: str = "PMJAY"  # Pradhan Mantri Jan Arogya Yojana
    aadhaar_last_4: Optional[str] = None
    ration_card_number: Optional[str] = None

class ClaimSubmissionRequest(BaseModel):
    patient_id: str
    abha_number: str
    claim_type: str  # preauth, claim, enhancement
    hospital_code: str = "INFUSE-AI-HIP-001"
    diagnosis_codes: List[str]  # ICD-10 codes
    procedure_codes: List[str]  # Procedure codes
    package_code: str  # HBP package code
    package_name: str
    estimated_amount: float
    treatment_details: Dict
    documents: Optional[List[Dict]] = None

class ClaimUpdateRequest(BaseModel):
    status: str
    remarks: Optional[str] = None
    approved_amount: Optional[float] = None

# National Health Record Access (HIU Flow)

@router.post("/health-records/fetch")
async def fetch_national_health_records(request: HealthRecordFetchRequest):
    """
    Fetch health records from National Health Stack (other HIPs)
    This initiates a data fetch request through ABDM gateway
    """
    db = await get_db()
    
    # Verify patient and consent
    patient = await db.healthtrack_patients.find_one(
        {"id": request.patient_id, "abha_number": request.abha_number}
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or ABHA mismatch")
    
    consent = await db.abdm_consent_requests.find_one(
        {"id": request.consent_id, "status": "GRANTED"}
    )
    if not consent:
        raise HTTPException(status_code=400, detail="Valid consent required")
    
    # Create fetch request record
    fetch_request = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "abha_number": request.abha_number,
        "consent_id": request.consent_id,
        "hi_types": request.hi_types,
        "date_range": {
            "from": request.date_from or consent["date_range"]["from"],
            "to": request.date_to or consent["date_range"]["to"]
        },
        "status": "REQUESTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "records_received": [],
        "hip_ids": []  # Will be populated with responding HIPs
    }
    
    await db.abdm_fetch_requests.insert_one(fetch_request)
    
    # Demo: Simulate receiving records from other facilities
    demo_records = generate_demo_national_records(request.patient_id, request.hi_types)
    
    # Update with demo records
    await db.abdm_fetch_requests.update_one(
        {"id": fetch_request["id"]},
        {
            "$set": {
                "status": "COMPLETED",
                "records_received": demo_records,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "hip_ids": ["AIIMS-DEL-001", "SAFDARJUNG-001", "APOLLO-BLR-001"]
            }
        }
    )
    
    return {
        "fetch_id": fetch_request["id"],
        "status": "COMPLETED",
        "records_count": len(demo_records),
        "records": demo_records,
        "source_facilities": ["AIIMS Delhi", "Safdarjung Hospital", "Apollo Bangalore"],
        "message": "Health records fetched successfully (Demo Mode)"
    }

@router.get("/health-records/national/{patient_id}")
async def get_national_health_records(patient_id: str):
    """Get all fetched national health records for a patient"""
    db = await get_db()
    
    fetch_requests = await db.abdm_fetch_requests.find(
        {"patient_id": patient_id, "status": "COMPLETED"},
        {"_id": 0}
    ).sort("completed_at", -1).to_list(50)
    
    all_records = []
    for req in fetch_requests:
        all_records.extend(req.get("records_received", []))
    
    return {
        "patient_id": patient_id,
        "total_records": len(all_records),
        "fetch_requests": len(fetch_requests),
        "records": all_records
    }

# Ayushman Bharat Eligibility Verification

@router.post("/ayushman/eligibility/check")
async def check_ayushman_eligibility(request: EligibilityCheckRequest):
    """
    Check patient eligibility for Ayushman Bharat (PMJAY) scheme
    """
    db = await get_db()
    
    # Get patient details
    patient = await db.healthtrack_patients.find_one({"id": request.patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Demo: Check eligibility based on mock data
    # In production, this would call PMJAY API
    eligibility_result = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "abha_number": request.abha_number or patient.get("abha_number"),
        "scheme": request.scheme,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "is_eligible": True,  # Demo: Always eligible
        "eligibility_details": {
            "beneficiary_id": f"PMJAY{str(uuid4())[:8].upper()}",
            "card_number": f"AB{patient.get('mobile', '0000000000')[-6:]}",
            "family_id": f"FAM{str(uuid4())[:6].upper()}",
            "category": "BPL",  # Below Poverty Line
            "state": patient.get("address", {}).get("state", "Delhi"),
            "district": patient.get("address", {}).get("city", "New Delhi"),
            "valid_from": "2024-01-01",
            "valid_until": "2025-12-31",
            "coverage_amount": 500000,  # Rs. 5 Lakhs per family per year
            "remaining_amount": 450000
        },
        "covered_packages": [
            {"code": "HBP-01", "name": "General Medicine", "limit": 50000},
            {"code": "HBP-02", "name": "General Surgery", "limit": 100000},
            {"code": "HBP-03", "name": "Cardiology", "limit": 200000},
            {"code": "HBP-04", "name": "Orthopedics", "limit": 150000},
            {"code": "HBP-05", "name": "Gynecology", "limit": 100000}
        ],
        "demo_mode": True
    }
    
    # Store eligibility record (make a copy to avoid _id issues)
    await db.abdm_eligibility_records.insert_one({**eligibility_result})
    
    return eligibility_result

@router.get("/ayushman/eligibility/{patient_id}")
async def get_eligibility_status(patient_id: str):
    """Get cached eligibility status for a patient"""
    db = await get_db()
    
    eligibility = await db.abdm_eligibility_records.find_one(
        {"patient_id": patient_id},
        {"_id": 0}
    )
    
    if not eligibility:
        return {"patient_id": patient_id, "checked": False, "message": "Eligibility not checked yet"}
    
    return eligibility

# Claims Management

@router.post("/ayushman/claims/submit")
async def submit_claim(request: ClaimSubmissionRequest):
    """
    Submit a claim to Ayushman Bharat (PMJAY)
    Supports: preauth (pre-authorization), claim, enhancement
    """
    db = await get_db()
    
    # Verify eligibility first
    eligibility = await db.abdm_eligibility_records.find_one(
        {"patient_id": request.patient_id, "is_eligible": True}
    )
    if not eligibility:
        raise HTTPException(status_code=400, detail="Patient not eligible for PMJAY")
    
    claim_record = {
        "id": str(uuid4()),
        "claim_number": f"CLM{datetime.now().strftime('%Y%m%d')}{str(uuid4())[:6].upper()}",
        "patient_id": request.patient_id,
        "abha_number": request.abha_number,
        "beneficiary_id": eligibility["eligibility_details"]["beneficiary_id"],
        "claim_type": request.claim_type,
        "hospital_code": request.hospital_code,
        "diagnosis": {
            "codes": request.diagnosis_codes,
            "primary": request.diagnosis_codes[0] if request.diagnosis_codes else None
        },
        "procedures": request.procedure_codes,
        "package": {
            "code": request.package_code,
            "name": request.package_name
        },
        "amounts": {
            "estimated": request.estimated_amount,
            "approved": None,
            "settled": None
        },
        "treatment_details": request.treatment_details,
        "documents": request.documents or [],
        "status": "SUBMITTED",
        "status_history": [
            {
                "status": "SUBMITTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "remarks": "Claim submitted for processing"
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "demo_mode": True
    }
    
    await db.abdm_claims.insert_one(claim_record)
    
    # Demo: Auto-approve preauth requests
    if request.claim_type == "preauth":
        await db.abdm_claims.update_one(
            {"id": claim_record["id"]},
            {
                "$set": {
                    "status": "APPROVED",
                    "amounts.approved": request.estimated_amount * 0.9,  # 90% approval
                    "updated_at": datetime.now(timezone.utc).isoformat()
                },
                "$push": {
                    "status_history": {
                        "status": "APPROVED",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "remarks": "Pre-authorization approved (Demo)"
                    }
                }
            }
        )
        claim_record["status"] = "APPROVED"
        claim_record["amounts"]["approved"] = request.estimated_amount * 0.9
    
    return {
        "success": True,
        "claim_id": claim_record["id"],
        "claim_number": claim_record["claim_number"],
        "status": claim_record["status"],
        "message": f"{request.claim_type.title()} submitted successfully"
    }

@router.get("/ayushman/claims/patient/{patient_id}")
async def get_patient_claims(patient_id: str, status: Optional[str] = None):
    """Get all claims for a patient"""
    db = await get_db()
    
    query = {"patient_id": patient_id}
    if status:
        query["status"] = status.upper()
    
    claims = await db.abdm_claims.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Calculate summary
    summary = {
        "total_claims": len(claims),
        "by_status": {},
        "total_estimated": 0,
        "total_approved": 0,
        "total_settled": 0
    }
    
    for claim in claims:
        status = claim["status"]
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        summary["total_estimated"] += claim["amounts"].get("estimated", 0)
        summary["total_approved"] += claim["amounts"].get("approved", 0) or 0
        summary["total_settled"] += claim["amounts"].get("settled", 0) or 0
    
    return {
        "patient_id": patient_id,
        "summary": summary,
        "claims": claims
    }

@router.get("/ayushman/claims/{claim_id}")
async def get_claim_details(claim_id: str):
    """Get detailed claim information"""
    db = await get_db()
    
    claim = await db.abdm_claims.find_one({"id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return claim

@router.put("/ayushman/claims/{claim_id}/update")
async def update_claim_status(claim_id: str, request: ClaimUpdateRequest):
    """Update claim status (for demo/admin purposes)"""
    db = await get_db()
    
    update_data = {
        "status": request.status.upper(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if request.approved_amount is not None:
        update_data["amounts.approved"] = request.approved_amount
    
    if request.status.upper() == "SETTLED" and request.approved_amount:
        update_data["amounts.settled"] = request.approved_amount
    
    result = await db.abdm_claims.update_one(
        {"id": claim_id},
        {
            "$set": update_data,
            "$push": {
                "status_history": {
                    "status": request.status.upper(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "remarks": request.remarks or f"Status updated to {request.status}"
                }
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    return {"success": True, "status": request.status.upper()}

@router.get("/ayushman/claims/dashboard/summary")
async def get_claims_dashboard_summary():
    """Get claims dashboard summary for the facility"""
    db = await get_db()
    
    # Aggregate claims data
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amounts.estimated"},
                "approved_amount": {"$sum": {"$ifNull": ["$amounts.approved", 0]}}
            }
        }
    ]
    
    results = await db.abdm_claims.aggregate(pipeline).to_list(20)
    
    summary = {
        "total_claims": 0,
        "total_estimated_amount": 0,
        "total_approved_amount": 0,
        "by_status": {},
        "recent_claims": []
    }
    
    for r in results:
        summary["by_status"][r["_id"]] = {
            "count": r["count"],
            "estimated": r["total_amount"],
            "approved": r["approved_amount"]
        }
        summary["total_claims"] += r["count"]
        summary["total_estimated_amount"] += r["total_amount"]
        summary["total_approved_amount"] += r["approved_amount"]
    
    # Get recent claims
    recent = await db.abdm_claims.find(
        {},
        {"_id": 0, "id": 1, "claim_number": 1, "status": 1, "amounts": 1, "created_at": 1, "patient_id": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    summary["recent_claims"] = recent
    
    return summary

# Helper function to generate demo national records
def generate_demo_national_records(patient_id: str, hi_types: List[str]) -> List[Dict]:
    """Generate demo health records from simulated external HIPs"""
    records = []
    
    if "OPConsultation" in hi_types:
        records.append({
            "id": str(uuid4()),
            "type": "OPConsultation",
            "source_hip": "AIIMS Delhi",
            "date": "2024-06-15",
            "provider": "Dr. Rajesh Kumar",
            "speciality": "Cardiology",
            "diagnosis": "Essential Hypertension",
            "notes": "Patient advised lifestyle modifications and medication",
            "prescription_given": True
        })
        records.append({
            "id": str(uuid4()),
            "type": "OPConsultation",
            "source_hip": "Safdarjung Hospital",
            "date": "2024-03-20",
            "provider": "Dr. Priya Singh",
            "speciality": "General Medicine",
            "diagnosis": "Acute Upper Respiratory Infection",
            "notes": "Symptomatic treatment prescribed",
            "prescription_given": True
        })
    
    if "Prescription" in hi_types:
        records.append({
            "id": str(uuid4()),
            "type": "Prescription",
            "source_hip": "AIIMS Delhi",
            "date": "2024-06-15",
            "provider": "Dr. Rajesh Kumar",
            "medications": [
                {"name": "Amlodipine 5mg", "dosage": "Once daily", "duration": "30 days"},
                {"name": "Aspirin 75mg", "dosage": "Once daily", "duration": "30 days"}
            ]
        })
    
    if "DiagnosticReport" in hi_types:
        records.append({
            "id": str(uuid4()),
            "type": "DiagnosticReport",
            "source_hip": "Apollo Bangalore",
            "date": "2024-05-10",
            "test_name": "Lipid Profile",
            "results": {
                "Total Cholesterol": "220 mg/dL (High)",
                "LDL": "150 mg/dL (High)",
                "HDL": "45 mg/dL (Low)",
                "Triglycerides": "180 mg/dL (Normal)"
            },
            "conclusion": "Dyslipidemia - lifestyle modification recommended"
        })
        records.append({
            "id": str(uuid4()),
            "type": "DiagnosticReport",
            "source_hip": "AIIMS Delhi",
            "date": "2024-06-15",
            "test_name": "ECG",
            "results": {
                "Heart Rate": "78 bpm",
                "Rhythm": "Normal Sinus Rhythm",
                "PR Interval": "0.16 sec",
                "QRS Duration": "0.08 sec"
            },
            "conclusion": "Normal ECG"
        })
    
    return records
