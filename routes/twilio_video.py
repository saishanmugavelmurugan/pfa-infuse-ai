"""
Twilio Video Integration for Telemedicine
Enterprise-grade video calling for doctor-patient consultations
Includes: 1-on-1 video rooms, recording, consent management
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os
import dependencies

# Twilio imports - will use mock if credentials not set
try:
    from twilio.rest import Client
    from twilio.jwt.access_token import AccessToken
    from twilio.jwt.access_token.grants import VideoGrant
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

router = APIRouter(prefix="/twilio-video", tags=["Twilio Video"])

# Twilio credentials from environment
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_API_KEY_SID = os.environ.get("TWILIO_API_KEY_SID")
TWILIO_API_KEY_SECRET = os.environ.get("TWILIO_API_KEY_SECRET")

# Check if Twilio is properly configured
def is_twilio_configured():
    return all([TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET, TWILIO_AVAILABLE])


class VideoRoomRequest(BaseModel):
    appointment_id: str
    doctor_id: str
    patient_id: str
    room_type: str = "group"  # "go", "group", "group-small", "peer-to-peer"
    max_participants: int = 2
    enable_recording: bool = True
    record_participants_on_connect: bool = True


class VideoTokenRequest(BaseModel):
    room_name: str
    identity: str  # User identifier (doctor_id or patient_id)
    user_type: str  # "doctor" or "patient"


class EndRoomRequest(BaseModel):
    room_sid: str


class RoomRecording(BaseModel):
    recording_sid: str
    room_sid: str
    duration_seconds: int
    size_bytes: int
    url: Optional[str] = None


@router.get("/status")
async def get_twilio_status():
    """Check Twilio Video integration status"""
    return {
        "twilio_sdk_available": TWILIO_AVAILABLE,
        "credentials_configured": is_twilio_configured(),
        "account_sid_set": bool(TWILIO_ACCOUNT_SID),
        "api_key_set": bool(TWILIO_API_KEY_SID),
        "api_secret_set": bool(TWILIO_API_KEY_SECRET),
        "status": "ready" if is_twilio_configured() else "credentials_required",
        "setup_instructions": {
            "step_1": "Sign up at https://www.twilio.com",
            "step_2": "Go to Console > Account > API Keys",
            "step_3": "Create a new API Key (Standard)",
            "step_4": "Set environment variables: TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SID, TWILIO_API_KEY_SECRET"
        }
    }


@router.post("/room/create")
async def create_video_room(request: VideoRoomRequest):
    """
    Create a Twilio Video room for a consultation.
    Returns room details and SID.
    """
    db = await dependencies.get_database()
    
    # Generate unique room name
    room_name = f"infuse-{request.appointment_id}-{str(uuid4())[:8]}"
    
    if is_twilio_configured():
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SECRET)
            
            # Create the video room
            room = client.video.rooms.create(
                unique_name=room_name,
                type=request.room_type,
                max_participants=request.max_participants,
                record_participants_on_connect=request.record_participants_on_connect,
                status_callback=f"{os.environ.get('REACT_APP_BACKEND_URL', '')}/api/twilio-video/webhook"
            )
            
            room_data = {
                "id": f"room_{str(uuid4())[:8]}",
                "room_sid": room.sid,
                "room_name": room_name,
                "appointment_id": request.appointment_id,
                "doctor_id": request.doctor_id,
                "patient_id": request.patient_id,
                "status": room.status,
                "type": room.type,
                "max_participants": room.max_participants,
                "recording_enabled": request.enable_recording,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "twilio_mode": "live"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create Twilio room: {str(e)}")
    else:
        # Mock mode when Twilio not configured
        room_data = {
            "id": f"room_{str(uuid4())[:8]}",
            "room_sid": f"RM{str(uuid4()).replace('-', '')[:32]}",
            "room_name": room_name,
            "appointment_id": request.appointment_id,
            "doctor_id": request.doctor_id,
            "patient_id": request.patient_id,
            "status": "in-progress",
            "type": request.room_type,
            "max_participants": request.max_participants,
            "recording_enabled": request.enable_recording,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "twilio_mode": "mock"
        }
    
    # Store room in database
    await db.video_rooms.insert_one(room_data)
    room_data.pop("_id", None)
    
    return {
        "success": True,
        "room": room_data,
        "mode": room_data.get("twilio_mode", "unknown")
    }


@router.post("/token")
async def generate_access_token(request: VideoTokenRequest):
    """
    Generate a Twilio Access Token for a participant to join a video room.
    Each participant needs their own token.
    """
    if is_twilio_configured():
        try:
            # Create Access Token
            token = AccessToken(
                TWILIO_ACCOUNT_SID,
                TWILIO_API_KEY_SID,
                TWILIO_API_KEY_SECRET,
                identity=request.identity,
                ttl=3600  # 1 hour validity
            )
            
            # Create Video Grant
            video_grant = VideoGrant(room=request.room_name)
            token.add_grant(video_grant)
            
            return {
                "success": True,
                "token": token.to_jwt(),
                "room_name": request.room_name,
                "identity": request.identity,
                "user_type": request.user_type,
                "expires_in_seconds": 3600,
                "mode": "live"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate token: {str(e)}")
    else:
        # Mock token for testing
        mock_token = f"mock_token_{request.identity}_{request.room_name}_{str(uuid4())[:8]}"
        
        return {
            "success": True,
            "token": mock_token,
            "room_name": request.room_name,
            "identity": request.identity,
            "user_type": request.user_type,
            "expires_in_seconds": 3600,
            "mode": "mock",
            "note": "This is a mock token. Configure Twilio credentials for real video calls."
        }


@router.get("/room/{room_name}")
async def get_room_details(room_name: str):
    """Get details of a video room"""
    db = await dependencies.get_database()
    
    room = await db.video_rooms.find_one({"room_name": room_name}, {"_id": 0})
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # If Twilio configured, get live status
    if is_twilio_configured() and room.get("room_sid"):
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SECRET)
            twilio_room = client.video.rooms(room["room_sid"]).fetch()
            room["live_status"] = twilio_room.status
            room["participants_count"] = len(list(twilio_room.participants.list()))
        except:
            pass
    
    return room


@router.post("/room/{room_sid}/end")
async def end_video_room(room_sid: str):
    """End a video room and stop recording"""
    db = await dependencies.get_database()
    
    if is_twilio_configured():
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SECRET)
            
            # Complete the room
            room = client.video.rooms(room_sid).update(status="completed")
            
            # Update database
            await db.video_rooms.update_one(
                {"room_sid": room_sid},
                {
                    "$set": {
                        "status": "completed",
                        "ended_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
            return {
                "success": True,
                "room_sid": room_sid,
                "status": "completed",
                "mode": "live"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to end room: {str(e)}")
    else:
        # Mock mode
        await db.video_rooms.update_one(
            {"room_sid": room_sid},
            {
                "$set": {
                    "status": "completed",
                    "ended_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "room_sid": room_sid,
            "status": "completed",
            "mode": "mock"
        }


@router.get("/room/{room_sid}/recordings")
async def get_room_recordings(room_sid: str):
    """Get all recordings for a video room"""
    if not is_twilio_configured():
        return {
            "room_sid": room_sid,
            "recordings": [],
            "mode": "mock",
            "note": "Configure Twilio credentials to access recordings"
        }
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SECRET)
        
        recordings = client.video.rooms(room_sid).recordings.list()
        
        recording_list = []
        for rec in recordings:
            recording_list.append({
                "recording_sid": rec.sid,
                "room_sid": room_sid,
                "status": rec.status,
                "duration_seconds": rec.duration,
                "size_bytes": rec.size,
                "type": rec.type,
                "source_sid": rec.source_sid,
                "created_at": rec.date_created.isoformat() if rec.date_created else None
            })
        
        return {
            "room_sid": room_sid,
            "recordings": recording_list,
            "count": len(recording_list),
            "mode": "live"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recordings: {str(e)}")


@router.post("/webhook")
async def twilio_status_webhook(data: dict):
    """
    Handle Twilio Video status callbacks.
    Called when room status changes, participants join/leave, recordings complete.
    """
    db = await dependencies.get_database()
    
    event_type = data.get("StatusCallbackEvent")
    room_sid = data.get("RoomSid")
    room_name = data.get("RoomName")
    
    # Log the event
    event = {
        "id": f"evt_{str(uuid4())[:8]}",
        "event_type": event_type,
        "room_sid": room_sid,
        "room_name": room_name,
        "data": data,
        "received_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.video_events.insert_one(event)
    
    # Handle specific events
    if event_type == "room-ended":
        await db.video_rooms.update_one(
            {"room_sid": room_sid},
            {"$set": {"status": "completed", "ended_at": datetime.now(timezone.utc).isoformat()}}
        )
    elif event_type == "participant-connected":
        participant_identity = data.get("ParticipantIdentity")
        await db.video_rooms.update_one(
            {"room_sid": room_sid},
            {"$push": {"participants": participant_identity}}
        )
    elif event_type == "recording-completed":
        recording_sid = data.get("RecordingSid")
        await db.video_rooms.update_one(
            {"room_sid": room_sid},
            {"$push": {"recordings": recording_sid}}
        )
    
    return {"received": True}


@router.get("/rooms/active")
async def get_active_rooms():
    """Get all currently active video rooms"""
    db = await dependencies.get_database()
    
    active_rooms = await db.video_rooms.find(
        {"status": "in-progress"},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "count": len(active_rooms),
        "rooms": active_rooms
    }


@router.get("/rooms/appointment/{appointment_id}")
async def get_appointment_room(appointment_id: str):
    """Get video room for a specific appointment"""
    db = await dependencies.get_database()
    
    room = await db.video_rooms.find_one(
        {"appointment_id": appointment_id},
        {"_id": 0}
    )
    
    if not room:
        raise HTTPException(status_code=404, detail="No video room found for this appointment")
    
    return room
