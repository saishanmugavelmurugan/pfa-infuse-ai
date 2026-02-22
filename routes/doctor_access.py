"""
Doctor OTP Access - Secure one-time access to patient health records
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import random
import string
from bson import ObjectId
import dependencies

router = APIRouter(prefix="/doctor-access", tags=["Doctor Access"])

# In-memory OTP storage (in production, use Redis or database)
otp_storage = {}
access_logs = []

class OTPRequest(BaseModel):
    doctor_id: str
    patient_id: str
    reason: str

class OTPVerify(BaseModel):
    doctor_id: str
    patient_id: str
    otp: str

class RevokeAccess(BaseModel):
    patient_id: str
    doctor_id: str

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

@router.post("/request-otp")
async def request_otp(request: OTPRequest):
    """
    Doctor requests OTP to access patient's health records.
    OTP is sent to patient's registered mobile (simulated here).
    """
    try:
        db = await dependencies.get_database()
        
        # Verify doctor exists and is verified
        doctor = await db.doctors.find_one({"_id": ObjectId(request.doctor_id)})
        if not doctor:
            # Try users collection
            doctor = await db.users.find_one({
                "_id": ObjectId(request.doctor_id),
                "role": {"$in": ["doctor", "ayurvedic_doctor", "allopathic_doctor"]}
            })
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found or not verified")
        
        # Verify patient exists
        patient = await db.patients.find_one({"_id": ObjectId(request.patient_id)})
        if not patient:
            patient = await db.users.find_one({"_id": ObjectId(request.patient_id)})
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Generate OTP
        otp = generate_otp()
        expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        # Store OTP
        otp_key = f"{request.doctor_id}_{request.patient_id}"
        otp_storage[otp_key] = {
            "otp": otp,
            "expiry": expiry,
            "reason": request.reason,
            "doctor_id": request.doctor_id,
            "patient_id": request.patient_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # In production, send OTP via SMS/WhatsApp to patient
        patient_phone = patient.get("phone", patient.get("mobile", "9999999999"))
        patient_name = patient.get("name", patient.get("full_name", "Patient"))
        doctor_name = doctor.get("name", doctor.get("full_name", "Doctor"))
        
        # Log the request
        access_logs.append({
            "type": "otp_requested",
            "doctor_id": request.doctor_id,
            "doctor_name": doctor_name,
            "patient_id": request.patient_id,
            "patient_name": patient_name,
            "reason": request.reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": f"OTP sent to patient's registered mobile ending with ***{patient_phone[-4:] if len(patient_phone) >= 4 else '****'}",
            "expires_in": "10 minutes",
            "doctor_name": doctor_name,
            "patient_name": patient_name,
            # For demo purposes only - remove in production
            "demo_otp": otp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error requesting OTP: {str(e)}")

@router.post("/verify-otp")
async def verify_otp(request: OTPVerify):
    """
    Verify OTP and grant one-time access to patient records.
    Returns access token valid for the current session only.
    """
    try:
        otp_key = f"{request.doctor_id}_{request.patient_id}"
        
        if otp_key not in otp_storage:
            raise HTTPException(status_code=400, detail="No OTP request found. Please request a new OTP.")
        
        stored_otp = otp_storage[otp_key]
        
        # Check expiry
        if datetime.now(timezone.utc) > stored_otp["expiry"]:
            del otp_storage[otp_key]
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new OTP.")
        
        # Verify OTP
        if stored_otp["otp"] != request.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP. Please try again.")
        
        # OTP verified - generate access token
        access_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        access_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Store access grant
        db = await dependencies.get_database()
        access_record = {
            "doctor_id": request.doctor_id,
            "patient_id": request.patient_id,
            "access_token": access_token,
            "reason": stored_otp["reason"],
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": access_expiry.isoformat(),
            "status": "active"
        }
        
        await db.doctor_access_grants.insert_one(access_record)
        
        # Log the access grant
        access_logs.append({
            "type": "access_granted",
            "doctor_id": request.doctor_id,
            "patient_id": request.patient_id,
            "reason": stored_otp["reason"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Clear OTP
        del otp_storage[otp_key]
        
        return {
            "success": True,
            "message": "Access granted successfully",
            "access_token": access_token,
            "expires_at": access_expiry.isoformat(),
            "valid_for": "1 hour",
            "access_type": "read_only"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying OTP: {str(e)}")

@router.get("/patient-records/{patient_id}")
async def get_patient_records(patient_id: str, access_token: str):
    """
    Get patient health records using valid access token.
    Only accessible with a verified OTP access token.
    """
    try:
        db = await dependencies.get_database()
        
        # Verify access token
        access_grant = await db.doctor_access_grants.find_one({
            "patient_id": patient_id,
            "access_token": access_token,
            "status": "active"
        })
        
        if not access_grant:
            raise HTTPException(status_code=403, detail="Invalid or expired access token")
        
        # Check if access has expired
        expiry = datetime.fromisoformat(access_grant["expires_at"].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry:
            await db.doctor_access_grants.update_one(
                {"_id": access_grant["_id"]},
                {"$set": {"status": "expired"}}
            )
            raise HTTPException(status_code=403, detail="Access token has expired")
        
        # Get patient records
        patient = await db.patients.find_one({"_id": ObjectId(patient_id)}, {"_id": 0})
        if not patient:
            patient = await db.users.find_one({"_id": ObjectId(patient_id)}, {"_id": 0, "password": 0})
        
        # Get lab reports
        lab_reports = await db.lab_reports.find(
            {"patient_id": patient_id},
            {"_id": 0}
        ).sort("date", -1).limit(10).to_list(10)
        
        # Get vital records
        vitals = await db.vitals.find(
            {"patient_id": patient_id},
            {"_id": 0}
        ).sort("recorded_at", -1).limit(20).to_list(20)
        
        # Get wearable data
        wearable_data = await db.wearable_data.find(
            {"patient_id": patient_id},
            {"_id": 0}
        ).sort("synced_at", -1).limit(10).to_list(10)
        
        # Log the record access
        await db.doctor_access_logs.insert_one({
            "doctor_id": access_grant["doctor_id"],
            "patient_id": patient_id,
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "data_accessed": ["profile", "lab_reports", "vitals", "wearable_data"]
        })
        
        return {
            "success": True,
            "patient_profile": patient,
            "lab_reports": lab_reports,
            "vitals": vitals,
            "wearable_data": wearable_data,
            "access_reason": access_grant["reason"],
            "access_expires_at": access_grant["expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")

@router.post("/revoke-access")
async def revoke_access(request: RevokeAccess):
    """
    Patient can revoke doctor's access at any time.
    """
    try:
        db = await dependencies.get_database()
        
        result = await db.doctor_access_grants.update_many(
            {
                "patient_id": request.patient_id,
                "doctor_id": request.doctor_id,
                "status": "active"
            },
            {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count == 0:
            return {"success": True, "message": "No active access found to revoke"}
        
        # Log the revocation
        access_logs.append({
            "type": "access_revoked",
            "doctor_id": request.doctor_id,
            "patient_id": request.patient_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": f"Access revoked for {result.modified_count} session(s)"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking access: {str(e)}")

@router.get("/access-history/{patient_id}")
async def get_access_history(patient_id: str):
    """
    Get history of all doctor access to patient records.
    """
    try:
        db = await dependencies.get_database()
        
        # Get access grants
        grants = await db.doctor_access_grants.find(
            {"patient_id": patient_id},
            {"_id": 0, "access_token": 0}
        ).sort("granted_at", -1).limit(50).to_list(50)
        
        # Get access logs
        logs = await db.doctor_access_logs.find(
            {"patient_id": patient_id},
            {"_id": 0}
        ).sort("accessed_at", -1).limit(100).to_list(100)
        
        # Enrich with doctor names
        for grant in grants:
            doctor = await db.doctors.find_one({"_id": ObjectId(grant["doctor_id"])})
            if not doctor:
                doctor = await db.users.find_one({"_id": ObjectId(grant["doctor_id"])})
            grant["doctor_name"] = doctor.get("name", "Unknown") if doctor else "Unknown"
        
        return {
            "success": True,
            "access_grants": grants,
            "access_logs": logs,
            "total_accesses": len(grants)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching access history: {str(e)}")

@router.get("/pending-requests/{doctor_id}")
async def get_pending_requests(doctor_id: str):
    """
    Get all pending OTP requests for a doctor.
    """
    pending = []
    for key, value in otp_storage.items():
        if value["doctor_id"] == doctor_id:
            if datetime.now(timezone.utc) < value["expiry"]:
                pending.append({
                    "patient_id": value["patient_id"],
                    "reason": value["reason"],
                    "created_at": value["created_at"],
                    "expires_at": value["expiry"].isoformat()
                })
    
    return {
        "success": True,
        "pending_requests": pending,
        "count": len(pending)
    }
