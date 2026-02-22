"""
Enterprise API Key Management
Create, manage, and monitor API keys for enterprise integrations
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import secrets
import hashlib

router = APIRouter(prefix="/api/admin/api-keys", tags=["Admin - API Keys"])

# Get database
from dependencies import get_database


# Models
class APIKeyCreate(BaseModel):
    name: str = Field(..., description="Display name for the API key")
    description: Optional[str] = None
    permissions: List[str] = Field(default=["read"], description="Permissions: read, write, admin")
    rate_limit: int = Field(default=1000, description="Requests per hour")
    expires_at: Optional[str] = None
    allowed_ips: Optional[List[str]] = None
    allowed_origins: Optional[List[str]] = None


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    rate_limit: Optional[int] = None
    expires_at: Optional[str] = None
    allowed_ips: Optional[List[str]] = None
    allowed_origins: Optional[List[str]] = None
    enabled: Optional[bool] = None


def generate_api_key() -> tuple:
    """Generate a new API key and its hash"""
    key = f"infuse_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash


@router.post("")
@router.post("/")
async def create_api_key(key_data: APIKeyCreate, db=Depends(get_database)):
    """Create a new API key"""
    key_id = str(uuid4())
    api_key, key_hash = generate_api_key()
    
    key_record = {
        "id": key_id,
        "name": key_data.name,
        "description": key_data.description,
        "key_hash": key_hash,
        "key_prefix": api_key[:12] + "...",  # Store prefix for identification
        "permissions": key_data.permissions,
        "rate_limit": key_data.rate_limit,
        "expires_at": key_data.expires_at,
        "allowed_ips": key_data.allowed_ips,
        "allowed_origins": key_data.allowed_origins,
        "enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_used_at": None,
        "usage_count": 0
    }
    
    await db.api_keys.insert_one(key_record)
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "api_key.created",
        "category": "api",
        "resource_type": "api_key",
        "resource_id": key_id,
        "details": {"name": key_data.name, "permissions": key_data.permissions},
        "severity": "info",
        "outcome": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Return the full key only once - it won't be retrievable again
    return {
        "id": key_id,
        "api_key": api_key,
        "name": key_data.name,
        "permissions": key_data.permissions,
        "rate_limit": key_data.rate_limit,
        "message": "Save this API key securely. It won't be shown again."
    }


@router.get("")
@router.get("/")
async def list_api_keys(enabled_only: bool = False, db=Depends(get_database)):
    """List all API keys (without the actual key values)"""
    query = {}
    if enabled_only:
        query["enabled"] = True
    
    keys = await db.api_keys.find(query, {"_id": 0, "key_hash": 0}).to_list(100)
    return {"api_keys": keys, "total": len(keys)}


@router.get("/{key_id}")
async def get_api_key(key_id: str, db=Depends(get_database)):
    """Get API key details"""
    key = await db.api_keys.find_one({"id": key_id}, {"_id": 0, "key_hash": 0})
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.put("/{key_id}")
async def update_api_key(key_id: str, update_data: APIKeyUpdate, db=Depends(get_database)):
    """Update API key settings"""
    existing = await db.api_keys.find_one({"id": key_id})
    if not existing:
        raise HTTPException(status_code=404, detail="API key not found")
    
    update_fields = {k: v for k, v in update_data.dict().items() if v is not None}
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.api_keys.update_one({"id": key_id}, {"$set": update_fields})
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "api_key.updated",
        "category": "api",
        "resource_type": "api_key",
        "resource_id": key_id,
        "details": {"updated_fields": list(update_fields.keys())},
        "severity": "info",
        "outcome": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "API key updated successfully"}


@router.delete("/{key_id}")
async def revoke_api_key(key_id: str, db=Depends(get_database)):
    """Revoke/delete an API key"""
    result = await db.api_keys.delete_one({"id": key_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "api_key.revoked",
        "category": "api",
        "resource_type": "api_key",
        "resource_id": key_id,
        "severity": "warning",
        "outcome": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "API key revoked successfully"}


@router.post("/{key_id}/toggle")
async def toggle_api_key(key_id: str, db=Depends(get_database)):
    """Enable or disable an API key"""
    key = await db.api_keys.find_one({"id": key_id})
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    new_status = not key.get("enabled", True)
    await db.api_keys.update_one(
        {"id": key_id},
        {"$set": {"enabled": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"enabled": new_status, "message": f"API key {'enabled' if new_status else 'disabled'}"}


@router.post("/{key_id}/regenerate")
async def regenerate_api_key(key_id: str, db=Depends(get_database)):
    """Regenerate an API key (creates new key, invalidates old)"""
    existing = await db.api_keys.find_one({"id": key_id})
    if not existing:
        raise HTTPException(status_code=404, detail="API key not found")
    
    new_key, new_hash = generate_api_key()
    
    await db.api_keys.update_one(
        {"id": key_id},
        {"$set": {
            "key_hash": new_hash,
            "key_prefix": new_key[:12] + "...",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "api_key.regenerated",
        "category": "api",
        "resource_type": "api_key",
        "resource_id": key_id,
        "severity": "warning",
        "outcome": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "id": key_id,
        "api_key": new_key,
        "message": "API key regenerated. Save this new key securely."
    }


@router.get("/{key_id}/usage")
async def get_api_key_usage(key_id: str, days: int = 30, db=Depends(get_database)):
    """Get usage statistics for an API key"""
    key = await db.api_keys.find_one({"id": key_id}, {"_id": 0, "key_hash": 0})
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get usage logs
    usage_logs = await db.api_key_usage.find(
        {"key_id": key_id, "timestamp": {"$gte": date_from}},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(1000)
    
    # Calculate statistics
    total_requests = len(usage_logs)
    successful = sum(1 for log in usage_logs if log.get("status_code", 200) < 400)
    failed = total_requests - successful
    
    # Group by day
    daily_usage = {}
    for log in usage_logs:
        day = log["timestamp"][:10]
        if day not in daily_usage:
            daily_usage[day] = 0
        daily_usage[day] += 1
    
    return {
        "key_id": key_id,
        "key_name": key["name"],
        "period_days": days,
        "total_requests": total_requests,
        "successful_requests": successful,
        "failed_requests": failed,
        "daily_usage": daily_usage,
        "last_used_at": key.get("last_used_at"),
        "rate_limit": key.get("rate_limit")
    }


@router.post("/validate")
async def validate_api_key(api_key: str, db=Depends(get_database)):
    """Validate an API key"""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_record = await db.api_keys.find_one({"key_hash": key_hash, "enabled": True})
    
    if not key_record:
        return {"valid": False, "reason": "Invalid or disabled API key"}
    
    # Check expiration
    if key_record.get("expires_at"):
        if datetime.fromisoformat(key_record["expires_at"].replace('Z', '+00:00')) < datetime.now(timezone.utc):
            return {"valid": False, "reason": "API key expired"}
    
    # Update last used
    await db.api_keys.update_one(
        {"id": key_record["id"]},
        {"$set": {"last_used_at": datetime.now(timezone.utc).isoformat()}, "$inc": {"usage_count": 1}}
    )
    
    return {
        "valid": True,
        "key_id": key_record["id"],
        "name": key_record["name"],
        "permissions": key_record["permissions"],
        "rate_limit": key_record["rate_limit"]
    }
