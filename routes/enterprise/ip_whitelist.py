"""
Enterprise IP Whitelisting
Restrict API access to specific IP addresses/ranges
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4
import ipaddress
import re

router = APIRouter(prefix="/api/enterprise/ip-whitelist", tags=["Enterprise IP Whitelist"])

# Get database
from dependencies import get_database


# Models
class IPWhitelistEntry(BaseModel):
    ip_address: str = Field(..., description="IP address or CIDR range")
    description: Optional[str] = None
    enabled: bool = True
    expires_at: Optional[str] = None
    
    @validator('ip_address')
    def validate_ip(cls, v):
        try:
            # Try parsing as single IP
            ipaddress.ip_address(v)
            return v
        except ValueError:
            pass
        
        try:
            # Try parsing as CIDR network
            ipaddress.ip_network(v, strict=False)
            return v
        except ValueError:
            raise ValueError(f"Invalid IP address or CIDR range: {v}")


class IPWhitelistConfig(BaseModel):
    enabled: bool = True
    enforcement_mode: str = Field(default="warn", description="Mode: warn, block, audit")
    apply_to: List[str] = Field(default=["api"], description="Apply to: api, admin, all")
    exempt_endpoints: List[str] = Field(default=[], description="Endpoints exempt from whitelist")


@router.get("/config")
async def get_whitelist_config(db=Depends(get_database)):
    """Get IP whitelist configuration"""
    config = await db.ip_whitelist_config.find_one({"type": "config"}, {"_id": 0})
    if not config:
        config = {
            "type": "config",
            "enabled": False,
            "enforcement_mode": "warn",
            "apply_to": ["api"],
            "exempt_endpoints": ["/api/health", "/api/auth/login", "/api/auth/register"]
        }
    return {"config": config}


@router.put("/config")
async def update_whitelist_config(config: IPWhitelistConfig, db=Depends(get_database)):
    """Update IP whitelist configuration"""
    config_data = {
        "type": "config",
        "enabled": config.enabled,
        "enforcement_mode": config.enforcement_mode,
        "apply_to": config.apply_to,
        "exempt_endpoints": config.exempt_endpoints,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ip_whitelist_config.update_one(
        {"type": "config"},
        {"$set": config_data},
        upsert=True
    )
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "ip_whitelist.config.updated",
        "resource_type": "ip_whitelist_config",
        "details": {"enabled": config.enabled, "mode": config.enforcement_mode},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "IP whitelist configuration updated", "config": config_data}


@router.post("/entries")
async def add_whitelist_entry(entry: IPWhitelistEntry, db=Depends(get_database)):
    """Add IP address/range to whitelist"""
    # Check for duplicates
    existing = await db.ip_whitelist.find_one({"ip_address": entry.ip_address})
    if existing:
        raise HTTPException(status_code=400, detail="IP address already in whitelist")
    
    entry_id = str(uuid4())
    entry_data = {
        "id": entry_id,
        "ip_address": entry.ip_address,
        "description": entry.description,
        "enabled": entry.enabled,
        "expires_at": entry.expires_at,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ip_whitelist.insert_one(entry_data)
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "ip_whitelist.entry.added",
        "resource_type": "ip_whitelist",
        "resource_id": entry_id,
        "details": {"ip_address": entry.ip_address},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"id": entry_id, "message": "IP address added to whitelist", "entry": entry_data}


@router.get("/entries")
async def list_whitelist_entries(enabled_only: bool = False, db=Depends(get_database)):
    """List all whitelist entries"""
    query = {}
    if enabled_only:
        query["enabled"] = True
    
    entries = await db.ip_whitelist.find(query, {"_id": 0}).to_list(1000)
    return {"entries": entries, "total": len(entries)}


@router.get("/entries/{entry_id}")
async def get_whitelist_entry(entry_id: str, db=Depends(get_database)):
    """Get whitelist entry details"""
    entry = await db.ip_whitelist.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")
    return entry


@router.put("/entries/{entry_id}")
async def update_whitelist_entry(entry_id: str, entry: IPWhitelistEntry, db=Depends(get_database)):
    """Update whitelist entry"""
    existing = await db.ip_whitelist.find_one({"id": entry_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")
    
    update_data = {
        "ip_address": entry.ip_address,
        "description": entry.description,
        "enabled": entry.enabled,
        "expires_at": entry.expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ip_whitelist.update_one({"id": entry_id}, {"$set": update_data})
    
    return {"message": "Whitelist entry updated"}


@router.delete("/entries/{entry_id}")
async def delete_whitelist_entry(entry_id: str, db=Depends(get_database)):
    """Delete whitelist entry"""
    result = await db.ip_whitelist.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "ip_whitelist.entry.deleted",
        "resource_type": "ip_whitelist",
        "resource_id": entry_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Whitelist entry deleted"}


@router.post("/entries/{entry_id}/toggle")
async def toggle_whitelist_entry(entry_id: str, db=Depends(get_database)):
    """Enable/disable whitelist entry"""
    entry = await db.ip_whitelist.find_one({"id": entry_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")
    
    new_status = not entry.get("enabled", True)
    await db.ip_whitelist.update_one(
        {"id": entry_id},
        {"$set": {"enabled": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"enabled": new_status, "message": f"Entry {'enabled' if new_status else 'disabled'}"}


@router.post("/verify")
async def verify_ip_address(request: Request, ip_address: Optional[str] = None, db=Depends(get_database)):
    """Verify if an IP address is whitelisted"""
    # Use provided IP or extract from request
    check_ip = ip_address or request.client.host
    
    # Get config
    config = await db.ip_whitelist_config.find_one({"type": "config"})
    if not config or not config.get("enabled"):
        return {"ip_address": check_ip, "whitelisted": True, "reason": "Whitelist not enabled"}
    
    # Get all enabled whitelist entries
    entries = await db.ip_whitelist.find({"enabled": True}, {"_id": 0}).to_list(1000)
    
    # Check if IP matches any entry
    try:
        check_ip_obj = ipaddress.ip_address(check_ip)
        
        for entry in entries:
            entry_ip = entry["ip_address"]
            try:
                # Check if it's a single IP
                if ipaddress.ip_address(entry_ip) == check_ip_obj:
                    return {
                        "ip_address": check_ip,
                        "whitelisted": True,
                        "matched_entry": entry["id"],
                        "description": entry.get("description")
                    }
            except ValueError:
                # Try as network range
                try:
                    if check_ip_obj in ipaddress.ip_network(entry_ip, strict=False):
                        return {
                            "ip_address": check_ip,
                            "whitelisted": True,
                            "matched_entry": entry["id"],
                            "matched_range": entry_ip,
                            "description": entry.get("description")
                        }
                except ValueError:
                    continue
        
        return {
            "ip_address": check_ip,
            "whitelisted": False,
            "reason": "IP not in whitelist"
        }
    
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid IP address: {check_ip}")


@router.get("/access-logs")
async def get_access_logs(blocked_only: bool = False, limit: int = 100, db=Depends(get_database)):
    """Get IP access logs"""
    query = {"event_type": {"$in": ["ip_whitelist.access.allowed", "ip_whitelist.access.blocked"]}}
    if blocked_only:
        query["event_type"] = "ip_whitelist.access.blocked"
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"logs": logs, "total": len(logs)}


@router.post("/bulk-add")
async def bulk_add_entries(entries: List[IPWhitelistEntry], db=Depends(get_database)):
    """Bulk add IP addresses to whitelist"""
    added = []
    skipped = []
    
    for entry in entries:
        existing = await db.ip_whitelist.find_one({"ip_address": entry.ip_address})
        if existing:
            skipped.append(entry.ip_address)
            continue
        
        entry_id = str(uuid4())
        entry_data = {
            "id": entry_id,
            "ip_address": entry.ip_address,
            "description": entry.description,
            "enabled": entry.enabled,
            "expires_at": entry.expires_at,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.ip_whitelist.insert_one(entry_data)
        added.append(entry.ip_address)
    
    return {
        "added": added,
        "skipped": skipped,
        "total_added": len(added),
        "total_skipped": len(skipped)
    }
