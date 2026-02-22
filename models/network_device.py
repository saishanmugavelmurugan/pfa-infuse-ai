from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class NetworkDevice(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    device_id: str  # Unique device identifier (MAC, IMEI, Serial)
    device_name: str
    device_type: str  # router, switch, firewall, iot_sensor, gsm_gateway, base_station, server, endpoint
    manufacturer: str
    model: str
    firmware_version: str
    ip_address: str
    mac_address: Optional[str] = None
    location: str
    network_zone: str  # dmz, internal, external, iot, telco_core
    criticality: str = Field(default="medium")  # low, medium, high, critical
    
    # Telco-specific fields
    is_telco_equipment: bool = Field(default=False)
    gsm_network_type: Optional[str] = None  # 2G, 3G, 4G, 5G
    carrier: Optional[str] = None
    imei: Optional[str] = None
    
    # Security status
    security_status: str = Field(default="protected")  # protected, vulnerable, compromised, unknown
    last_scan: Optional[datetime] = None
    vulnerabilities_count: int = Field(default=0, ge=0)
    threats_blocked: int = Field(default=0, ge=0)
    
    # NetFlow configuration
    netflow_enabled: bool = Field(default=True)
    netflow_collector: Optional[str] = None
    flow_export_rate: int = Field(default=1000, ge=0)  # flows per second
    
    # Operational data
    is_online: bool = Field(default=True)
    uptime_hours: float = Field(default=0.0, ge=0)
    cpu_usage: Optional[float] = Field(None, ge=0, le=100)
    memory_usage: Optional[float] = Field(None, ge=0, le=100)
    bandwidth_usage_mbps: Optional[float] = Field(None, ge=0)
    
    # Compliance
    compliance_status: str = Field(default="compliant")  # compliant, non_compliant, unknown
    last_compliance_check: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class DeviceGroup(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    name: str
    description: Optional[str] = None
    device_ids: List[str] = Field(default_factory=list)
    security_policies: List[str] = Field(default_factory=list)  # policy_ids
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}