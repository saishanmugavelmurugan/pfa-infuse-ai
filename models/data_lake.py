from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class DataSource(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    name: str
    source_type: str  # website_analytics, social_media, crm, email, ads, ecommerce, custom
    platform: str  # google_analytics, facebook, salesforce, mailchimp, shopify, etc.
    connection_status: str = Field(default="disconnected")  # connected, disconnected, error
    credentials_encrypted: Optional[str] = None
    sync_frequency: str = Field(default="daily")  # realtime, hourly, daily, weekly
    last_sync: Optional[datetime] = None
    records_synced: int = Field(default=0, ge=0)
    data_size_mb: float = Field(default=0.0, ge=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class DataRecord(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    source_id: str
    record_type: str  # pageview, click, purchase, lead, impression, etc.
    timestamp: datetime
    data: Dict[str, Any]  # Flexible schema for different data types
    processed: bool = Field(default=False)
    enriched_data: Optional[Dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

class DataPipeline(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    name: str
    description: Optional[str] = None
    source_ids: List[str]  # List of data_source ids
    transformations: List[Dict] = Field(default_factory=list)
    destination: str  # data_warehouse, analytics, ml_model, export
    schedule: str = Field(default="daily")
    is_active: bool = Field(default=True)
    last_run: Optional[datetime] = None
    records_processed: int = Field(default=0, ge=0)
    status: str = Field(default="idle")  # idle, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class MarketingInsight(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    insight_type: str  # trend, anomaly, opportunity, risk, prediction
    title: str
    description: str
    impact_level: str  # low, medium, high, critical
    confidence_score: float = Field(..., ge=0, le=100)
    data_sources: List[str]  # source_ids
    metrics_affected: List[str]
    recommended_actions: List[str] = Field(default_factory=list)
    is_acted_upon: bool = Field(default=False)
    generated_by: str = Field(default="ai")  # ai, user, system
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class PreLaunchAnalysis(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    campaign_id: str
    analysis_type: str  # feasibility, market_fit, budget_optimization, audience_validation
    market_size: Optional[int] = None
    estimated_reach: Optional[int] = None
    estimated_engagement_rate: float = Field(default=0.0, ge=0, le=100)
    estimated_conversion_rate: float = Field(default=0.0, ge=0, le=100)
    estimated_roi: float = Field(default=0.0)
    risk_factors: List[Dict] = Field(default_factory=list)
    opportunities: List[Dict] = Field(default_factory=list)
    competitor_analysis: Dict = Field(default_factory=dict)
    budget_recommendation: Dict = Field(default_factory=dict)
    go_no_go_recommendation: str  # go, no_go, optimize_first
    confidence_level: float = Field(..., ge=0, le=100)
    ai_analysis: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}