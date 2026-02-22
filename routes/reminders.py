"""
Appointment Reminders API
Smart reminder system with customizable timing
Supports: 1 day before, 3 hours before, custom intervals
Delivery channels: SMS, Email, Push notifications
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import dependencies
from enum import Enum

router = APIRouter(prefix="/reminders", tags=["Appointment Reminders"])


class ReminderChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class ReminderStatus(str, Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AppointmentReminder(BaseModel):
    appointment_id: str
    user_id: str
    reminder_type: str  # "day_before", "3_hours", "1_hour", "30_min", "custom"
    scheduled_time: datetime
    channels: List[ReminderChannel]
    status: ReminderStatus = ReminderStatus.SCHEDULED
    message: Optional[str] = None
    metadata: Dict = {}


class ReminderPreferences(BaseModel):
    user_id: str
    day_before: bool = True
    three_hours_before: bool = True
    one_hour_before: bool = False
    thirty_minutes_before: bool = False
    custom_minutes: List[int] = []  # e.g., [120, 15] for 2 hours and 15 minutes before
    channels: List[ReminderChannel] = [ReminderChannel.PUSH, ReminderChannel.EMAIL]
    quiet_hours_start: Optional[str] = "22:00"  # Don't send reminders after this time
    quiet_hours_end: Optional[str] = "07:00"    # Don't send reminders before this time
    enabled: bool = True


class CreateRemindersRequest(BaseModel):
    appointment_id: str
    appointment_time: datetime
    user_id: str
    doctor_name: str
    consultation_type: str
    custom_preferences: Optional[ReminderPreferences] = None


# Reminder message templates
REMINDER_TEMPLATES = {
    "day_before": """
Hi {patient_name},

This is a reminder for your appointment tomorrow:

📅 Date: {date}
⏰ Time: {time}
👨‍⚕️ Doctor: {doctor_name}
📍 Type: {consultation_type}

Please ensure you're available and have any relevant medical documents ready.

Need to reschedule? Visit: {reschedule_link}

Best regards,
Infuse Health Team
www.infuse.net.in
""",
    "three_hours": """
Hi {patient_name},

Your appointment is in 3 hours!

⏰ Time: {time}
👨‍⚕️ Doctor: {doctor_name}
📍 Type: {consultation_type}

{video_call_instructions}

Best regards,
Infuse Health Team
""",
    "one_hour": """
Reminder: Your appointment with {doctor_name} is in 1 hour at {time}.

{quick_join_link}
""",
    "thirty_min": """
Your appointment starts in 30 minutes!

👨‍⚕️ {doctor_name}
⏰ {time}

{join_button}
""",
}


@router.post("/create")
async def create_appointment_reminders(
    request: CreateRemindersRequest,
    background_tasks: BackgroundTasks
):
    """
    Create reminders for an appointment based on user preferences.
    Schedules multiple reminders: 1 day before, 3 hours before, etc.
    """
    db = await dependencies.get_database()
    
    # Get user's reminder preferences or use defaults
    user_prefs = await db.reminder_preferences.find_one({"user_id": request.user_id})
    
    if not user_prefs:
        user_prefs = ReminderPreferences(user_id=request.user_id).dict()
    
    # Override with custom preferences if provided
    if request.custom_preferences:
        user_prefs = request.custom_preferences.dict()
    
    if not user_prefs.get("enabled", True):
        return {"status": "skipped", "reason": "Reminders disabled by user"}
    
    reminders_created = []
    appointment_time = request.appointment_time
    channels = user_prefs.get("channels", [ReminderChannel.PUSH, ReminderChannel.EMAIL])
    
    # 1 Day Before
    if user_prefs.get("day_before", True):
        reminder_time = appointment_time - timedelta(days=1)
        if reminder_time > datetime.now(timezone.utc):
            reminder = await _create_reminder(
                db=db,
                appointment_id=request.appointment_id,
                user_id=request.user_id,
                reminder_type="day_before",
                scheduled_time=reminder_time,
                channels=channels,
                doctor_name=request.doctor_name,
                consultation_type=request.consultation_type,
                appointment_time=appointment_time
            )
            reminders_created.append(reminder)
    
    # 3 Hours Before
    if user_prefs.get("three_hours_before", True):
        reminder_time = appointment_time - timedelta(hours=3)
        if reminder_time > datetime.now(timezone.utc):
            reminder = await _create_reminder(
                db=db,
                appointment_id=request.appointment_id,
                user_id=request.user_id,
                reminder_type="three_hours",
                scheduled_time=reminder_time,
                channels=channels,
                doctor_name=request.doctor_name,
                consultation_type=request.consultation_type,
                appointment_time=appointment_time
            )
            reminders_created.append(reminder)
    
    # 1 Hour Before
    if user_prefs.get("one_hour_before", False):
        reminder_time = appointment_time - timedelta(hours=1)
        if reminder_time > datetime.now(timezone.utc):
            reminder = await _create_reminder(
                db=db,
                appointment_id=request.appointment_id,
                user_id=request.user_id,
                reminder_type="one_hour",
                scheduled_time=reminder_time,
                channels=channels,
                doctor_name=request.doctor_name,
                consultation_type=request.consultation_type,
                appointment_time=appointment_time
            )
            reminders_created.append(reminder)
    
    # 30 Minutes Before
    if user_prefs.get("thirty_minutes_before", False):
        reminder_time = appointment_time - timedelta(minutes=30)
        if reminder_time > datetime.now(timezone.utc):
            reminder = await _create_reminder(
                db=db,
                appointment_id=request.appointment_id,
                user_id=request.user_id,
                reminder_type="thirty_min",
                scheduled_time=reminder_time,
                channels=channels,
                doctor_name=request.doctor_name,
                consultation_type=request.consultation_type,
                appointment_time=appointment_time
            )
            reminders_created.append(reminder)
    
    # Custom reminder times
    for minutes in user_prefs.get("custom_minutes", []):
        reminder_time = appointment_time - timedelta(minutes=minutes)
        if reminder_time > datetime.now(timezone.utc):
            reminder = await _create_reminder(
                db=db,
                appointment_id=request.appointment_id,
                user_id=request.user_id,
                reminder_type=f"custom_{minutes}min",
                scheduled_time=reminder_time,
                channels=channels,
                doctor_name=request.doctor_name,
                consultation_type=request.consultation_type,
                appointment_time=appointment_time
            )
            reminders_created.append(reminder)
    
    return {
        "status": "created",
        "appointment_id": request.appointment_id,
        "reminders_count": len(reminders_created),
        "reminders": reminders_created
    }


async def _create_reminder(
    db,
    appointment_id: str,
    user_id: str,
    reminder_type: str,
    scheduled_time: datetime,
    channels: List,
    doctor_name: str,
    consultation_type: str,
    appointment_time: datetime
) -> dict:
    """Create a single reminder record"""
    
    reminder = {
        "id": f"rem_{str(uuid4())[:8]}",
        "appointment_id": appointment_id,
        "user_id": user_id,
        "reminder_type": reminder_type,
        "scheduled_time": scheduled_time.isoformat(),
        "channels": [c.value if hasattr(c, 'value') else c for c in channels],
        "status": "scheduled",
        "metadata": {
            "doctor_name": doctor_name,
            "consultation_type": consultation_type,
            "appointment_time": appointment_time.isoformat()
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.reminders.insert_one(reminder)
    reminder.pop("_id", None)
    
    return reminder


@router.get("/appointment/{appointment_id}")
async def get_appointment_reminders(appointment_id: str):
    """Get all reminders for an appointment"""
    db = await dependencies.get_database()
    
    reminders = await db.reminders.find(
        {"appointment_id": appointment_id},
        {"_id": 0}
    ).sort("scheduled_time", 1).to_list(100)
    
    return {
        "appointment_id": appointment_id,
        "reminders": reminders
    }


@router.get("/user/{user_id}")
async def get_user_reminders(
    user_id: str,
    status: Optional[ReminderStatus] = None,
    limit: int = 50
):
    """Get all reminders for a user"""
    db = await dependencies.get_database()
    
    query = {"user_id": user_id}
    if status:
        query["status"] = status.value
    
    reminders = await db.reminders.find(
        query,
        {"_id": 0}
    ).sort("scheduled_time", 1).limit(limit).to_list(limit)
    
    return {
        "user_id": user_id,
        "count": len(reminders),
        "reminders": reminders
    }


@router.delete("/appointment/{appointment_id}")
async def cancel_appointment_reminders(appointment_id: str):
    """Cancel all reminders for an appointment"""
    db = await dependencies.get_database()
    
    result = await db.reminders.update_many(
        {"appointment_id": appointment_id, "status": "scheduled"},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "status": "cancelled",
        "appointment_id": appointment_id,
        "reminders_cancelled": result.modified_count
    }


@router.put("/preferences")
async def update_reminder_preferences(preferences: ReminderPreferences):
    """Update user's reminder preferences"""
    db = await dependencies.get_database()
    
    await db.reminder_preferences.update_one(
        {"user_id": preferences.user_id},
        {
            "$set": {
                **preferences.dict(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"status": "updated", "preferences": preferences.dict()}


@router.get("/preferences/{user_id}")
async def get_reminder_preferences(user_id: str):
    """Get user's reminder preferences"""
    db = await dependencies.get_database()
    
    prefs = await db.reminder_preferences.find_one({"user_id": user_id}, {"_id": 0})
    
    if not prefs:
        # Return defaults
        prefs = ReminderPreferences(user_id=user_id).dict()
    
    return prefs


@router.post("/send/{reminder_id}")
async def send_reminder(reminder_id: str, background_tasks: BackgroundTasks):
    """
    Manually trigger sending a reminder.
    In production, this would be called by a scheduled job.
    """
    db = await dependencies.get_database()
    
    reminder = await db.reminders.find_one({"id": reminder_id})
    
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    if reminder["status"] != "scheduled":
        raise HTTPException(status_code=400, detail=f"Reminder status is {reminder['status']}, cannot send")
    
    # In production, actually send via SMS/Email/Push
    # For now, just update status
    
    await db.reminders.update_one(
        {"id": reminder_id},
        {
            "$set": {
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "status": "sent",
        "reminder_id": reminder_id,
        "channels": reminder["channels"],
        "note": "MOCKED - In production, this would send actual SMS/Email/Push notifications"
    }


@router.get("/pending")
async def get_pending_reminders(
    minutes_ahead: int = 5
):
    """
    Get reminders that need to be sent in the next N minutes.
    Used by the reminder scheduler job.
    """
    db = await dependencies.get_database()
    
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(minutes=minutes_ahead)
    
    pending = await db.reminders.find({
        "status": "scheduled",
        "scheduled_time": {
            "$gte": now.isoformat(),
            "$lte": cutoff.isoformat()
        }
    }, {"_id": 0}).to_list(1000)
    
    return {
        "count": len(pending),
        "time_window": f"next {minutes_ahead} minutes",
        "reminders": pending
    }


@router.get("/stats")
async def get_reminder_stats():
    """Get reminder statistics"""
    db = await dependencies.get_database()
    
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]
    
    stats = await db.reminders.aggregate(pipeline).to_list(10)
    
    stats_dict = {item["_id"]: item["count"] for item in stats}
    
    return {
        "total": sum(stats_dict.values()),
        "scheduled": stats_dict.get("scheduled", 0),
        "sent": stats_dict.get("sent", 0),
        "failed": stats_dict.get("failed", 0),
        "cancelled": stats_dict.get("cancelled", 0)
    }
