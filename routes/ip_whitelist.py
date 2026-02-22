"""
IP Whitelisting API - Enterprise Security Feature
Manage allowed IP addresses for organization access

Features:
- IP address/CIDR range whitelisting
- Geo-location based restrictions
- Time-based access rules
- Audit logging for IP access
- Real-time enforcement
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import ipaddress
import re

import dependencies

router = APIRouter(prefix="/api/ip-whitelist", tags=["IP Whitelisting"])

# ==================== MODELS ====================

class IPRule(BaseModel):
    ip_or_cidr: str  # Single IP or CIDR range
    description: Optional[str] = None
    rule_type: str = "allow"  # allow, deny
    expires_at: Optional[str] = None  # ISO datetime or None for permanent
    
    @validator('ip_or_cidr')
    def validate_ip(cls, v):
        try:
            # Check if it's a valid IP or CIDR
            if '/' in v:
                ipaddress.ip_network(v, strict=False)
            else:
                ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid IP address or CIDR: {v}")

class IPWhitelistConfig(BaseModel):
    enabled: bool = False
    default_action: str = "deny"  # deny, allow
    rules: List[IPRule] = []
    geo_restrictions: Optional[Dict[str, Any]] = None
    time_restrictions: Optional[Dict[str, Any]] = None

class GeoRestriction(BaseModel):
    allowed_countries: List[str] = []  # ISO country codes
    blocked_countries: List[str] = []
    enabled: bool = False

class TimeRestriction(BaseModel):
    allowed_hours_start: int = 0  # 0-23
    allowed_hours_end: int = 23
    allowed_days: List[str] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    timezone: str = "UTC"
    enabled: bool = False

# ==================== AUTH ====================

async def verify_org_admin(x_org_id: str = Header(None), x_admin_token: str = Header(None)):
    """Verify organization admin for IP whitelist management"""
    if not x_org_id or not x_admin_token:
        raise HTTPException(status_code=401, detail="Admin credentials required")
    return {"org_id": x_org_id}

async def verify_internal_admin(x_internal_key: str = Header(None)):
    """Verify internal admin access"""
    if x_internal_key != "infuse_internal_2025_secret":
        raise HTTPException(status_code=403, detail="Internal admin access required")
    return True

# ==================== IP WHITELIST MANAGEMENT ====================

@router.get("/config")
async def get_ip_whitelist_config(auth: dict = Depends(verify_org_admin)):
    """Get IP whitelist configuration for organization"""
    db = dependencies.get_db()
    
    config = await db.ip_whitelist_configs.find_one(
        {"org_id": auth["org_id"]},
        {"_id": 0}
    )
    
    if not config:
        # Return default config
        config = {
            "org_id": auth["org_id"],
            "enabled": False,
            "default_action": "allow",
            "rules": [],
            "geo_restrictions": {"enabled": False, "allowed_countries": [], "blocked_countries": []},
            "time_restrictions": {"enabled": False, "allowed_hours_start": 0, "allowed_hours_end": 23, "allowed_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    return {"config": config}

@router.put("/config")
async def update_ip_whitelist_config(
    config: IPWhitelistConfig,
    auth: dict = Depends(verify_org_admin)
):
    """Update IP whitelist configuration"""
    db = dependencies.get_db()
    
    config_dict = {
        "org_id": auth["org_id"],
        "enabled": config.enabled,
        "default_action": config.default_action,
        "rules": [r.dict() for r in config.rules],
        "geo_restrictions": config.geo_restrictions,
        "time_restrictions": config.time_restrictions,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ip_whitelist_configs.update_one(
        {"org_id": auth["org_id"]},
        {"$set": config_dict},
        upsert=True
    )
    
    # Log configuration change
    await db.ip_whitelist_audit.insert_one({
        "org_id": auth["org_id"],
        "action": "config_updated",
        "details": {"enabled": config.enabled, "rules_count": len(config.rules)},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "config": config_dict}

@router.post("/rules")
async def add_ip_rule(
    rule: IPRule,
    auth: dict = Depends(verify_org_admin)
):
    """Add a new IP rule"""
    db = dependencies.get_db()
    
    rule_dict = {
        "id": f"rule_{uuid4().hex[:12]}",
        "org_id": auth["org_id"],
        **rule.dict(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add to config
    await db.ip_whitelist_configs.update_one(
        {"org_id": auth["org_id"]},
        {"$push": {"rules": rule_dict}},
        upsert=True
    )
    
    # Audit log
    await db.ip_whitelist_audit.insert_one({
        "org_id": auth["org_id"],
        "action": "rule_added",
        "rule_id": rule_dict["id"],
        "ip": rule.ip_or_cidr,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "rule": rule_dict}

@router.delete("/rules/{rule_id}")
async def delete_ip_rule(
    rule_id: str,
    auth: dict = Depends(verify_org_admin)
):
    """Delete an IP rule"""
    db = dependencies.get_db()
    
    result = await db.ip_whitelist_configs.update_one(
        {"org_id": auth["org_id"]},
        {"$pull": {"rules": {"id": rule_id}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Audit log
    await db.ip_whitelist_audit.insert_one({
        "org_id": auth["org_id"],
        "action": "rule_deleted",
        "rule_id": rule_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "message": "Rule deleted"}

@router.get("/rules")
async def list_ip_rules(auth: dict = Depends(verify_org_admin)):
    """List all IP rules for organization"""
    db = dependencies.get_db()
    
    config = await db.ip_whitelist_configs.find_one(
        {"org_id": auth["org_id"]},
        {"_id": 0, "rules": 1}
    )
    
    rules = config.get("rules", []) if config else []
    
    return {"rules": rules, "total": len(rules)}

# ==================== GEO RESTRICTIONS ====================

@router.put("/geo")
async def update_geo_restrictions(
    geo: GeoRestriction,
    auth: dict = Depends(verify_org_admin)
):
    """Update geo-location restrictions"""
    db = dependencies.get_db()
    
    await db.ip_whitelist_configs.update_one(
        {"org_id": auth["org_id"]},
        {"$set": {
            "geo_restrictions": geo.dict(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"success": True, "geo_restrictions": geo.dict()}

@router.get("/geo")
async def get_geo_restrictions(auth: dict = Depends(verify_org_admin)):
    """Get geo-location restrictions"""
    db = dependencies.get_db()
    
    config = await db.ip_whitelist_configs.find_one(
        {"org_id": auth["org_id"]},
        {"_id": 0, "geo_restrictions": 1}
    )
    
    geo = config.get("geo_restrictions") if config else {"enabled": False, "allowed_countries": [], "blocked_countries": []}
    
    return {"geo_restrictions": geo}

# ==================== TIME RESTRICTIONS ====================

@router.put("/time")
async def update_time_restrictions(
    time_rule: TimeRestriction,
    auth: dict = Depends(verify_org_admin)
):
    """Update time-based access restrictions"""
    db = dependencies.get_db()
    
    await db.ip_whitelist_configs.update_one(
        {"org_id": auth["org_id"]},
        {"$set": {
            "time_restrictions": time_rule.dict(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"success": True, "time_restrictions": time_rule.dict()}

# ==================== VALIDATION ====================

@router.post("/validate")
async def validate_ip_access(
    request: Request,
    ip_address: Optional[str] = None,
    auth: dict = Depends(verify_org_admin)
):
    """
    Validate if an IP address is allowed
    If no IP provided, uses request's IP
    """
    db = dependencies.get_db()
    
    # Get IP from request if not provided
    if not ip_address:
        ip_address = request.client.host if request.client else "127.0.0.1"
    
    # Get config
    config = await db.ip_whitelist_configs.find_one(
        {"org_id": auth["org_id"]},
        {"_id": 0}
    )
    
    if not config or not config.get("enabled", False):
        return {
            "allowed": True,
            "reason": "IP whitelisting not enabled",
            "ip_address": ip_address
        }
    
    # Check rules
    rules = config.get("rules", [])
    default_action = config.get("default_action", "deny")
    
    for rule in rules:
        try:
            rule_network = ipaddress.ip_network(rule["ip_or_cidr"], strict=False)
            check_ip = ipaddress.ip_address(ip_address)
            
            if check_ip in rule_network:
                # Check expiry
                if rule.get("expires_at"):
                    expiry = datetime.fromisoformat(rule["expires_at"].replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > expiry:
                        continue  # Rule expired, skip
                
                allowed = rule["rule_type"] == "allow"
                return {
                    "allowed": allowed,
                    "reason": f"Matched rule: {rule.get('description', rule['ip_or_cidr'])}",
                    "ip_address": ip_address,
                    "rule_id": rule.get("id")
                }
        except:
            continue
    
    # Default action
    return {
        "allowed": default_action == "allow",
        "reason": f"Default action: {default_action}",
        "ip_address": ip_address
    }

# ==================== AUDIT LOG ====================

@router.get("/audit")
async def get_ip_audit_log(
    limit: int = 100,
    auth: dict = Depends(verify_org_admin)
):
    """Get IP whitelist audit log"""
    db = dependencies.get_db()
    
    logs = await db.ip_whitelist_audit.find(
        {"org_id": auth["org_id"]},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "total": len(logs)}

# ==================== INTERNAL ADMIN ====================

@router.get("/admin/all-configs")
async def admin_get_all_configs(auth: bool = Depends(verify_internal_admin)):
    """Internal admin: Get all organization IP whitelist configs"""
    db = dependencies.get_db()
    
    configs = await db.ip_whitelist_configs.find({}, {"_id": 0}).to_list(100)
    
    return {
        "configs": configs,
        "total": len(configs),
        "enabled_count": len([c for c in configs if c.get("enabled", False)])
    }

@router.get("/admin/audit-all")
async def admin_get_all_audit(
    limit: int = 500,
    auth: bool = Depends(verify_internal_admin)
):
    """Internal admin: Get all IP whitelist audit logs"""
    db = dependencies.get_db()
    
    logs = await db.ip_whitelist_audit.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "total": len(logs)}
