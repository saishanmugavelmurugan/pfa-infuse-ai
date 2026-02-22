from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/healthtrack/notifications", tags=["HealthTrack - Notifications"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def send_notification(
    notification_data: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Send notification - USP: Multi-channel delivery"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    notification_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "status": "pending",
        "read": False,
        "action_taken": False,
        "delivery_attempts": 0,
        "priority": notification_data.get("priority", "normal"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **notification_data
    }
    
    await db.healthtrack_notifications.insert_one(notification_dict)
    notification_dict.pop("_id", None)
    
    # TODO: Actual sending via SMS/Email (integrate with services)
    
    return {"message": "Notification queued", "notification": notification_dict}

@router.get("/")
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List user notifications"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    query = {"user_id": user_id, "organization_id": org["id"]}
    
    if unread_only:
        query["read"] = False
    
    total = await db.healthtrack_notifications.count_documents(query)
    
    notifications = await db.healthtrack_notifications.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {"total": total, "unread_count": len([n for n in notifications if not n["read"]]), "notifications": notifications}

@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Mark notification as read"""
    user_id = current_user["user_id"]
    
    result = await db.healthtrack_notifications.update_one(
        {"id": notification_id, "user_id": user_id},
        {"$set": {
            "read": True,
            "read_time": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    
    return {"message": "Marked as read"}

@router.post("/preferences")
async def set_notification_preferences(
    preferences: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Set notification preferences - USP: Granular control"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    prefs_dict = {
        "id": str(uuid.uuid4()),
        "organization_id": org["id"],
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **preferences
    }
    
    # Upsert preferences
    await db.healthtrack_notification_preferences.update_one(
        {"user_id": user_id, "organization_id": org["id"]},
        {"$set": prefs_dict},
        upsert=True
    )
    
    return {"message": "Preferences updated", "preferences": prefs_dict}
