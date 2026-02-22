from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class CampaignObjective(BaseModel):
    primary: str  # awareness, consideration, conversion, retention
    kpis: List[str]  # reach, engagement, clicks, conversions, roi
    target_metrics: Dict[str, float] = Field(default_factory=dict)

class TargetAudience(BaseModel):
    demographics: Dict = Field(default_factory=dict)  # age, gender, location, income
    interests: List[str] = Field(default_factory=list)
    behaviors: List[str] = Field(default_factory=list)
    custom_segments: List[str] = Field(default_factory=list)  # segment_ids
    estimated_reach: Optional[int] = None

class CampaignBudget(BaseModel):
    total_budget: float = Field(ge=0)
    currency: str = Field(default="USD")
    daily_budget: Optional[float] = Field(None, ge=0)
    spent_amount: float = Field(default=0.0, ge=0)
    allocation: Dict[str, float] = Field(default_factory=dict)  # platform-wise allocation

class CampaignMetrics(BaseModel):
    impressions: int = Field(default=0, ge=0)
    reach: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    engagement_rate: float = Field(default=0.0, ge=0)
    click_through_rate: float = Field(default=0.0, ge=0)
    conversion_rate: float = Field(default=0.0, ge=0)
    cost_per_click: float = Field(default=0.0, ge=0)
    cost_per_conversion: float = Field(default=0.0, ge=0)
    roi: float = Field(default=0.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class Campaign(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    objective: CampaignObjective
    target_audience: TargetAudience
    budget: CampaignBudget
    platforms: List[str] = Field(default_factory=list)  # facebook, instagram, google, linkedin, etc.
    start_date: datetime
    end_date: datetime
    status: str = Field(default="draft")  # draft, planning, testing, active, paused, completed, cancelled
    creative_assets: List[str] = Field(default_factory=list)  # asset_ids
    ad_prototypes: List[str] = Field(default_factory=list)  # prototype_ids
    metrics: CampaignMetrics = Field(default_factory=CampaignMetrics)
    ai_insights: List[Dict] = Field(default_factory=list)
    created_by: str  # user_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}

class AdPrototype(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    campaign_id: str
    company_id: str
    name: str
    ad_type: str  # image, video, carousel, story, banner
    platform: str  # facebook, instagram, youtube, google_display, etc.
    creative_url: Optional[str] = None
    headline: str
    body_text: Optional[str] = None
    call_to_action: str
    dimensions: Dict = Field(default_factory=dict)  # width, height, aspect_ratio
    duration_seconds: Optional[int] = None  # for video ads
    test_audience_size: int = Field(default=1000, ge=100)
    test_metrics: Dict = Field(default_factory=dict)
    ai_score: Optional[float] = Field(None, ge=0, le=100)
    ai_recommendations: List[str] = Field(default_factory=list)
    status: str = Field(default="draft")  # draft, testing, approved, rejected, live
    variants: List[Dict] = Field(default_factory=list)  # A/B test variants
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}