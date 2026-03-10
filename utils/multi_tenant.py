"""
Multi-Tenant Utilities (Unified)
This module now uses the consolidated MultiTenantService
All legacy organization lookups are redirected to the unified service
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, List

# Import directly from the file to avoid circular imports through services/__init__.py
import sys
import importlib.util
spec = importlib.util.spec_from_file_location("multi_tenant_service", "services/multi_tenant_service.py")
multi_tenant_module = importlib.util.module_from_spec(spec)
sys.modules["multi_tenant_service"] = multi_tenant_module
spec.loader.exec_module(multi_tenant_module)
multi_tenant_service = multi_tenant_module.multi_tenant_service

# ==================== UNIFIED WRAPPERS ====================

async def get_user_organization(user_id: str, db, auto_create: bool = True) -> Optional[dict]:
    """
    Get organization for a user (unified lookup)
    If auto_create is True, will create/assign a default organization if none exists
    """
    orgs = await multi_tenant_service.get_user_organizations(user_id)
    if orgs:
        return orgs[0].get("organization")
    
    # If no organization found and auto_create is enabled, try to find/create one
    if auto_create:
        # First, check if user has organization_id in their user record
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user and user.get("organization_id"):
            org = await multi_tenant_service.get_organization(user["organization_id"])
            if org:
                # Add user to organization membership
                await multi_tenant_service.add_user_to_organization(
                    org_id=org["id"],
                    user_id=user_id,
                    role=user.get("role", "member")
                )
                return org
        
        # Check if there's a default organization for the platform
        default_orgs = await db.unified_organizations.find(
            {"name": {"$regex": "Default.*Organization", "$options": "i"}, "status": "active"},
            {"_id": 0}
        ).to_list(1)
        
        if default_orgs:
            default_org = default_orgs[0]
            # Add user to default organization
            await multi_tenant_service.add_user_to_organization(
                org_id=default_org["id"],
                user_id=user_id,
                role="member"
            )
            return default_org
        
        # Create a new default organization
        default_org = await multi_tenant_service.create_organization(
            name="Default HealthTrack Organization",
            tier="professional",
            platforms=["healthtrack", "securesphere"],
            admin_user_id=user_id
        )
        
        # Add user as admin
        await multi_tenant_service.add_user_to_organization(
            org_id=default_org["id"],
            user_id=user_id,
            role="admin"
        )
        
        return default_org
    
    return None

async def verify_organization_access(user_id: str, org_id: str, db) -> dict:
    """Verify user has access to organization (unified)"""
    org = await multi_tenant_service.get_organization(org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check membership via unified service
    members = await multi_tenant_service.get_organization_members(org_id)
    user_ids = [m.get("user_id") for m in members]
    
    if user_id not in user_ids and org.get("admin_user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this organization"
        )
    
    return org

async def verify_organization_admin(user_id: str, org_id: str, db) -> dict:
    """Verify user is admin of organization (unified)"""
    org = await multi_tenant_service.get_organization(org_id)
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check admin status
    if org.get("admin_user_id") != user_id:
        # Also check for admin role in membership
        members = await multi_tenant_service.get_organization_members(org_id)
        admin_member = next((m for m in members if m.get("user_id") == user_id and m.get("role") == "admin"), None)
        if not admin_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization admin can perform this action"
            )
    
    return org

def apply_tenant_filter(base_query: dict, organization_id: str) -> dict:
    """Apply organization filter to database query for multi-tenancy"""
    return {**base_query, "organization_id": organization_id}

async def check_subscription_limits(org: dict, resource_type: str) -> bool:
    """Check if organization has reached subscription limits (unified)"""
    org_id = org.get("id")
    
    if resource_type == "users":
        quota = await multi_tenant_service.check_quota(org_id, "users")
    elif resource_type == "devices":
        quota = await multi_tenant_service.check_quota(org_id, "devices")
    else:
        return True
    
    if not quota.get("allowed", False):
        tier = org.get("tier", "free")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{resource_type.title()} limit reached for {tier} plan. Upgrade to add more."
        )
    
    return True

async def increment_api_calls(org_id: str, db):
    """Increment API call counter for organization (unified)"""
    await db.unified_organizations.update_one(
        {"id": org_id},
        {"$inc": {"usage.api_calls_today": 1}}
    )

# ==================== HELPER FUNCTIONS ====================

async def get_or_create_organization(
    name: str,
    admin_user_id: str,
    tier: str = "free",
    platforms: List[str] = None
) -> Dict:
    """Get existing organization or create new one"""
    # Check if org exists
    org = await multi_tenant_service.get_organization_by_name(name)
    if org:
        return org
    
    # Create new organization
    return await multi_tenant_service.create_organization(
        name=name,
        tier=tier,
        platforms=platforms or ["healthtrack", "securesphere"],
        admin_user_id=admin_user_id
    )

async def add_user_to_org(org_id: str, user_id: str, role: str = "member") -> Dict:
    """Add user to organization with role"""
    return await multi_tenant_service.add_user_to_organization(
        org_id=org_id,
        user_id=user_id,
        role=role
    )

async def migrate_legacy_organizations():
    """Migrate all legacy organizations to unified collection"""
    return await multi_tenant_service.migrate_all_legacy_organizations()

# ==================== EXPORTS ====================
__all__ = [
    'get_user_organization',
    'verify_organization_access',
    'verify_organization_admin',
    'apply_tenant_filter',
    'check_subscription_limits',
    'increment_api_calls',
    'get_or_create_organization',
    'add_user_to_org',
    'migrate_legacy_organizations'
]
