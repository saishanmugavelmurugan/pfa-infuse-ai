"""
Unified Multi-Tenant Service
Consolidates organization management across HealthTrack Pro and SecureSphere

Features:
- Single source of truth for organization data
- Cross-platform membership management
- Unified quota and billing
- Organization hierarchy support
- Audit logging
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import uuid4

import dependencies

class MultiTenantService:
    """
    Unified multi-tenant organization service
    Replaces the fragmented organization lookup logic
    """
    
    # Supported platforms
    PLATFORMS = ["healthtrack", "securesphere", "infuse"]
    
    # Organization tiers
    TIERS = {
        "free": {"max_users": 5, "max_devices": 10, "features": ["basic"]},
        "starter": {"max_users": 25, "max_devices": 50, "features": ["basic", "reports"]},
        "professional": {"max_users": 100, "max_devices": 200, "features": ["basic", "reports", "api"]},
        "enterprise": {"max_users": 1000, "max_devices": 10000, "features": ["basic", "reports", "api", "sso", "vran"]},
        "unlimited": {"max_users": -1, "max_devices": -1, "features": ["all"]}
    }
    
    def __init__(self):
        self.db = None
    
    async def _get_db(self):
        """Get database connection"""
        if self.db is None:
            self.db = dependencies.get_db()
        return self.db
    
    # ==================== ORGANIZATION CRUD ====================
    
    async def create_organization(
        self,
        name: str,
        tier: str = "free",
        platforms: List[str] = None,
        admin_user_id: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Create a new organization (unified across platforms)
        """
        db = await self._get_db()
        
        org_id = f"org_{uuid4().hex[:12]}"
        
        organization = {
            "id": org_id,
            "name": name,
            "tier": tier,
            "platforms": platforms or ["healthtrack", "securesphere"],
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "admin_user_id": admin_user_id,
            "metadata": metadata or {},
            "settings": {
                "ip_whitelist_enabled": False,
                "sso_enabled": False,
                "mfa_required": False,
                "data_retention_days": 365
            },
            "quotas": self.TIERS.get(tier, self.TIERS["free"]),
            "usage": {
                "users_count": 0,
                "devices_count": 0,
                "api_calls_today": 0
            }
        }
        
        # Insert into unified organizations collection
        await db.unified_organizations.insert_one(organization)
        organization.pop("_id", None)
        
        # Log creation
        await self._audit_log(org_id, "organization_created", {"name": name, "tier": tier})
        
        return organization
    
    async def get_organization(self, org_id: str) -> Optional[Dict]:
        """
        Get organization by ID (searches unified collection first, then legacy)
        """
        db = await self._get_db()
        
        # First check unified collection
        org = await db.unified_organizations.find_one({"id": org_id}, {"_id": 0})
        
        if org:
            return org
        
        # Check legacy collections for backwards compatibility
        org = await db.organizations.find_one({"id": org_id}, {"_id": 0})
        if org:
            # Migrate to unified collection
            await self._migrate_legacy_org(org)
            return org
        
        org = await db.healthtrack_organizations.find_one({"id": org_id}, {"_id": 0})
        if org:
            await self._migrate_legacy_org(org, platform="healthtrack")
            return org
        
        return None
    
    async def get_organization_by_name(self, name: str) -> Optional[Dict]:
        """Get organization by name"""
        db = await self._get_db()
        
        org = await db.unified_organizations.find_one({"name": name}, {"_id": 0})
        return org
    
    async def update_organization(self, org_id: str, updates: Dict) -> Optional[Dict]:
        """Update organization details"""
        db = await self._get_db()
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.unified_organizations.update_one(
            {"id": org_id},
            {"$set": updates}
        )
        
        if result.modified_count > 0:
            await self._audit_log(org_id, "organization_updated", updates)
            return await self.get_organization(org_id)
        
        return None
    
    async def delete_organization(self, org_id: str) -> bool:
        """Soft delete organization"""
        db = await self._get_db()
        
        result = await db.unified_organizations.update_one(
            {"id": org_id},
            {"$set": {"status": "deleted", "deleted_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count > 0:
            await self._audit_log(org_id, "organization_deleted", {})
            return True
        
        return False
    
    async def list_organizations(
        self,
        platform: str = None,
        tier: str = None,
        status: str = "active",
        limit: int = 100
    ) -> List[Dict]:
        """List organizations with filters"""
        db = await self._get_db()
        
        query = {"status": status}
        if platform:
            query["platforms"] = platform
        if tier:
            query["tier"] = tier
        
        orgs = await db.unified_organizations.find(query, {"_id": 0}).limit(limit).to_list(limit)
        return orgs
    
    # ==================== MEMBERSHIP MANAGEMENT ====================
    
    async def add_user_to_organization(
        self,
        org_id: str,
        user_id: str,
        role: str = "member",
        platforms: List[str] = None
    ) -> Dict:
        """Add user to organization with specific role and platform access"""
        db = await self._get_db()
        
        membership = {
            "id": f"mem_{uuid4().hex[:12]}",
            "org_id": org_id,
            "user_id": user_id,
            "role": role,  # admin, manager, member, viewer
            "platforms": platforms or ["healthtrack", "securesphere"],
            "status": "active",
            "joined_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check quota
        org = await self.get_organization(org_id)
        if org:
            max_users = org.get("quotas", {}).get("max_users", 5)
            if max_users != -1 and org.get("usage", {}).get("users_count", 0) >= max_users:
                raise Exception(f"Organization has reached maximum users limit ({max_users})")
        
        await db.unified_memberships.insert_one(membership)
        membership.pop("_id", None)
        
        # Update user count
        await db.unified_organizations.update_one(
            {"id": org_id},
            {"$inc": {"usage.users_count": 1}}
        )
        
        await self._audit_log(org_id, "user_added", {"user_id": user_id, "role": role})
        
        return membership
    
    async def remove_user_from_organization(self, org_id: str, user_id: str) -> bool:
        """Remove user from organization"""
        db = await self._get_db()
        
        result = await db.unified_memberships.update_one(
            {"org_id": org_id, "user_id": user_id},
            {"$set": {"status": "removed", "removed_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count > 0:
            await db.unified_organizations.update_one(
                {"id": org_id},
                {"$inc": {"usage.users_count": -1}}
            )
            await self._audit_log(org_id, "user_removed", {"user_id": user_id})
            return True
        
        return False
    
    async def get_user_organizations(self, user_id: str) -> List[Dict]:
        """Get all organizations a user belongs to"""
        db = await self._get_db()
        
        memberships = await db.unified_memberships.find(
            {"user_id": user_id, "status": "active"},
            {"_id": 0}
        ).to_list(100)
        
        # Enrich with org details
        result = []
        for mem in memberships:
            org = await self.get_organization(mem["org_id"])
            if org:
                result.append({
                    **mem,
                    "organization": org
                })
        
        return result
    
    async def get_organization_members(self, org_id: str) -> List[Dict]:
        """Get all members of an organization"""
        db = await self._get_db()
        
        memberships = await db.unified_memberships.find(
            {"org_id": org_id, "status": "active"},
            {"_id": 0}
        ).to_list(1000)
        
        return memberships
    
    async def update_member_role(self, org_id: str, user_id: str, new_role: str) -> bool:
        """Update member's role in organization"""
        db = await self._get_db()
        
        result = await db.unified_memberships.update_one(
            {"org_id": org_id, "user_id": user_id, "status": "active"},
            {"$set": {"role": new_role, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count > 0:
            await self._audit_log(org_id, "member_role_updated", {"user_id": user_id, "new_role": new_role})
            return True
        
        return False
    
    # ==================== DEVICE MANAGEMENT ====================
    
    async def register_device_to_organization(
        self,
        org_id: str,
        device_id: str,
        device_type: str,
        platform: str = "securesphere"
    ) -> Dict:
        """Register a device to organization"""
        db = await self._get_db()
        
        # Check quota
        org = await self.get_organization(org_id)
        if org:
            max_devices = org.get("quotas", {}).get("max_devices", 10)
            if max_devices != -1 and org.get("usage", {}).get("devices_count", 0) >= max_devices:
                raise Exception(f"Organization has reached maximum devices limit ({max_devices})")
        
        device_reg = {
            "id": f"dev_reg_{uuid4().hex[:12]}",
            "org_id": org_id,
            "device_id": device_id,
            "device_type": device_type,
            "platform": platform,
            "status": "active",
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.unified_device_registrations.insert_one(device_reg)
        device_reg.pop("_id", None)
        
        # Update device count
        await db.unified_organizations.update_one(
            {"id": org_id},
            {"$inc": {"usage.devices_count": 1}}
        )
        
        return device_reg
    
    async def get_organization_devices(self, org_id: str) -> List[Dict]:
        """Get all devices registered to an organization"""
        db = await self._get_db()
        
        devices = await db.unified_device_registrations.find(
            {"org_id": org_id, "status": "active"},
            {"_id": 0}
        ).to_list(10000)
        
        return devices
    
    # ==================== QUOTA & BILLING ====================
    
    async def check_quota(self, org_id: str, resource: str) -> Dict:
        """Check if organization has quota available for a resource"""
        org = await self.get_organization(org_id)
        
        if not org:
            return {"allowed": False, "reason": "Organization not found"}
        
        quotas = org.get("quotas", {})
        usage = org.get("usage", {})
        
        if resource == "users":
            max_val = quotas.get("max_users", 5)
            current = usage.get("users_count", 0)
        elif resource == "devices":
            max_val = quotas.get("max_devices", 10)
            current = usage.get("devices_count", 0)
        else:
            return {"allowed": True, "reason": "Unknown resource, allowing"}
        
        if max_val == -1:
            return {"allowed": True, "reason": "Unlimited", "current": current, "max": "unlimited"}
        
        allowed = current < max_val
        return {
            "allowed": allowed,
            "reason": "Quota available" if allowed else "Quota exceeded",
            "current": current,
            "max": max_val,
            "remaining": max(0, max_val - current)
        }
    
    async def upgrade_organization_tier(self, org_id: str, new_tier: str) -> Dict:
        """Upgrade organization to a new tier"""
        if new_tier not in self.TIERS:
            raise Exception(f"Invalid tier: {new_tier}")
        
        new_quotas = self.TIERS[new_tier]
        
        org = await self.update_organization(org_id, {
            "tier": new_tier,
            "quotas": new_quotas
        })
        
        await self._audit_log(org_id, "tier_upgraded", {"new_tier": new_tier})
        
        return org
    
    # ==================== MIGRATION HELPERS ====================
    
    async def _migrate_legacy_org(self, org: Dict, platform: str = None):
        """Migrate legacy organization to unified collection"""
        db = await self._get_db()
        
        # Check if already migrated
        existing = await db.unified_organizations.find_one({"id": org["id"]})
        if existing:
            return
        
        # Add missing fields
        org.setdefault("platforms", [platform] if platform else ["healthtrack", "securesphere"])
        org.setdefault("status", "active")
        org.setdefault("tier", "free")
        org.setdefault("quotas", self.TIERS["free"])
        org.setdefault("usage", {"users_count": 0, "devices_count": 0})
        org.setdefault("settings", {})
        org["migrated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.unified_organizations.insert_one(org)
        
        await self._audit_log(org["id"], "organization_migrated", {"from_collection": "legacy"})
    
    async def migrate_all_legacy_organizations(self) -> Dict:
        """Migrate all legacy organizations to unified collection"""
        db = await self._get_db()
        
        migrated = {"organizations": 0, "healthtrack_organizations": 0}
        
        # Migrate from organizations collection
        async for org in db.organizations.find({}, {"_id": 0}):
            await self._migrate_legacy_org(org)
            migrated["organizations"] += 1
        
        # Migrate from healthtrack_organizations collection
        async for org in db.healthtrack_organizations.find({}, {"_id": 0}):
            await self._migrate_legacy_org(org, platform="healthtrack")
            migrated["healthtrack_organizations"] += 1
        
        return migrated
    
    # ==================== AUDIT LOG ====================
    
    async def _audit_log(self, org_id: str, action: str, details: Dict):
        """Log organization activity"""
        db = await self._get_db()
        
        await db.unified_org_audit.insert_one({
            "org_id": org_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def get_audit_log(self, org_id: str, limit: int = 100) -> List[Dict]:
        """Get organization audit log"""
        db = await self._get_db()
        
        logs = await db.unified_org_audit.find(
            {"org_id": org_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        return logs


# Singleton instance
multi_tenant_service = MultiTenantService()
