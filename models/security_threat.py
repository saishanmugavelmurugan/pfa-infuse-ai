from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class SecurityThreat(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    
    # Threat identification
    threat_id: str  # Unique threat identifier
    threat_type: str  # ddos, port_scan, brute_force, malware, data_exfiltration, gsm_jamming, etc.
    severity: str  # low, medium, high, critical
    
    # Source and target
    source_device_id: Optional[str] = None
    source_ip: str
    source_country: Optional[str] = None
    target_device_id: Optional[str] = None
    target_ip: str
    target_port: Optional[int] = None
    
    # Threat details
    description: str
    indicators_of_compromise: List[str] = Field(default_factory=list)
    attack_vector: str
    
    # Detection information
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    detection_method: str  # netflow_analysis, signature, behavioral, ml_model, correlation
    confidence_score: float = Field(..., ge=0, le=100)
    
    # Impact assessment
    affected_devices: List[str] = Field(default_factory=list)
    estimated_impact: str  # low, medium, high, critical
    data_at_risk_gb: Optional[float] = Field(None, ge=0)
    
    # Response status
    status: str = Field(default="active")  # active, investigating, contained, mitigated, resolved
    auto_mitigated: bool = Field(default=False)
    mitigation_actions: List[Dict] = Field(default_factory=list)
    
    # Enforcement
    enforcement_applied: bool = Field(default=False)
    enforcement_type: Optional[str] = None  # block_ip, rate_limit, isolate_device, alert_only
    enforcement_timestamp: Optional[datetime] = None
    
    # AI analysis
    ai_analysis: Optional[Dict] = None
    predicted_progression: Optional[str] = None
    
    # Investigation
    assigned_to: Optional[str] = None  # user_id
    investigation_notes: List[Dict] = Field(default_factory=list)
    
    # Telco-specific
    is_telco_threat: bool = Field(default=False)
    gsm_related: bool = Field(default=False)
    
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

class SecurityPolicy(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    policy_name: str
    description: Optional[str] = None
    
    # Policy rules
    rules: List[Dict] = Field(default_factory=list)
    
    # Enforcement configuration
    enforcement_mode: str = Field(default="monitor")  # monitor, block, rate_limit, isolate
    auto_enforcement: bool = Field(default=False)
    enforcement_threshold: float = Field(default=80.0, ge=0, le=100)  # confidence threshold
    
    # Scope
    applies_to_devices: List[str] = Field(default_factory=list)  # device_ids or "all"
    applies_to_groups: List[str] = Field(default_factory=list)  # device_group_ids
    
    # Operational settings
    is_active: bool = Field(default=True)
    priority: int = Field(default=50, ge=0, le=100)
    
    # Notifications
    alert_on_trigger: bool = Field(default=True)
    notification_channels: List[str] = Field(default_factory=list)  # email, sms, slack, webhook
    
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class SecurityIncident(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    incident_id: str
    
    # Incident classification
    incident_type: str
    severity: str
    status: str = Field(default="open")  # open, investigating, contained, resolved, closed
    
    # Related threats
    threat_ids: List[str] = Field(default_factory=list)
    
    # Timeline
    first_detected: datetime
    last_activity: datetime
    resolved_at: Optional[datetime] = None
    
    # Impact
    affected_systems: List[str] = Field(default_factory=list)
    business_impact: str
    
    # Response
    response_actions: List[Dict] = Field(default_factory=list)
    responders: List[str] = Field(default_factory=list)  # user_ids
    
    # Root cause analysis
    root_cause: Optional[str] = None
    lessons_learned: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}