from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/telemedicine", tags=["HealthTrack - Telemedicine"])

@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_telemedicine_session(
    session_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create telemedicine session - USP: Recording with consent"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    video_room_id = f"room_{uuid.uuid4().hex[:12]}"
    
    session_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "video_room_id": video_room_id,
        "session_token": f"token_{uuid.uuid4().hex}",
        "status": "scheduled",
        "scheduled_duration": 30,
        "recording_enabled": False,
        "recording_consent_given": False,
        "chat_enabled": True,
        "chat_transcript": [],
        "shared_files": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **session_data
    }
    
    await db.healthtrack_telemedicine_sessions.insert_one(session_dict)
    session_dict.pop("_id", None)
    
    return {"message": "Telemedicine session created", "session": session_dict}

@router.get("/sessions/{session_id}")
async def join_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Join telemedicine session"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    session = await db.healthtrack_telemedicine_sessions.find_one(
        {"id": session_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Update status if first join
    if session["status"] == "scheduled":
        await db.healthtrack_telemedicine_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "status": "in-progress",
                "session_start": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    return session

@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    session_notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """End telemedicine session"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    session = await db.healthtrack_telemedicine_sessions.find_one(
        {"id": session_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    session_end = datetime.now(timezone.utc)
    session_start = datetime.fromisoformat(session.get("session_start", session_end.isoformat()))
    duration = int((session_end - session_start).total_seconds() / 60)
    
    await db.healthtrack_telemedicine_sessions.update_one(
        {"id": session_id},
        {"$set": {
            "status": "completed",
            "session_end": session_end.isoformat(),
            "duration_minutes": duration,
            "session_notes": session_notes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Session ended", "duration_minutes": duration}

@router.get("/sessions/{session_id}/recording")
async def get_session_recording(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get session recording - USP: Only with consent"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    session = await db.healthtrack_telemedicine_sessions.find_one(
        {"id": session_id, "organization_id": org["id"]},
        {"_id": 0}
    )
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if not session.get("recording_consent_given"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Recording consent not given")
    
    return {"recording_url": session.get("recording_url"), "session": session}

@router.post("/sessions/{session_id}/chat")
async def send_chat_message(
    session_id: str,
    message: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Send chat message during session"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    chat_message = {
        "sender_id": user_id,
        "sender_type": current_user.get("role", "user"),
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_type": "text"
    }
    
    result = await db.healthtrack_telemedicine_sessions.update_one(
        {"id": session_id, "organization_id": org["id"]},
        {"$push": {"chat_transcript": chat_message}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    return {"message": "Message sent", "chat_message": chat_message}

@router.get("/waiting-room")
async def get_waiting_room(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get waiting room - scheduled sessions"""
    user_id = current_user["user_id"]
    role = current_user.get("role")
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"organization_id": org["id"], "status": "scheduled"}
    
    if role == "doctor":
        query["doctor_id"] = user_id
    elif role == "user":
        query["patient_id"] = user_id
    
    sessions = await db.healthtrack_telemedicine_sessions.find(query, {"_id": 0}).to_list(50)
    
    return {"waiting_sessions": sessions, "total": len(sessions)}
