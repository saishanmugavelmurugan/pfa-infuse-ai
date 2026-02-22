"""
vRAN Integration Models - Scalable Threat Detection System
Supports: Telco, Mobile User, Enterprise, Automotive segments
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums for type safety
class SegmentType(str, Enum):
    TELCO = "telco"
    MOBILE = "mobile"
    ENTERPRISE = "enterprise"
    AUTOMOTIVE = "automotive"
    WHITE_GOODS = "white_goods"  # IoT appliances
    CCTV = "cctv"  # Surveillance cameras

class ConnectionType(str, Enum):
    MOBILE_NUMBER = "mobile_number"
    APN = "apn"
    IMSI = "imsi"
    IMEI = "imei"
    IP_RANGE = "ip_range"
    DOMAIN = "domain"
    VIN = "vin"
    ESIM = "esim"
    MAC_ADDRESS = "mac_address"
    DEVICE_ID = "device_id"
    CAMERA_ID = "camera_id"
    STREAM_URL = "stream_url"

class ThreatSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatAction(str, Enum):
    DETECT = "detect"      # Monitor and log
    PROTECT = "protect"    # Alert and quarantine
    ENFORCE = "enforce"    # Block and report

class AlertChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# vRAN Connection Models
class VRANConnectionBase(BaseModel):
    user_id: str
    segment: SegmentType
    connection_type: ConnectionType
    identifier: str  # Mobile number, APN, IMSI, etc.
    description: Optional[str] = None

class VRANConnectionCreate(VRANConnectionBase):
    pass

class VRANConnection(VRANConnectionBase):
    id: str
    status: str = "active"
    vran_session_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    threat_score: float = 0.0
    created_at: datetime
    updated_at: datetime

# Identifier Models per Segment
class TelcoIdentifier(BaseModel):
    msisdn: Optional[str] = None  # Phone number
    imsi: Optional[str] = None    # SIM identity
    iccid: Optional[str] = None   # SIM serial
    imei_range_start: Optional[str] = None
    imei_range_end: Optional[str] = None
    apn: Optional[str] = None     # Access Point Name
    network_code: Optional[str] = None  # MCC-MNC

class MobileIdentifier(BaseModel):
    phone_number: str
    imei: Optional[str] = None
    device_id: Optional[str] = None
    os_type: Optional[str] = None  # android/ios
    apn: Optional[str] = None

class EnterpriseIdentifier(BaseModel):
    ip_address: Optional[str] = None
    ip_range_cidr: Optional[str] = None
    domain: Optional[str] = None
    api_key_hash: Optional[str] = None
    certificate_fingerprint: Optional[str] = None
    apn: Optional[str] = None

class AutomotiveIdentifier(BaseModel):
    vin: str  # Vehicle Identification Number
    esim_iccid: Optional[str] = None
    telematics_unit_id: Optional[str] = None
    apn: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None

class WhiteGoodsIdentifier(BaseModel):
    """IoT Appliances - Smart Home Devices"""
    device_id: str
    mac_address: Optional[str] = None
    imei: Optional[str] = None  # For cellular-connected devices
    apn: Optional[str] = None
    serial_number: Optional[str] = None
    device_type: Optional[str] = None  # refrigerator, washer, ac, tv, etc.
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    wifi_ssid: Optional[str] = None

class CCTVIdentifier(BaseModel):
    """Surveillance Cameras - Public & Private"""
    camera_id: str
    camera_type: str = "private"  # public, private
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    stream_url: Optional[str] = None
    apn: Optional[str] = None  # For cellular cameras
    imei: Optional[str] = None  # For 4G/5G cameras
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    firmware_version: Optional[str] = None
    resolution: Optional[str] = None
    is_ptz: Optional[bool] = False  # Pan-Tilt-Zoom capability
    has_audio: Optional[bool] = False
    storage_type: Optional[str] = None  # local, cloud, nvr

# Bulk Upload Models
class BulkUploadRequest(BaseModel):
    segment: SegmentType
    file_type: str = "csv"  # csv, json
    identifiers: List[Dict[str, Any]]
    priority: str = "normal"  # normal, high, urgent

class BulkUploadJob(BaseModel):
    id: str
    user_id: str
    segment: SegmentType
    status: JobStatus = JobStatus.PENDING
    total_records: int
    processed_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    error_log: List[Dict] = []
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# Threat Models
class ThreatIndicator(BaseModel):
    id: str
    indicator_type: str  # ip, domain, hash, pattern
    indicator_value: str
    severity: ThreatSeverity
    source: str  # internal, external_feed, ai_detected
    confidence_score: float
    description: str
    tags: List[str] = []
    first_seen: datetime
    last_seen: datetime
    is_active: bool = True

class ThreatEvent(BaseModel):
    id: str
    connection_id: str
    user_id: str
    segment: SegmentType
    identifier: str
    threat_type: str
    severity: ThreatSeverity
    action_taken: ThreatAction
    details: Dict[str, Any]
    ai_analysis: Optional[str] = None
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class ThreatAnalysisRequest(BaseModel):
    connection_id: str
    identifier: str
    segment: SegmentType
    data_payload: Optional[Dict[str, Any]] = None

class ThreatAnalysisResult(BaseModel):
    connection_id: str
    threat_detected: bool
    threat_score: float  # 0-100
    severity: ThreatSeverity
    recommended_action: ThreatAction
    threats_found: List[Dict[str, Any]]
    ai_summary: str
    analysis_time_ms: int

# Alert Models
class AlertConfig(BaseModel):
    user_id: str
    segment: SegmentType
    channels: List[AlertChannel]
    severity_threshold: ThreatSeverity = ThreatSeverity.MEDIUM
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    enabled: bool = True

class Alert(BaseModel):
    id: str
    user_id: str
    connection_id: str
    threat_event_id: str
    channel: AlertChannel
    severity: ThreatSeverity
    title: str
    message: str
    status: str = "pending"  # pending, sent, delivered, failed
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime

# AI Learning Models
class AILearningEvent(BaseModel):
    id: str
    event_type: str  # new_pattern, updated_rule, false_positive
    source_data: Dict[str, Any]
    learned_pattern: Dict[str, Any]
    confidence: float
    applied_to_rules: bool = False
    created_at: datetime

class ThreatRule(BaseModel):
    id: str
    name: str
    description: str
    segment: Optional[SegmentType] = None  # None = all segments
    pattern: Dict[str, Any]  # Detection pattern/regex
    severity: ThreatSeverity
    action: ThreatAction
    ai_generated: bool = False
    confidence_score: float = 1.0
    hit_count: int = 0
    false_positive_count: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
