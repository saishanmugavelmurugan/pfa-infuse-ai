from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/organizations", tags=["Organizations"])

# Request/Response Models
class OrganizationCreate(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    industry: str
    company_size: str = Field(default="startup")  # startup, small, medium, large, enterprise
    website: Optional[str] = None
    country: str
    city: str
    billing_email: EmailStr

class OrganizationUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=200)
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    billing_email: Optional[EmailStr] = None

class TeamMemberAdd(BaseModel):
    user_email: EmailStr
    role: str = Field(default="member")  # admin, member, viewer

class OrganizationResponse(BaseModel):
    id: str
    company_name: str
    industry: str
    company_size: str
    website: Optional[str]
    country: str
    city: str
    admin_user_id: str
    team_members: List[str]
    subscription_tier: str
    subscription_status: str
    billing_email: str
    is_verified: bool
    created_at: str

# Routes
@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new organization - User becomes admin"""
    user_id = current_user["user_id"]
    
    # Check if user already has an organization as admin
    existing_org = await db.organizations.find_one(
        {"admin_user_id": user_id},
        {"_id": 0}
    )
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an organization"
        )
    
    # Create organization
    org_dict = {
        "id": str(uuid.uuid4()),
        "company_name": org_data.company_name,
        "industry": org_data.industry,
        "company_size": org_data.company_size,
        "website": org_data.website,
        "country": org_data.country,
        "city": org_data.city,
        "admin_user_id": user_id,
        "team_members": [user_id],  # Admin is also a team member
        "subscription_tier": "basic",  # Default to basic plan
        "subscription_status": "active",
        "subscription_start_date": datetime.now(timezone.utc).isoformat(),
        "subscription_end_date": None,
        "data_storage_used_gb": 0.0,
        "data_storage_limit_gb": 50.0,  # Basic plan limit
        "api_calls_this_month": 0,
        "api_calls_limit": 50000,  # Basic plan limit
        "billing_email": org_data.billing_email,
        "payment_method_id": None,
        "is_verified": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.organizations.insert_one(org_dict)
    
    return OrganizationResponse(**org_dict)

@router.get("/my-organization", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get current user's organization"""
    user_id = current_user["user_id"]
    
    # Find organization where user is admin or team member
    org = await db.organizations.find_one(
        {"$or": [
            {"admin_user_id": user_id},
            {"team_members": user_id}
        ]},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for this user"
        )
    
    return OrganizationResponse(**org)

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get organization by ID - must be team member"""
    user_id = current_user["user_id"]
    
    org = await db.organizations.find_one(
        {"id": org_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is team member
    if user_id not in org["team_members"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )
    
    return OrganizationResponse(**org)

@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_update: OrganizationUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update organization - admin only"""
    user_id = current_user["user_id"]
    
    org = await db.organizations.find_one(
        {"id": org_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is admin
    if org["admin_user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin can update organization"
        )
    
    # Update fields
    update_data = org_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.organizations.update_one(
            {"id": org_id},
            {"$set": update_data}
        )
        
        # Get updated organization
        org = await db.organizations.find_one(
            {"id": org_id},
            {"_id": 0}
        )
    
    return OrganizationResponse(**org)

@router.post("/{org_id}/team-members", status_code=status.HTTP_201_CREATED)
async def add_team_member(
    org_id: str,
    member_data: TeamMemberAdd,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Add team member to organization - admin only"""
    user_id = current_user["user_id"]
    
    org = await db.organizations.find_one(
        {"id": org_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is admin
    if org["admin_user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin can add team members"
        )
    
    # Find user by email
    new_member = await db.users.find_one(
        {"email": member_data.user_email},
        {"_id": 0}
    )
    
    if not new_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found with this email"
        )
    
    new_member_id = new_member["id"]
    
    # Check if already a member
    if new_member_id in org["team_members"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a team member"
        )
    
    # Add to team members
    await db.organizations.update_one(
        {"id": org_id},
        {
            "$push": {"team_members": new_member_id},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {
        "message": "Team member added successfully",
        "user_id": new_member_id,
        "user_email": member_data.user_email
    }

@router.delete("/{org_id}/team-members/{member_id}")
async def remove_team_member(
    org_id: str,
    member_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Remove team member from organization - admin only"""
    user_id = current_user["user_id"]
    
    org = await db.organizations.find_one(
        {"id": org_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is admin
    if org["admin_user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin can remove team members"
        )
    
    # Cannot remove admin
    if member_id == org["admin_user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization admin"
        )
    
    # Remove from team members
    await db.organizations.update_one(
        {"id": org_id},
        {
            "$pull": {"team_members": member_id},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Team member removed successfully"}

@router.get("/{org_id}/team-members")
async def get_team_members(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all team members - any team member can view"""
    user_id = current_user["user_id"]
    
    org = await db.organizations.find_one(
        {"id": org_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user is team member
    if user_id not in org["team_members"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view team members"
        )
    
    # Get user details for all team members
    team_member_ids = org["team_members"]
    members = await db.users.find(
        {"id": {"$in": team_member_ids}},
        {"_id": 0, "password_hash": 0}
    ).to_list(100)
    
    return {
        "organization_id": org_id,
        "team_members": members,
        "total_members": len(members)
    }
