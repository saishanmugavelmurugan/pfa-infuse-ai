from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/security", tags=["SecureSphere"])

# Admin-only access check
async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role for security endpoints"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin role required for security features."
        )
    return current_user

# Models
class NetworkDevice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    ip_address: str
    mac_address: Optional[str] = None
    device_type: str = Field(..., pattern="^(router|switch|firewall|server|iot|endpoint|workstation|automotive|cctv|white_goods|mobile)$")
    location: Optional[str] = None
    os: Optional[str] = None
    segment: Optional[str] = None
    status: str = Field(default="active", pattern="^(active|inactive|compromised|maintenance|warning)$")
    threats: int = Field(default=0)
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class NetworkDeviceCreate(BaseModel):
    name: str = Field(..., min_length=2)
    ip_address: str
    mac_address: Optional[str] = None
    device_type: str = Field(..., pattern="^(router|switch|firewall|server|iot|endpoint|workstation|automotive|cctv|white_goods|mobile)$")
    location: Optional[str] = None
    os: Optional[str] = None
    segment: Optional[str] = None

class SecurityThreat(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    threat_type: str = Field(..., pattern="^(malware|intrusion|ddos|phishing|data_breach|unauthorized_access|other)$")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    source_ip: Optional[str] = None
    target_ip: Optional[str] = None
    device_id: Optional[str] = None
    description: str
    status: str = Field(default="detected", pattern="^(detected|investigating|mitigated|resolved|false_positive)$")
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SecurityThreatCreate(BaseModel):
    threat_type: str = Field(..., pattern="^(malware|intrusion|ddos|phishing|data_breach|unauthorized_access|other)$")
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    source_ip: Optional[str] = None
    target_ip: Optional[str] = None
    device_id: Optional[str] = None
    description: str

class SecurityPolicy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    policy_type: str = Field(..., pattern="^(firewall|access_control|encryption|monitoring|compliance)$")
    rules: List[Dict] = []
    enabled: bool = True
    priority: int = Field(default=50, ge=1, le=100)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SecurityPolicyCreate(BaseModel):
    name: str = Field(..., min_length=2)
    policy_type: str = Field(..., pattern="^(firewall|access_control|encryption|monitoring|compliance)$")
    rules: List[Dict] = []
    enabled: bool = True
    priority: int = Field(default=50, ge=1, le=100)

class NetFlowRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    protocol: str
    bytes_transferred: int = Field(default=0, ge=0)
    packets: int = Field(default=0, ge=0)
    flow_start: str
    flow_end: str
    flags: List[str] = []
    anomaly_score: Optional[float] = Field(default=None, ge=0, le=100)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class NetFlowRecordCreate(BaseModel):
    source_ip: str
    destination_ip: str
    source_port: int
    destination_port: int
    protocol: str
    bytes_transferred: int = Field(default=0, ge=0)
    packets: int = Field(default=0, ge=0)
    flow_start: str
    flow_end: str
    flags: List[str] = []

class ThreatIntelligence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    indicator_type: str = Field(..., pattern="^(ip|domain|hash|url|email)$")
    indicator_value: str
    threat_type: str
    confidence: float = Field(..., ge=0, le=100)
    source: str
    description: Optional[str] = None
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ThreatIntelligenceCreate(BaseModel):
    indicator_type: str = Field(..., pattern="^(ip|domain|hash|url|email)$")
    indicator_value: str
    threat_type: str
    confidence: float = Field(..., ge=0, le=100)
    source: str
    description: Optional[str] = None

class ThreatStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(detected|investigating|mitigated|resolved|false_positive)$")

class DeviceStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|inactive|compromised|maintenance)$")

# Network Device Endpoints
@router.post("/devices", response_model=NetworkDevice, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_data: NetworkDeviceCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Register a new network device"""
    device_dict = NetworkDevice(**device_data.model_dump()).model_dump()
    await db.network_devices.insert_one(device_dict)
    return device_dict

@router.get("/devices", response_model=List[NetworkDevice])
async def get_devices(
    device_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get network devices with optional filters"""
    query = {}
    if device_type:
        query["device_type"] = device_type
    if status_filter:
        query["status"] = status_filter
    
    devices = await db.network_devices.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return devices

@router.get("/devices/{device_id}", response_model=NetworkDevice)
async def get_device(
    device_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get a specific network device"""
    device = await db.network_devices.find_one({"id": device_id}, {"_id": 0})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.put("/devices/{device_id}/status", response_model=NetworkDevice)
async def update_device_status(
    device_id: str,
    status_data: DeviceStatusUpdate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Update device status"""
    result = await db.network_devices.update_one(
        {"id": device_id},
        {"$set": {
            "status": status_data.status,
            "last_seen": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    updated = await db.network_devices.find_one({"id": device_id}, {"_id": 0})
    return updated

@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Delete a network device"""
    result = await db.network_devices.delete_one({"id": device_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")

# Security Threat Endpoints
@router.post("/threats", response_model=SecurityThreat, status_code=status.HTTP_201_CREATED)
async def create_threat(
    threat_data: SecurityThreatCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Report a new security threat"""
    threat_dict = SecurityThreat(**threat_data.model_dump()).model_dump()
    await db.security_threats.insert_one(threat_dict)
    return threat_dict

@router.get("/threats", response_model=List[SecurityThreat])
async def get_threats(
    severity: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    threat_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get security threats with optional filters"""
    query = {}
    if severity:
        query["severity"] = severity
    if status_filter:
        query["status"] = status_filter
    if threat_type:
        query["threat_type"] = threat_type
    
    threats = await db.security_threats.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return threats

@router.get("/threats/{threat_id}", response_model=SecurityThreat)
async def get_threat(
    threat_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get a specific security threat"""
    threat = await db.security_threats.find_one({"id": threat_id}, {"_id": 0})
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")
    return threat

@router.put("/threats/{threat_id}/status", response_model=SecurityThreat)
async def update_threat_status(
    threat_id: str,
    status_data: ThreatStatusUpdate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Update threat status"""
    update_data = {"status": status_data.status}
    
    # If resolving, set resolved_at timestamp
    if status_data.status == "resolved":
        update_data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.security_threats.update_one(
        {"id": threat_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Threat not found")
    
    updated = await db.security_threats.find_one({"id": threat_id}, {"_id": 0})
    return updated

# Security Policy Endpoints
@router.post("/policies", response_model=SecurityPolicy, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_data: SecurityPolicyCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Create a security policy"""
    policy_dict = SecurityPolicy(**policy_data.model_dump()).model_dump()
    await db.security_policies.insert_one(policy_dict)
    return policy_dict

@router.get("/policies", response_model=List[SecurityPolicy])
async def get_policies(
    policy_type: Optional[str] = None,
    enabled_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get security policies"""
    query = {}
    if policy_type:
        query["policy_type"] = policy_type
    if enabled_only:
        query["enabled"] = True
    
    policies = await db.security_policies.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return policies

@router.get("/policies/{policy_id}", response_model=SecurityPolicy)
async def get_policy(
    policy_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get a specific security policy"""
    policy = await db.security_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.put("/policies/{policy_id}", response_model=SecurityPolicy)
async def update_policy(
    policy_id: str,
    policy_data: SecurityPolicyCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Update a security policy"""
    existing = await db.security_policies.find_one({"id": policy_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    updated_data = policy_data.model_dump()
    updated_data["id"] = policy_id
    updated_data["created_at"] = existing["created_at"]
    updated_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.security_policies.update_one({"id": policy_id}, {"$set": updated_data})
    return updated_data

@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Delete a security policy"""
    result = await db.security_policies.delete_one({"id": policy_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Policy not found")

# NetFlow Endpoints
@router.post("/netflow", response_model=NetFlowRecord, status_code=status.HTTP_201_CREATED)
async def create_netflow_record(
    record_data: NetFlowRecordCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Record a NetFlow entry"""
    record_dict = NetFlowRecord(**record_data.model_dump()).model_dump()
    await db.netflow_records.insert_one(record_dict)
    return record_dict

@router.get("/netflow", response_model=List[NetFlowRecord])
async def get_netflow_records(
    source_ip: Optional[str] = None,
    destination_ip: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get NetFlow records with optional filters"""
    query = {}
    if source_ip:
        query["source_ip"] = source_ip
    if destination_ip:
        query["destination_ip"] = destination_ip
    
    records = await db.netflow_records.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return records

@router.get("/netflow/{record_id}", response_model=NetFlowRecord)
async def get_netflow_record(
    record_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get a specific NetFlow record"""
    record = await db.netflow_records.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="NetFlow record not found")
    return record

# Threat Intelligence Endpoints
@router.post("/threat-intel", response_model=ThreatIntelligence, status_code=status.HTTP_201_CREATED)
async def create_threat_intel(
    intel_data: ThreatIntelligenceCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Add threat intelligence data"""
    intel_dict = ThreatIntelligence(**intel_data.model_dump()).model_dump()
    await db.threat_intelligence.insert_one(intel_dict)
    return intel_dict

@router.get("/threat-intel", response_model=List[ThreatIntelligence])
async def get_threat_intel(
    indicator_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get threat intelligence data"""
    query = {"indicator_type": indicator_type} if indicator_type else {}
    intel = await db.threat_intelligence.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return intel

@router.get("/threat-intel/search")
async def search_threat_intel(
    indicator_value: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Search for threat intelligence by indicator value"""
    intel = await db.threat_intelligence.find_one(
        {"indicator_value": indicator_value},
        {"_id": 0}
    )
    
    if not intel:
        return {"found": False, "indicator_value": indicator_value}
    
    return {"found": True, "data": intel}

# Analytics Endpoint
@router.get("/analytics/dashboard")
async def get_security_dashboard(
    current_user: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """Get security analytics dashboard data"""
    # Get threat counts by severity
    threats = await db.security_threats.find({}, {"_id": 0}).to_list(1000)
    
    threat_by_severity = {
        "critical": len([t for t in threats if t.get("severity") == "critical"]),
        "high": len([t for t in threats if t.get("severity") == "high"]),
        "medium": len([t for t in threats if t.get("severity") == "medium"]),
        "low": len([t for t in threats if t.get("severity") == "low"])
    }
    
    threat_by_status = {
        "detected": len([t for t in threats if t.get("status") == "detected"]),
        "investigating": len([t for t in threats if t.get("status") == "investigating"]),
        "mitigated": len([t for t in threats if t.get("status") == "mitigated"]),
        "resolved": len([t for t in threats if t.get("status") == "resolved"])
    }
    
    # Get device counts
    device_count = await db.network_devices.count_documents({})
    active_devices = await db.network_devices.count_documents({"status": "active"})
    compromised_devices = await db.network_devices.count_documents({"status": "compromised"})
    
    # Get policy count
    policy_count = await db.security_policies.count_documents({})
    enabled_policies = await db.security_policies.count_documents({"enabled": True})
    
    # Get NetFlow stats
    netflow_count = await db.netflow_records.count_documents({})
    
    return {
        "threats": {
            "total": len(threats),
            "by_severity": threat_by_severity,
            "by_status": threat_by_status
        },
        "devices": {
            "total": device_count,
            "active": active_devices,
            "compromised": compromised_devices,
            "healthy_percentage": (active_devices / device_count * 100) if device_count > 0 else 0
        },
        "policies": {
            "total": policy_count,
            "enabled": enabled_policies
        },
        "netflow": {
            "total_records": netflow_count
        }
    }
