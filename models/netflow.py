from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class NetFlowRecord(BaseModel):
    """
    Enterprise/Telco-grade NetFlow record for traffic analysis
    Supports NetFlow v5, v9, and IPFIX formats
    """
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    device_id: str  # Source device
    
    # Flow identification (5-tuple)
    src_ip: str
    dst_ip: str
    src_port: int = Field(..., ge=0, le=65535)
    dst_port: int = Field(..., ge=0, le=65535)
    protocol: int = Field(..., ge=0, le=255)  # TCP=6, UDP=17, ICMP=1
    
    # Flow metrics
    bytes_transferred: int = Field(ge=0)
    packets: int = Field(ge=0)
    flow_duration_ms: int = Field(ge=0)
    
    # Timestamps
    flow_start: datetime
    flow_end: datetime
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Network context
    input_interface: Optional[int] = None
    output_interface: Optional[int] = None
    next_hop: Optional[str] = None
    src_as: Optional[int] = None  # Autonomous System
    dst_as: Optional[int] = None
    
    # TCP flags
    tcp_flags: Optional[str] = None
    
    # Telco-specific
    is_gsm_traffic: bool = Field(default=False)
    gsm_cell_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    
    # Security analysis
    threat_score: float = Field(default=0.0, ge=0, le=100)
    is_anomalous: bool = Field(default=False)
    anomaly_reasons: List[str] = Field(default_factory=list)
    is_blocked: bool = Field(default=False)
    
    # Geolocation
    src_country: Optional[str] = None
    dst_country: Optional[str] = None
    src_city: Optional[str] = None
    dst_city: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

class FlowAggregate(BaseModel):
    """
    Aggregated flow statistics for operational efficiency
    Reduces storage and improves query performance
    """
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    device_id: str
    
    # Time window
    window_start: datetime
    window_end: datetime
    window_duration_minutes: int = Field(default=5)
    
    # Aggregated metrics
    total_flows: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    total_packets: int = Field(ge=0)
    unique_src_ips: int = Field(ge=0)
    unique_dst_ips: int = Field(ge=0)
    unique_protocols: List[int] = Field(default_factory=list)
    
    # Top talkers
    top_source_ips: List[Dict] = Field(default_factory=list)
    top_destination_ips: List[Dict] = Field(default_factory=list)
    top_ports: List[Dict] = Field(default_factory=list)
    
    # Security metrics
    suspicious_flows: int = Field(default=0, ge=0)
    blocked_flows: int = Field(default=0, ge=0)
    anomaly_score: float = Field(default=0.0, ge=0, le=100)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

class TrafficBaseline(BaseModel):
    """
    Baseline traffic patterns for anomaly detection
    Machine learning powered baselines
    """
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    device_id: Optional[str] = None  # None for company-wide baseline
    
    # Baseline metrics
    time_of_day: str  # hourly buckets: 00-01, 01-02, etc.
    day_of_week: str  # Monday, Tuesday, etc.
    
    avg_bytes_per_second: float = Field(ge=0)
    avg_packets_per_second: float = Field(ge=0)
    avg_flows_per_second: float = Field(ge=0)
    
    # Statistical bounds
    bytes_std_dev: float = Field(ge=0)
    packets_std_dev: float = Field(ge=0)
    
    # Protocol distribution
    protocol_distribution: Dict[str, float] = Field(default_factory=dict)
    
    # Port usage patterns
    common_ports: List[int] = Field(default_factory=list)
    
    # Learning period
    learning_period_days: int = Field(default=30)
    samples_collected: int = Field(ge=0)
    confidence_level: float = Field(default=0.0, ge=0, le=100)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}