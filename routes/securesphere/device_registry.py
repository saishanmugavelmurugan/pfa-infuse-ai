"""
Mobile Device Registry API
Part of SecureSphere Mobile Security Module

Features:
- Device registration and management
- Device fingerprinting
- Multi-platform support (Android, iOS, macOS, Windows)
- Enterprise device management
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
from uuid import uuid4
import hashlib

import dependencies

router = APIRouter(prefix="/securesphere/devices", tags=["SecureSphere - Device Registry"])


class DeviceRegistration(BaseModel):
    user_id: str
    device_name: str
    platform: str  # android, ios, windows, macos
    os_version: str
    device_model: Optional[str] = None
    device_manufacturer: Optional[str] = None
    app_version: Optional[str] = None
    push_token: Optional[str] = None
    # Security features
    biometric_enabled: Optional[bool] = False
    encryption_enabled: Optional[bool] = True
    screen_lock_enabled: Optional[bool] = True


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    push_token: Optional[str] = None
    biometric_enabled: Optional[bool] = None
    encryption_enabled: Optional[bool] = None
    screen_lock_enabled: Optional[bool] = None


def generate_device_fingerprint(device_data: Dict) -> str:
    """Generate unique device fingerprint"""
    fingerprint_data = f"{device_data.get('platform', '')}-{device_data.get('device_model', '')}-{device_data.get('device_manufacturer', '')}-{device_data.get('os_version', '')}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]


@router.post("/register")
async def register_device(device: DeviceRegistration):
    """
    Register a new device in SecureSphere
    Returns device_id for future authentication
    """
    db = dependencies.get_db()
    
    device_id = str(uuid4())
    fingerprint = generate_device_fingerprint(device.dict())
    
    # Check if device with same fingerprint exists for this user
    existing = await db.devices.find_one({
        "user_id": device.user_id,
        "fingerprint": fingerprint
    })
    
    if existing:
        return {
            "message": "Device already registered",
            "device_id": existing['device_id'],
            "registered_at": existing.get('registered_at')
        }
    
    # Create new device record
    device_record = {
        "device_id": device_id,
        "user_id": device.user_id,
        "fingerprint": fingerprint,
        "device_name": device.device_name,
        "platform": device.platform,
        "os_version": device.os_version,
        "device_model": device.device_model,
        "device_manufacturer": device.device_manufacturer,
        "app_version": device.app_version,
        "push_token": device.push_token,
        "security_features": {
            "biometric_enabled": device.biometric_enabled,
            "encryption_enabled": device.encryption_enabled,
            "screen_lock_enabled": device.screen_lock_enabled
        },
        "status": "active",
        "trust_level": "new",
        "latest_threat_score": 50,
        "security_posture": "unknown",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat()
    }
    
    await db.devices.insert_one(device_record)
    
    return {
        "message": "Device registered successfully",
        "device_id": device_id,
        "fingerprint": fingerprint,
        "trust_level": "new",
        "next_steps": [
            "Complete initial security scan",
            "Enable all security features",
            "Set up real-time protection"
        ]
    }


@router.get("/{device_id}")
async def get_device(device_id: str):
    """
    Get device details by device_id
    """
    db = dependencies.get_db()
    
    device = await db.devices.find_one(
        {"device_id": device_id},
        {"_id": 0}
    )
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device


@router.put("/{device_id}")
async def update_device(device_id: str, update: DeviceUpdate):
    """
    Update device information
    """
    db = dependencies.get_db()
    
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Handle security features separately
    security_updates = {}
    for key in ['biometric_enabled', 'encryption_enabled', 'screen_lock_enabled']:
        if key in update_data:
            security_updates[f"security_features.{key}"] = update_data.pop(key)
    
    update_data.update(security_updates)
    update_data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.devices.update_one(
        {"device_id": device_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"message": "Device updated successfully", "device_id": device_id}


@router.delete("/{device_id}")
async def deregister_device(device_id: str):
    """
    Deregister/remove a device
    """
    db = dependencies.get_db()
    
    result = await db.devices.update_one(
        {"device_id": device_id},
        {
            "$set": {
                "status": "deregistered",
                "deregistered_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"message": "Device deregistered successfully", "device_id": device_id}


@router.get("/user/{user_id}")
async def get_user_devices(user_id: str):
    """
    Get all devices for a user
    """
    db = dependencies.get_db()
    
    devices = await db.devices.find(
        {"user_id": user_id, "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "user_id": user_id,
        "total_devices": len(devices),
        "devices": devices
    }


@router.post("/{device_id}/heartbeat")
async def device_heartbeat(device_id: str, metadata: Optional[Dict] = None):
    """
    Device heartbeat - update last_seen timestamp
    """
    db = dependencies.get_db()
    
    update_data = {
        "last_seen": datetime.now(timezone.utc).isoformat()
    }
    
    if metadata:
        update_data["last_metadata"] = metadata
    
    result = await db.devices.update_one(
        {"device_id": device_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get current threat score
    device = await db.devices.find_one(
        {"device_id": device_id},
        {"_id": 0, "latest_threat_score": 1, "security_posture": 1}
    )
    
    return {
        "status": "ok",
        "device_id": device_id,
        "threat_score": device.get('latest_threat_score', 50) if device else 50,
        "security_posture": device.get('security_posture', 'unknown') if device else 'unknown'
    }


@router.put("/{device_id}/trust-level")
async def update_trust_level(device_id: str, trust_level: str):
    """
    Update device trust level
    Levels: new, trusted, verified, compromised
    """
    valid_levels = ['new', 'trusted', 'verified', 'compromised']
    if trust_level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid trust level. Must be one of: {valid_levels}")
    
    db = dependencies.get_db()
    
    result = await db.devices.update_one(
        {"device_id": device_id},
        {
            "$set": {
                "trust_level": trust_level,
                "trust_updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"message": f"Trust level updated to {trust_level}", "device_id": device_id}


@router.get("/stats/overview")
async def get_device_stats():
    """
    Get overall device statistics
    """
    db = dependencies.get_db()
    
    total_devices = await db.devices.count_documents({"status": "active"})
    
    # Platform breakdown
    platform_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$platform", "count": {"$sum": 1}}}
    ]
    platforms = await db.devices.aggregate(platform_pipeline).to_list(None)
    
    # Trust level breakdown
    trust_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$trust_level", "count": {"$sum": 1}}}
    ]
    trust_levels = await db.devices.aggregate(trust_pipeline).to_list(None)
    
    # Security posture breakdown
    posture_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$security_posture", "count": {"$sum": 1}}}
    ]
    postures = await db.devices.aggregate(posture_pipeline).to_list(None)
    
    return {
        "total_devices": total_devices,
        "by_platform": {p['_id']: p['count'] for p in platforms if p['_id']},
        "by_trust_level": {t['_id']: t['count'] for t in trust_levels if t['_id']},
        "by_security_posture": {p['_id']: p['count'] for p in postures if p['_id']},
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
