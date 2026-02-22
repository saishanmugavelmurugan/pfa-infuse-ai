from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from bson import ObjectId
from models.user import PyObjectId

class CompanyProfile(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_name: str = Field(..., min_length=2, max_length=200)
    industry: str
    company_size: str  # startup, small, medium, large, enterprise
    website: Optional[str] = None
    country: str
    city: str
    admin_user_id: str  # Reference to User who is admin
    team_members: List[str] = Field(default_factory=list)  # List of user_ids
    subscription_tier: str = Field(default="free")  # free, basic, professional, enterprise
    subscription_status: str = Field(default="active")  # active, suspended, cancelled
    subscription_start_date: datetime = Field(default_factory=datetime.utcnow)
    subscription_end_date: Optional[datetime] = None
    data_storage_used_gb: float = Field(default=0.0, ge=0)
    data_storage_limit_gb: float = Field(default=10.0, ge=0)
    api_calls_this_month: int = Field(default=0, ge=0)
    api_calls_limit: int = Field(default=10000, ge=0)
    billing_email: EmailStr
    payment_method_id: Optional[str] = None
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class BrandAsset(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    asset_type: str  # logo, color_palette, font, image, video, template
    name: str
    description: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)  # color codes, font details, etc.
    tags: List[str] = Field(default_factory=list)
    is_primary: bool = Field(default=False)
    created_by: str  # user_id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class BrandGuidelines(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    company_id: str
    brand_name: str
    tagline: Optional[str] = None
    brand_voice: str  # professional, casual, friendly, authoritative, etc.
    target_audience: Dict = Field(default_factory=dict)
    primary_colors: List[str] = Field(default_factory=list)  # hex codes
    secondary_colors: List[str] = Field(default_factory=list)
    typography: Dict = Field(default_factory=dict)  # {primary_font, secondary_font, sizes}
    logo_usage: Dict = Field(default_factory=dict)
    imagery_style: str
    dos_and_donts: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}