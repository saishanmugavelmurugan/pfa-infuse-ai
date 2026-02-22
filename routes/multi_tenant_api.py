"""
Multi-Tenant API - Unified Organization Management
Exposes the consolidated multi-tenant service via REST API
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List, Dict
from services.multi_tenant_service import multi_tenant_service

router = APIRouter(prefix="/api/organizations", tags=["Multi-Tenant Organizations"])

# ==================== MODELS ====================

class OrganizationCreate(BaseModel):
    name: str
    tier: str = "free"
    platforms: List[str] = ["healthtrack", "securesphere"]
    admin_user_id: Optional[str] = None
    metadata: Optional[Dict] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    tier: Optional[str] = None
    settings: Optional[Dict] = None

class MembershipCreate(BaseModel):
    user_id: str
    role: str = "member"
    platforms: List[str] = ["healthtrack", "securesphere"]

# ==================== AUTH ====================

async def verify_internal_admin(x_internal_key: str = Header(None)):
    if x_internal_key != "infuse_internal_2025_secret":
        raise HTTPException(status_code=403, detail="Internal admin access required")
    return True

async def verify_org_admin(x_org_id: str = Header(None), x_admin_token: str = Header(None)):
    if not x_org_id or not x_admin_token:
        raise HTTPException(status_code=401, detail="Organization credentials required")
    return {"org_id": x_org_id}

# ==================== ORGANIZATION ENDPOINTS ====================

@router.post("")
async def create_organization(
    org: OrganizationCreate,
    auth: bool = Depends(verify_internal_admin)
):
    """Create a new organization"""
    try:
        result = await multi_tenant_service.create_organization(
            name=org.name,
            tier=org.tier,
            platforms=org.platforms,
            admin_user_id=org.admin_user_id,
            metadata=org.metadata
        )
        return {"success": True, "organization": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("")
async def list_organizations(
    platform: Optional[str] = None,
    tier: Optional[str] = None,
    status: str = "active",
    limit: int = 100,
    auth: bool = Depends(verify_internal_admin)
):
    """List all organizations"""
    orgs = await multi_tenant_service.list_organizations(
        platform=platform,
        tier=tier,
        status=status,
        limit=limit
    )
    return {"organizations": orgs, "total": len(orgs)}

@router.get("/{org_id}")
async def get_organization(org_id: str, auth: dict = Depends(verify_org_admin)):
    """Get organization details"""
    org = await multi_tenant_service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"organization": org}

@router.put("/{org_id}")
async def update_organization(
    org_id: str,
    updates: OrganizationUpdate,
    auth: dict = Depends(verify_org_admin)
):
    """Update organization"""
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    org = await multi_tenant_service.update_organization(org_id, update_dict)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"success": True, "organization": org}

@router.delete("/{org_id}")
async def delete_organization(org_id: str, auth: bool = Depends(verify_internal_admin)):
    """Delete organization (soft delete)"""
    success = await multi_tenant_service.delete_organization(org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"success": True, "message": "Organization deleted"}

# ==================== MEMBERSHIP ENDPOINTS ====================

@router.post("/{org_id}/members")
async def add_member(
    org_id: str,
    member: MembershipCreate,
    auth: dict = Depends(verify_org_admin)
):
    """Add user to organization"""
    try:
        result = await multi_tenant_service.add_user_to_organization(
            org_id=org_id,
            user_id=member.user_id,
            role=member.role,
            platforms=member.platforms
        )
        return {"success": True, "membership": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{org_id}/members")
async def list_members(org_id: str, auth: dict = Depends(verify_org_admin)):
    """List organization members"""
    members = await multi_tenant_service.get_organization_members(org_id)
    return {"members": members, "total": len(members)}

@router.delete("/{org_id}/members/{user_id}")
async def remove_member(org_id: str, user_id: str, auth: dict = Depends(verify_org_admin)):
    """Remove user from organization"""
    success = await multi_tenant_service.remove_user_from_organization(org_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"success": True, "message": "Member removed"}

@router.put("/{org_id}/members/{user_id}/role")
async def update_member_role(
    org_id: str,
    user_id: str,
    role: str,
    auth: dict = Depends(verify_org_admin)
):
    """Update member's role"""
    success = await multi_tenant_service.update_member_role(org_id, user_id, role)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"success": True, "message": f"Role updated to {role}"}

# ==================== QUOTA & BILLING ====================

@router.get("/{org_id}/quota/{resource}")
async def check_quota(org_id: str, resource: str, auth: dict = Depends(verify_org_admin)):
    """Check organization quota for a resource"""
    result = await multi_tenant_service.check_quota(org_id, resource)
    return result

@router.post("/{org_id}/upgrade")
async def upgrade_tier(
    org_id: str,
    new_tier: str,
    auth: bool = Depends(verify_internal_admin)
):
    """Upgrade organization tier"""
    try:
        org = await multi_tenant_service.upgrade_organization_tier(org_id, new_tier)
        return {"success": True, "organization": org}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== DEVICES ====================

@router.get("/{org_id}/devices")
async def list_organization_devices(org_id: str, auth: dict = Depends(verify_org_admin)):
    """List organization devices"""
    devices = await multi_tenant_service.get_organization_devices(org_id)
    return {"devices": devices, "total": len(devices)}

# ==================== USER ORGANIZATIONS ====================

@router.get("/user/{user_id}/memberships")
async def get_user_organizations(user_id: str, auth: bool = Depends(verify_internal_admin)):
    """Get all organizations a user belongs to"""
    orgs = await multi_tenant_service.get_user_organizations(user_id)
    return {"memberships": orgs, "total": len(orgs)}

# ==================== AUDIT ====================

@router.get("/{org_id}/audit")
async def get_organization_audit(
    org_id: str,
    limit: int = 100,
    auth: dict = Depends(verify_org_admin)
):
    """Get organization audit log"""
    logs = await multi_tenant_service.get_audit_log(org_id, limit)
    return {"logs": logs, "total": len(logs)}

# ==================== MIGRATION ====================

@router.post("/admin/migrate-legacy")
async def migrate_legacy_organizations(auth: bool = Depends(verify_internal_admin)):
    """Migrate all legacy organizations to unified collection"""
    result = await multi_tenant_service.migrate_all_legacy_organizations()
    return {"success": True, "migrated": result}
