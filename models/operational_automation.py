from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class AutomationRule(BaseModel):
    """
    Operational automation to reduce manual IT/Telco operations
    """
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    rule_name: str
    description: Optional[str] = None
    
    # Trigger conditions
    trigger_type: str  # threshold_breach, anomaly_detected, threat_identified, time_based, event_based
    trigger_conditions: Dict[str, Any]
    
    # Actions to execute
    actions: List[Dict] = Field(default_factory=list)  # {action_type, parameters}
    
    # Action types:
    # - block_ip
    # - rate_limit
    # - isolate_device
    # - update_firewall_rule
    # - restart_service
    # - send_alert
    # - create_ticket
    # - run_diagnostic
    # - backup_config
    
    # Execution settings
    is_active: bool = Field(default=True)
    auto_execute: bool = Field(default=True)
    require_approval: bool = Field(default=False)
    
    # Operational parameters
    cooldown_minutes: int = Field(default=5, ge=0)  # Prevent repeated execution
    max_executions_per_hour: int = Field(default=10, ge=1)
    
    # Tracking
    execution_count: int = Field(default=0, ge=0)
    last_executed: Optional[datetime] = None
    success_rate: float = Field(default=0.0, ge=0, le=100)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class AutomationExecution(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    rule_id: str
    
    # Execution details
    triggered_by: str  # event_id or user_id
    trigger_reason: str
    
    # Actions executed
    actions_executed: List[Dict] = Field(default_factory=list)
    
    # Results
    status: str  # success, partial_success, failed
    execution_time_ms: int
    
    # Impact
    devices_affected: List[str] = Field(default_factory=list)
    threats_mitigated: List[str] = Field(default_factory=list)
    
    # Logs
    execution_log: str
    error_log: Optional[str] = None
    
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class OperationalMetrics(BaseModel):
    """
    Metrics to demonstrate operational efficiency improvements
    """
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    
    # Time period
    period_start: datetime
    period_end: datetime
    
    # Manual operations reduced
    manual_operations_before: int
    automated_operations: int
    manual_operations_remaining: int
    automation_rate: float  # percentage
    
    # Time savings
    avg_manual_time_minutes: float
    total_time_saved_hours: float
    
    # Threat response
    avg_detection_time_seconds: float
    avg_mitigation_time_seconds: float
    threats_auto_mitigated: int
    threats_requiring_manual: int
    
    # Cost savings
    estimated_labor_cost_saved: float
    
    # Quality metrics
    false_positive_rate: float
    false_negative_rate: float
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}