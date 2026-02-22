"""
Team Management API for Enterprise Users
Allows enterprise organizations to invite and manage team members
for both HealthTrack Pro and SecureSphere platforms
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import secrets
import hashlib

from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/api/team", tags=["Team Management"])


# ==================== MODELS ====================

class TeamInvite(BaseModel):
    email: EmailStr
    name: str
    role: str = "member"  # admin, manager, member, viewer
    platforms: List[str] = ["healthtrack", "securesphere"]  # which platforms user can access
    department: Optional[str] = None

class InviteResponse(BaseModel):
    invite_id: str
    email: str
    invite_link: str
    expires_at: str

class AcceptInvite(BaseModel):
    invite_token: str
    password: str
    phone: Optional[str] = None

class TeamMemberUpdate(BaseModel):
    role: Optional[str] = None
    platforms: Optional[List[str]] = None
    department: Optional[str] = None
    status: Optional[str] = None


# ==================== INVITE MANAGEMENT ====================

@router.post("/invite", response_model=InviteResponse)
async def invite_team_member(
    invite: TeamInvite,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Invite a new team member to the organization.
    Only admins and managers can invite new members.
    """
    user_id = current_user["user_id"]
    
    # Get user's organization
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if current user has permission to invite
    membership = await db.unified_memberships.find_one(
        {"user_id": user_id, "org_id": org["id"], "status": "active"},
        {"_id": 0}
    )
    
    if not membership or membership.get("role") not in ["admin", "manager"]:
        # Check if user is org admin
        if org.get("admin_user_id") != user_id:
            raise HTTPException(status_code=403, detail="Only admins and managers can invite team members")
    
    # Check if email already exists in organization
    existing = await db.team_invites.find_one({
        "org_id": org["id"],
        "email": invite.email,
        "status": "pending"
    })
    if existing:
        raise HTTPException(status_code=400, detail="An invitation for this email already exists")
    
    existing_member = await db.users.find_one({"email": invite.email}, {"_id": 0})
    if existing_member:
        # Check if already in org
        existing_membership = await db.unified_memberships.find_one({
            "user_id": existing_member["id"],
            "org_id": org["id"],
            "status": "active"
        })
        if existing_membership:
            raise HTTPException(status_code=400, detail="User is already a member of this organization")
    
    # Generate invite token
    invite_token = secrets.token_urlsafe(32)
    invite_id = str(uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    invite_record = {
        "id": invite_id,
        "org_id": org["id"],
        "org_name": org.get("name", "Organization"),
        "email": invite.email,
        "name": invite.name,
        "role": invite.role,
        "platforms": invite.platforms,
        "department": invite.department,
        "token": invite_token,
        "token_hash": hashlib.sha256(invite_token.encode()).hexdigest(),
        "invited_by": user_id,
        "invited_by_name": current_user.get("name", "Admin"),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at
    }
    
    await db.team_invites.insert_one(invite_record)
    
    # Generate invite link
    base_url = "https://caretrack-68.preview.emergentagent.com"
    invite_link = f"{base_url}/accept-invite?token={invite_token}"
    
    return {
        "invite_id": invite_id,
        "email": invite.email,
        "invite_link": invite_link,
        "expires_at": expires_at
    }


@router.get("/invites")
async def list_pending_invites(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all pending invitations for the organization"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    invites = await db.team_invites.find(
        {"org_id": org["id"], "status": "pending"},
        {"_id": 0, "token": 0, "token_hash": 0}
    ).to_list(100)
    
    return {
        "total": len(invites),
        "invites": invites
    }


@router.delete("/invites/{invite_id}")
async def cancel_invite(
    invite_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Cancel a pending invitation"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    result = await db.team_invites.update_one(
        {"id": invite_id, "org_id": org["id"], "status": "pending"},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Invitation not found or already processed")
    
    return {"status": "cancelled", "invite_id": invite_id}


@router.post("/accept-invite")
async def accept_invitation(
    data: AcceptInvite,
    db = Depends(get_db)
):
    """
    Accept an invitation and create user account.
    The invited user can set their own password.
    """
    # Find invitation by token hash
    token_hash = hashlib.sha256(data.invite_token.encode()).hexdigest()
    
    invite = await db.team_invites.find_one(
        {"token_hash": token_hash, "status": "pending"},
        {"_id": 0}
    )
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    
    # Check if expired
    if datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        await db.team_invites.update_one(
            {"id": invite["id"]},
            {"$set": {"status": "expired"}}
        )
        raise HTTPException(status_code=400, detail="Invitation has expired")
    
    # Check if email already registered
    existing_user = await db.users.find_one({"email": invite["email"]}, {"_id": 0})
    
    if existing_user:
        # User exists, just add to organization
        user_id = existing_user["id"]
    else:
        # Create new user account
        import bcrypt
        
        user_id = str(uuid4())
        password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
        
        user_record = {
            "id": user_id,
            "email": invite["email"],
            "name": invite["name"],
            "password_hash": password_hash,
            "hashed_password": password_hash,  # For compatibility
            "phone": data.phone,
            "role": invite["role"],
            "organization_id": invite["org_id"],
            "platforms": invite["platforms"],
            "department": invite.get("department"),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_via": "team_invite"
        }
        
        await db.users.insert_one(user_record)
    
    # Add to organization membership
    from services.multi_tenant_service import MultiTenantService
    multi_tenant = MultiTenantService()
    
    await multi_tenant.add_user_to_organization(
        org_id=invite["org_id"],
        user_id=user_id,
        role=invite["role"],
        platforms=invite["platforms"]
    )
    
    # Update invite status
    await db.team_invites.update_one(
        {"id": invite["id"]},
        {
            "$set": {
                "status": "accepted",
                "accepted_at": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id
            }
        }
    )
    
    return {
        "status": "success",
        "message": "Account created successfully. You can now login.",
        "email": invite["email"],
        "organization": invite["org_name"],
        "platforms": invite["platforms"]
    }


@router.get("/validate-invite/{token}")
async def validate_invite_token(
    token: str,
    db = Depends(get_db)
):
    """Validate an invitation token and return invite details"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    invite = await db.team_invites.find_one(
        {"token_hash": token_hash},
        {"_id": 0, "token": 0, "token_hash": 0}
    )
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invitation")
    
    if invite["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Invitation has been {invite['status']}")
    
    # Check if expired
    if datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        return {"valid": False, "reason": "expired"}
    
    return {
        "valid": True,
        "email": invite["email"],
        "name": invite["name"],
        "organization": invite["org_name"],
        "role": invite["role"],
        "platforms": invite["platforms"],
        "invited_by": invite.get("invited_by_name", "Admin")
    }


# ==================== TEAM MEMBERS MANAGEMENT ====================

@router.get("/members")
async def list_team_members(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    platform: Optional[str] = None,
    role: Optional[str] = None
):
    """List all team members in the organization"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get all memberships
    query = {"org_id": org["id"], "status": "active"}
    if role:
        query["role"] = role
    if platform:
        query["platforms"] = platform
    
    memberships = await db.unified_memberships.find(query, {"_id": 0}).to_list(500)
    
    # Enrich with user details
    members = []
    for mem in memberships:
        user = await db.users.find_one(
            {"id": mem["user_id"]},
            {"_id": 0, "password_hash": 0, "hashed_password": 0}
        )
        if user:
            members.append({
                **mem,
                "user": {
                    "id": user["id"],
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "department": user.get("department"),
                    "last_login": user.get("last_login")
                }
            })
    
    return {
        "total": len(members),
        "organization": org.get("name"),
        "members": members
    }


@router.put("/members/{member_user_id}")
async def update_team_member(
    member_user_id: str,
    updates: TeamMemberUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update a team member's role or access"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check permission - only admins can update members
    membership = await db.unified_memberships.find_one(
        {"user_id": user_id, "org_id": org["id"], "status": "active"},
        {"_id": 0}
    )
    
    if not membership or membership.get("role") not in ["admin"]:
        if org.get("admin_user_id") != user_id:
            raise HTTPException(status_code=403, detail="Only admins can update team members")
    
    # Build update
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if updates.role:
        update_data["role"] = updates.role
    if updates.platforms:
        update_data["platforms"] = updates.platforms
    if updates.status:
        update_data["status"] = updates.status
    
    result = await db.unified_memberships.update_one(
        {"user_id": member_user_id, "org_id": org["id"]},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    # Also update user record if department changed
    if updates.department:
        await db.users.update_one(
            {"id": member_user_id},
            {"$set": {"department": updates.department}}
        )
    
    return {"status": "updated", "user_id": member_user_id}


@router.delete("/members/{member_user_id}")
async def remove_team_member(
    member_user_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Remove a team member from the organization"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Can't remove yourself
    if member_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the organization")
    
    # Check permission
    membership = await db.unified_memberships.find_one(
        {"user_id": user_id, "org_id": org["id"], "status": "active"},
        {"_id": 0}
    )
    
    if not membership or membership.get("role") not in ["admin"]:
        if org.get("admin_user_id") != user_id:
            raise HTTPException(status_code=403, detail="Only admins can remove team members")
    
    # Soft delete membership
    result = await db.unified_memberships.update_one(
        {"user_id": member_user_id, "org_id": org["id"]},
        {"$set": {"status": "removed", "removed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    return {"status": "removed", "user_id": member_user_id}


# ==================== ORGANIZATION SETTINGS ====================

@router.get("/organization")
async def get_organization_details(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get organization details and settings"""
    user_id = current_user["user_id"]
    
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get member count
    member_count = await db.unified_memberships.count_documents({
        "org_id": org["id"],
        "status": "active"
    })
    
    # Get pending invites count
    pending_invites = await db.team_invites.count_documents({
        "org_id": org["id"],
        "status": "pending"
    })
    
    return {
        "organization": org,
        "stats": {
            "member_count": member_count,
            "pending_invites": pending_invites,
            "max_members": org.get("quotas", {}).get("max_users", 100)
        }
    }
