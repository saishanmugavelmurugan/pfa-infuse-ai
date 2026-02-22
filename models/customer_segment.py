from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class SegmentCriteria(BaseModel):
    demographics: Dict = Field(default_factory=dict)
    behaviors: Dict = Field(default_factory=dict)
    psychographics: Dict = Field(default_factory=dict)
    purchase_history: Dict = Field(default_factory=dict)
    engagement_level: Optional[str] = None
    custom_attributes: Dict = Field(default_factory=dict)

class CustomerSegment(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    criteria: SegmentCriteria
    segment_size: int = Field(default=0, ge=0)
    avg_customer_value: float = Field(default=0.0, ge=0)
    avg_purchase_frequency: float = Field(default=0.0, ge=0)
    conversion_rate: float = Field(default=0.0, ge=0, le=100)
    churn_rate: float = Field(default=0.0, ge=0, le=100)
    lifetime_value: float = Field(default=0.0, ge=0)
    growth_rate: float = Field(default=0.0)  # can be negative
    top_products: List[str] = Field(default_factory=list)
    top_channels: List[str] = Field(default_factory=list)
    ai_insights: Dict = Field(default_factory=dict)
    recommended_actions: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)
    last_analyzed: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class CustomerProfile(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    customer_id: str  # External customer ID from company's system
    email: Optional[str] = None
    phone: Optional[str] = None
    demographics: Dict = Field(default_factory=dict)
    segments: List[str] = Field(default_factory=list)  # segment_ids
    purchase_history: List[Dict] = Field(default_factory=list)
    engagement_score: float = Field(default=0.0, ge=0, le=100)
    lifetime_value: float = Field(default=0.0, ge=0)
    churn_probability: float = Field(default=0.0, ge=0, le=100)
    preferences: Dict = Field(default_factory=dict)
    interactions: List[Dict] = Field(default_factory=list)
    last_interaction: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}