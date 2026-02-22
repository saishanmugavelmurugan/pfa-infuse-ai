"""
License Management System
Manage enterprise licenses, subscriptions, and feature access
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import secrets

router = APIRouter(prefix="/api/admin/licenses", tags=["Admin - Licenses"])

# Get database
from dependencies import get_database


# License Tiers
LICENSE_TIERS = {
    "starter": {
        "name": "Starter",
        "max_users": 10,
        "products": ["healthtrack"],
        "features": ["basic_reports", "email_support"],
        "api_calls_per_month": 10000,
        "data_retention_days": 30
    },
    "professional": {
        "name": "Professional",
        "max_users": 50,
        "products": ["healthtrack", "securesphere"],
        "features": ["basic_reports", "advanced_reports", "api_access", "email_support", "chat_support"],
        "api_calls_per_month": 100000,
        "data_retention_days": 90
    },
    "enterprise": {
        "name": "Enterprise",
        "max_users": -1,  # Unlimited
        "products": ["healthtrack", "securesphere"],
        "features": ["basic_reports", "advanced_reports", "api_access", "sso", "audit_logs", "custom_integrations", "dedicated_support", "sla"],
        "api_calls_per_month": -1,  # Unlimited
        "data_retention_days": 365
    },
    "trial": {
        "name": "Trial",
        "max_users": 5,
        "products": ["healthtrack", "securesphere"],
        "features": ["basic_reports", "api_access"],
        "api_calls_per_month": 1000,
        "data_retention_days": 14,
        "trial_days": 14
    }
}


# Models
class LicenseCreate(BaseModel):
    organization_name: str
    tier: str = Field(..., description="License tier: starter, professional, enterprise, trial")
    admin_email: str
    valid_months: int = Field(default=12, description="License validity in months")
    custom_max_users: Optional[int] = None
    custom_features: Optional[List[str]] = None
    notes: Optional[str] = None


class LicenseUpdate(BaseModel):
    tier: Optional[str] = None
    custom_max_users: Optional[int] = None
    custom_features: Optional[List[str]] = None
    extends_months: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None


def generate_license_key() -> str:
    """Generate a unique license key"""
    key_parts = [
        secrets.token_hex(4).upper(),
        secrets.token_hex(4).upper(),
        secrets.token_hex(4).upper(),
        secrets.token_hex(4).upper()
    ]
    return "-".join(key_parts)


@router.get("/tiers")
async def get_license_tiers():
    """Get available license tiers and their features"""
    return {"tiers": LICENSE_TIERS}


@router.post("/")
async def create_license(license_data: LicenseCreate, db=Depends(get_database)):
    """Create a new license"""
    if license_data.tier not in LICENSE_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Available: {list(LICENSE_TIERS.keys())}")
    
    tier_config = LICENSE_TIERS[license_data.tier]
    license_id = str(uuid4())
    license_key = generate_license_key()
    
    # Calculate validity
    now = datetime.now(timezone.utc)
    if license_data.tier == "trial":
        valid_until = now + timedelta(days=tier_config.get("trial_days", 14))
    else:
        valid_until = now + timedelta(days=license_data.valid_months * 30)
    
    license_record = {
        "id": license_id,
        "license_key": license_key,
        "license_key_hash": hashlib.sha256(license_key.encode()).hexdigest(),
        "organization_name": license_data.organization_name,
        "admin_email": license_data.admin_email,
        "tier": license_data.tier,
        "tier_name": tier_config["name"],
        "max_users": license_data.custom_max_users or tier_config["max_users"],
        "products": tier_config["products"],
        "features": license_data.custom_features or tier_config["features"],
        "api_calls_per_month": tier_config["api_calls_per_month"],
        "data_retention_days": tier_config["data_retention_days"],
        "status": "active",
        "created_at": now.isoformat(),
        "valid_from": now.isoformat(),
        "valid_until": valid_until.isoformat(),
        "notes": license_data.notes,
        "usage": {
            "current_users": 0,
            "api_calls_this_month": 0,
            "last_reset": now.isoformat()
        }
    }
    
    await db.licenses.insert_one(license_record)
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "license.created",
        "category": "configuration",
        "resource_type": "license",
        "resource_id": license_id,
        "details": {"tier": license_data.tier, "organization": license_data.organization_name},
        "severity": "info",
        "outcome": "success",
        "timestamp": now.isoformat()
    })
    
    return {
        "id": license_id,
        "license_key": license_key,
        "organization": license_data.organization_name,
        "tier": license_data.tier,
        "valid_until": valid_until.isoformat(),
        "message": "License created successfully. Save the license key securely."
    }


@router.get("/")
async def list_licenses(status: Optional[str] = None, tier: Optional[str] = None, db=Depends(get_database)):
    """List all licenses"""
    query = {}
    if status:
        query["status"] = status
    if tier:
        query["tier"] = tier
    
    licenses = await db.licenses.find(query, {"_id": 0, "license_key": 0, "license_key_hash": 0}).to_list(1000)
    return {"licenses": licenses, "total": len(licenses)}


@router.get("/{license_id}")
async def get_license(license_id: str, db=Depends(get_database)):
    """Get license details"""
    license_record = await db.licenses.find_one({"id": license_id}, {"_id": 0, "license_key": 0, "license_key_hash": 0})
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")
    return license_record


@router.put("/{license_id}")
async def update_license(license_id: str, update_data: LicenseUpdate, db=Depends(get_database)):
    """Update license settings"""
    license_record = await db.licenses.find_one({"id": license_id})
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")
    
    update_fields = {}
    
    if update_data.tier and update_data.tier in LICENSE_TIERS:
        tier_config = LICENSE_TIERS[update_data.tier]
        update_fields["tier"] = update_data.tier
        update_fields["tier_name"] = tier_config["name"]
        update_fields["products"] = tier_config["products"]
        update_fields["features"] = tier_config["features"]
        update_fields["api_calls_per_month"] = tier_config["api_calls_per_month"]
    
    if update_data.custom_max_users:
        update_fields["max_users"] = update_data.custom_max_users
    
    if update_data.custom_features:
        update_fields["features"] = update_data.custom_features
    
    if update_data.extends_months:
        current_valid = datetime.fromisoformat(license_record["valid_until"].replace('Z', '+00:00'))
        new_valid = current_valid + timedelta(days=update_data.extends_months * 30)
        update_fields["valid_until"] = new_valid.isoformat()
    
    if update_data.status:
        update_fields["status"] = update_data.status
    
    if update_data.notes:
        update_fields["notes"] = update_data.notes
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.licenses.update_one({"id": license_id}, {"$set": update_fields})
    
    return {"message": "License updated successfully"}


@router.post("/{license_id}/activate")
async def activate_license(license_id: str, db=Depends(get_database)):
    """Activate a license"""
    result = await db.licenses.update_one(
        {"id": license_id},
        {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="License not found")
    return {"message": "License activated"}


@router.post("/{license_id}/suspend")
async def suspend_license(license_id: str, reason: Optional[str] = None, db=Depends(get_database)):
    """Suspend a license"""
    result = await db.licenses.update_one(
        {"id": license_id},
        {"$set": {
            "status": "suspended",
            "suspension_reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="License not found")
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "license.suspended",
        "category": "configuration",
        "resource_type": "license",
        "resource_id": license_id,
        "details": {"reason": reason},
        "severity": "warning",
        "outcome": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "License suspended"}


@router.post("/validate")
async def validate_license(license_key: str, db=Depends(get_database)):
    """Validate a license key"""
    key_hash = hashlib.sha256(license_key.encode()).hexdigest()
    license_record = await db.licenses.find_one({"license_key_hash": key_hash})
    
    if not license_record:
        return {"valid": False, "reason": "Invalid license key"}
    
    # Check status
    if license_record["status"] != "active":
        return {"valid": False, "reason": f"License is {license_record['status']}"}
    
    # Check expiration
    valid_until = datetime.fromisoformat(license_record["valid_until"].replace('Z', '+00:00'))
    if valid_until < datetime.now(timezone.utc):
        return {"valid": False, "reason": "License expired"}
    
    # Check user limit
    max_users = license_record["max_users"]
    current_users = license_record["usage"]["current_users"]
    if max_users > 0 and current_users >= max_users:
        return {"valid": False, "reason": "User limit reached"}
    
    return {
        "valid": True,
        "license_id": license_record["id"],
        "organization": license_record["organization_name"],
        "tier": license_record["tier"],
        "products": license_record["products"],
        "features": license_record["features"],
        "valid_until": license_record["valid_until"],
        "users_remaining": max_users - current_users if max_users > 0 else "unlimited"
    }


@router.get("/{license_id}/usage")
async def get_license_usage(license_id: str, db=Depends(get_database)):
    """Get license usage statistics"""
    license_record = await db.licenses.find_one({"id": license_id}, {"_id": 0})
    if not license_record:
        raise HTTPException(status_code=404, detail="License not found")
    
    usage = license_record.get("usage", {})
    
    return {
        "license_id": license_id,
        "organization": license_record["organization_name"],
        "tier": license_record["tier"],
        "users": {
            "current": usage.get("current_users", 0),
            "max": license_record["max_users"],
            "available": license_record["max_users"] - usage.get("current_users", 0) if license_record["max_users"] > 0 else "unlimited"
        },
        "api_calls": {
            "this_month": usage.get("api_calls_this_month", 0),
            "limit": license_record["api_calls_per_month"],
            "remaining": license_record["api_calls_per_month"] - usage.get("api_calls_this_month", 0) if license_record["api_calls_per_month"] > 0 else "unlimited"
        },
        "valid_until": license_record["valid_until"],
        "days_remaining": (datetime.fromisoformat(license_record["valid_until"].replace('Z', '+00:00')) - datetime.now(timezone.utc)).days
    }


@router.post("/{license_id}/reset-usage")
async def reset_license_usage(license_id: str, db=Depends(get_database)):
    """Reset monthly API usage counter"""
    result = await db.licenses.update_one(
        {"id": license_id},
        {"$set": {
            "usage.api_calls_this_month": 0,
            "usage.last_reset": datetime.now(timezone.utc).isoformat()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="License not found")
    return {"message": "Usage counter reset"}
