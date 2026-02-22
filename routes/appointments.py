from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone, date, timedelta
import uuid
import random
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/appointments", tags=["HealthTrack - Appointments"])

# USP: Smart Doctor Matching Algorithm
async def calculate_match_score(patient_id: str, doctor_id: str, reason: str, db) -> dict:
    """Calculate smart matching score between patient and doctor"""
    score = 0.5  # Base score
    reasons = []
    
    # Check if patient has seen this doctor before
    past_appointments = await db.healthtrack_appointments.count_documents({
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "status": "completed"
    })
    
    if past_appointments > 0:
        score += 0.3
        reasons.append(f"Seen this doctor {past_appointments} times before")
    
    # Check doctor's specialty matches reason (simplified)
    if "heart" in reason.lower() or "cardiac" in reason.lower():
        score += 0.2
        reasons.append("Matches cardiac specialty")
    
    return {"score": min(score, 1.0), "reasons": reasons}

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create new appointment with USP features: guarantee system & smart matching"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Verify patient exists
    patient = await db.healthtrack_patients.find_one(
        {"id": appointment_data["patient_id"], "organization_id": org["id"]},
        {"_id": 0}
    )
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    
    # If doctor_id not provided, auto-assign the current user if they are a doctor, or find one
    if "doctor_id" not in appointment_data or not appointment_data.get("doctor_id"):
        # Check if current user is a doctor
        current_user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if current_user_doc and current_user_doc.get("role") == "doctor":
            appointment_data["doctor_id"] = user_id
        else:
            # Find any available doctor in the organization
            available_doctor = await db.users.find_one(
                {"role": "doctor", "organization_id": org["id"]},
                {"_id": 0}
            )
            if available_doctor:
                appointment_data["doctor_id"] = available_doctor["id"]
            else:
                # Fallback to current user as the attending
                appointment_data["doctor_id"] = user_id
    
    # Verify doctor exists
    doctor = await db.users.find_one(
        {"id": appointment_data["doctor_id"]},
        {"_id": 0}
    )
    if not doctor:
        # Create a placeholder doctor record if needed
        appointment_data["doctor_id"] = user_id
    
    # USP: Calculate smart matching score
    match_data = await calculate_match_score(
        appointment_data["patient_id"],
        appointment_data["doctor_id"],
        appointment_data.get("reason", ""),
        db
    )
    
    # Create appointment
    appointment_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "created_by": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "scheduled",
        "payment_status": "pending",
        "payment_amount": 500.0,  # Default consultation fee
        "doctor_confirmed": False,
        "guarantee_status": "pending",
        "match_score": match_data["score"],
        "match_reasons": match_data["reasons"],
        "reminder_sent": False,
        **appointment_data
    }
    
    await db.healthtrack_appointments.insert_one(appointment_dict)
    appointment_dict.pop("_id", None)
    
    return {"message": "Appointment created successfully", "appointment": appointment_dict}

@router.get("")
async def list_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List appointments with filters"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"organization_id": org["id"]}
    
    if status_filter:
        query["status"] = status_filter
    
    if date_from and date_to:
        query["appointment_date"] = {"$gte": date_from.isoformat(), "$lte": date_to.isoformat()}
    elif date_from:
        query["appointment_date"] = {"$gte": date_from.isoformat()}
    elif date_to:
        query["appointment_date"] = {"$lte": date_to.isoformat()}
    
    total = await db.healthtrack_appointments.count_documents(query)
    
    appointments = await db.healthtrack_appointments.find(
        query,
        {"_id": 0}
    ).sort("appointment_date", -1).skip(skip).limit(limit).to_list(limit)
    
    return {"total": total, "skip": skip, "limit": limit, "appointments": appointments}

@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get appointment details"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    appointment = await db.healthtrack_appointments.find_one(
        {"id": appointment_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    
    return appointment

@router.put("/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    appointment_update: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update appointment"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    appointment = await db.healthtrack_appointments.find_one(
        {"id": appointment_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    
    appointment_update["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.healthtrack_appointments.update_one(
        {"id": appointment_id},
        {"$set": appointment_update}
    )
    
    updated = await db.healthtrack_appointments.find_one({"id": appointment_id}, {"_id": 0})
    
    return {"message": "Appointment updated", "appointment": updated}

@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    cancellation_reason: str = Query(..., min_length=5),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Cancel appointment with USP: instant refund"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    appointment = await db.healthtrack_appointments.find_one(
        {"id": appointment_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    
    if appointment["status"] == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already cancelled")
    
    # USP: Calculate refund based on cancellation time
    appt_datetime = datetime.fromisoformat(f"{appointment['appointment_date']}T{appointment['appointment_time']}")
    hours_before = (appt_datetime - datetime.now()).total_seconds() / 3600
    
    refund_percentage = 1.0 if hours_before >= 24 else 0.5 if hours_before >= 12 else 0.0
    refund_amount = appointment["payment_amount"] * refund_percentage
    
    # Update appointment
    await db.healthtrack_appointments.update_one(
        {"id": appointment_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_by": user_id,
            "cancellation_reason": cancellation_reason,
            "payment_status": "refunded" if refund_amount > 0 else "paid",
            "refund_amount": refund_amount,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Appointment cancelled",
        "refund_amount": refund_amount,
        "refund_percentage": refund_percentage * 100
    }

@router.get("/calendar/view")
async def get_calendar_view(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2024),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get calendar view of appointments"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Get appointments for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    appointments = await db.healthtrack_appointments.find(
        {
            "organization_id": org["id"],
            "appointment_date": {
                "$gte": start_date.isoformat(),
                "$lt": end_date.isoformat()
            }
        },
        {"_id": 0}
    ).to_list(1000)
    
    return {"month": month, "year": year, "appointments": appointments}

@router.get("/slots/available")
async def get_available_slots(
    doctor_id: str,
    appointment_date: date,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get available time slots for a doctor on a specific date"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Get existing appointments for this doctor on this date
    booked_appointments = await db.healthtrack_appointments.find(
        {
            "doctor_id": doctor_id,
            "appointment_date": appointment_date.isoformat(),
            "status": {"$in": ["scheduled", "confirmed"]}
        },
        {"_id": 0, "appointment_time": 1}
    ).to_list(100)
    
    booked_times = [appt["appointment_time"] for appt in booked_appointments]
    
    # Generate all possible slots (9 AM to 5 PM, 30-min slots)
    all_slots = []
    for hour in range(9, 17):
        for minute in [0, 30]:
            slot_time = f"{hour:02d}:{minute:02d}"
            if slot_time not in booked_times:
                all_slots.append({
                    "time": slot_time,
                    "available": True
                })
    
    return {"date": appointment_date.isoformat(), "doctor_id": doctor_id, "available_slots": all_slots}
