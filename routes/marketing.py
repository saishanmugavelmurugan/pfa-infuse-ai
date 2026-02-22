from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/marketing", tags=["MarketLake AI"])

# Models
class Company(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    industry: str
    size: str = Field(..., pattern="^(startup|small|medium|large|enterprise)$")
    website: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2)
    industry: str
    size: str = Field(..., pattern="^(startup|small|medium|large|enterprise)$")
    website: Optional[str] = None

class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    name: str
    budget: float = Field(..., ge=0)
    target_audience: str
    channels: List[str] = []
    status: str = Field(default="draft", pattern="^(draft|active|paused|completed)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    metrics: Dict[str, float] = {}
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CampaignCreate(BaseModel):
    company_id: str
    name: str = Field(..., min_length=2)
    budget: float = Field(..., ge=0)
    target_audience: str
    channels: List[str] = []
    status: str = Field(default="draft", pattern="^(draft|active|paused|completed)$")
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class CustomerSegment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    name: str
    criteria: Dict[str, str] = {}
    size: int = Field(default=0, ge=0)
    demographics: Dict[str, str] = {}
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CustomerSegmentCreate(BaseModel):
    company_id: str
    name: str = Field(..., min_length=2)
    criteria: Dict[str, str] = {}
    demographics: Dict[str, str] = {}

class AdPrototype(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    title: str
    description: str
    image_url: Optional[str] = None
    cta_text: str
    target_url: str
    ai_generated: bool = False
    performance_score: Optional[float] = Field(default=None, ge=0, le=100)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AdPrototypeCreate(BaseModel):
    campaign_id: str
    title: str = Field(..., min_length=2)
    description: str
    image_url: Optional[str] = None
    cta_text: str
    target_url: str
    ai_generated: bool = False

class DataLakeEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str
    data_type: str = Field(..., pattern="^(customer|campaign|analytics|market_research)$")
    source: str
    data: Dict = {}
    tags: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DataLakeEntryCreate(BaseModel):
    company_id: str
    data_type: str = Field(..., pattern="^(customer|campaign|analytics|market_research)$")
    source: str
    data: Dict = {}
    tags: List[str] = []

class CampaignStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(draft|active|paused|completed)$")

class CampaignMetricsUpdate(BaseModel):
    metrics: Dict[str, float]

# Company Endpoints
@router.post("/companies", response_model=Company, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_data: CompanyCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new company"""
    company_dict = Company(**company_data.model_dump()).model_dump()
    await db.companies.insert_one(company_dict)
    return company_dict

@router.get("/companies", response_model=List[Company])
async def get_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all companies"""
    companies = await db.companies.find({}, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return companies

@router.get("/companies/{company_id}", response_model=Company)
async def get_company(
    company_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific company"""
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.put("/companies/{company_id}", response_model=Company)
async def update_company(
    company_id: str,
    company_data: CompanyCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update a company"""
    existing = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Company not found")
    
    updated_data = company_data.model_dump()
    updated_data["id"] = company_id
    updated_data["created_at"] = existing["created_at"]
    
    await db.companies.update_one({"id": company_id}, {"$set": updated_data})
    return updated_data

@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a company"""
    result = await db.companies.delete_one({"id": company_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Company not found")

# Campaign Endpoints
@router.post("/campaigns", response_model=Campaign, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new marketing campaign"""
    campaign_dict = Campaign(**campaign_data.model_dump()).model_dump()
    campaign_dict["metrics"] = {
        "impressions": 0,
        "clicks": 0,
        "conversions": 0,
        "spend": 0,
        "roi": 0
    }
    await db.campaigns.insert_one(campaign_dict)
    return campaign_dict

@router.get("/campaigns", response_model=List[Campaign])
async def get_campaigns(
    company_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get campaigns with optional filters"""
    query = {}
    if company_id:
        query["company_id"] = company_id
    if status_filter:
        query["status"] = status_filter
    
    campaigns = await db.campaigns.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return campaigns

@router.get("/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.put("/campaigns/{campaign_id}/status", response_model=Campaign)
async def update_campaign_status(
    campaign_id: str,
    status_data: CampaignStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update campaign status"""
    result = await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": status_data.status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    updated = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return updated

@router.put("/campaigns/{campaign_id}/metrics", response_model=Campaign)
async def update_campaign_metrics(
    campaign_id: str,
    metrics_data: CampaignMetricsUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update campaign metrics"""
    result = await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"metrics": metrics_data.metrics}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    updated = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return updated

# Customer Segment Endpoints
@router.post("/segments", response_model=CustomerSegment, status_code=status.HTTP_201_CREATED)
async def create_segment(
    segment_data: CustomerSegmentCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a customer segment"""
    segment_dict = CustomerSegment(**segment_data.model_dump()).model_dump()
    await db.customer_segments.insert_one(segment_dict)
    return segment_dict

@router.get("/segments", response_model=List[CustomerSegment])
async def get_segments(
    company_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get customer segments"""
    query = {"company_id": company_id} if company_id else {}
    segments = await db.customer_segments.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return segments

@router.get("/segments/{segment_id}", response_model=CustomerSegment)
async def get_segment(
    segment_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific customer segment"""
    segment = await db.customer_segments.find_one({"id": segment_id}, {"_id": 0})
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment

# Ad Prototype Endpoints
@router.post("/ads", response_model=AdPrototype, status_code=status.HTTP_201_CREATED)
async def create_ad_prototype(
    ad_data: AdPrototypeCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create an ad prototype"""
    ad_dict = AdPrototype(**ad_data.model_dump()).model_dump()
    await db.ad_prototypes.insert_one(ad_dict)
    return ad_dict

@router.get("/ads", response_model=List[AdPrototype])
async def get_ad_prototypes(
    campaign_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get ad prototypes"""
    query = {"campaign_id": campaign_id} if campaign_id else {}
    ads = await db.ad_prototypes.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return ads

@router.get("/ads/{ad_id}", response_model=AdPrototype)
async def get_ad_prototype(
    ad_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific ad prototype"""
    ad = await db.ad_prototypes.find_one({"id": ad_id}, {"_id": 0})
    if not ad:
        raise HTTPException(status_code=404, detail="Ad prototype not found")
    return ad

# Data Lake Endpoints
@router.post("/datalake", response_model=DataLakeEntry, status_code=status.HTTP_201_CREATED)
async def create_datalake_entry(
    entry_data: DataLakeEntryCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Add entry to data lake"""
    entry_dict = DataLakeEntry(**entry_data.model_dump()).model_dump()
    await db.data_lake.insert_one(entry_dict)
    return entry_dict

@router.get("/datalake", response_model=List[DataLakeEntry])
async def get_datalake_entries(
    company_id: Optional[str] = None,
    data_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get data lake entries"""
    query = {}
    if company_id:
        query["company_id"] = company_id
    if data_type:
        query["data_type"] = data_type
    
    entries = await db.data_lake.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return entries

@router.get("/datalake/{entry_id}", response_model=DataLakeEntry)
async def get_datalake_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a specific data lake entry"""
    entry = await db.data_lake.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Data lake entry not found")
    return entry

# Analytics Endpoint
@router.get("/analytics/overview")
async def get_analytics_overview(
    company_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get marketing analytics overview for a company"""
    # Get campaign counts by status
    campaigns = await db.campaigns.find({"company_id": company_id}, {"_id": 0}).to_list(1000)
    
    total_campaigns = len(campaigns)
    active_campaigns = len([c for c in campaigns if c.get("status") == "active"])
    total_budget = sum([c.get("budget", 0) for c in campaigns])
    
    # Calculate total metrics
    total_impressions = sum([c.get("metrics", {}).get("impressions", 0) for c in campaigns])
    total_clicks = sum([c.get("metrics", {}).get("clicks", 0) for c in campaigns])
    total_conversions = sum([c.get("metrics", {}).get("conversions", 0) for c in campaigns])
    total_spend = sum([c.get("metrics", {}).get("spend", 0) for c in campaigns])
    
    # Get segment count
    segment_count = await db.customer_segments.count_documents({"company_id": company_id})
    
    # Get ad prototype count
    ad_count = await db.ad_prototypes.count_documents({})
    
    return {
        "company_id": company_id,
        "campaigns": {
            "total": total_campaigns,
            "active": active_campaigns,
            "total_budget": total_budget
        },
        "performance": {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "conversions": total_conversions,
            "spend": total_spend,
            "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
            "conversion_rate": (total_conversions / total_clicks * 100) if total_clicks > 0 else 0
        },
        "segments": segment_count,
        "ad_prototypes": ad_count
    }
