"""
Feature Flags API - Exposes feature configuration to frontend with admin management
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from utils.feature_flags import feature_flags, FeatureFlags

router = APIRouter(prefix="/api/features", tags=["Feature Flags"])

# Internal admin key for protected endpoints
INTERNAL_ADMIN_KEY = "infuse_internal_2025_secret"


class FeatureToggleRequest(BaseModel):
    enabled: bool


class FeatureConfigUpdate(BaseModel):
    enabled: bool
    tier: Optional[str] = None
    requires_config: Optional[List[str]] = None


def verify_admin_key(x_internal_key: str = Header(None)):
    """Verify internal admin key for protected endpoints"""
    if x_internal_key != INTERNAL_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True


@router.get("/")
async def get_all_features() -> Dict:
    """Get all feature flags"""
    return feature_flags.get_all()


@router.get("/admin/summary")
async def get_features_summary(x_internal_key: str = Header(None)) -> Dict:
    """Get summary of all features for admin dashboard"""
    verify_admin_key(x_internal_key)
    
    all_features = feature_flags.get_all()
    summary = {
        "products": [],
        "total_features": 0,
        "enabled_features": 0,
        "disabled_features": 0,
        "by_tier": {"free": 0, "basic": 0, "pro": 0, "enterprise": 0}
    }
    
    for product_name, product_config in all_features.items():
        product_summary = {
            "name": product_name,
            "enabled": product_config.get("enabled", False),
            "features": [],
            "feature_count": 0,
            "enabled_count": 0
        }
        
        features = product_config.get("features", {})
        for feature_name, feature_config in features.items():
            is_enabled = feature_config.get("enabled", False)
            tier = feature_config.get("tier", "free")
            
            product_summary["features"].append({
                "name": feature_name,
                "enabled": is_enabled,
                "tier": tier,
                "requires_config": feature_config.get("requires_config", [])
            })
            
            product_summary["feature_count"] += 1
            summary["total_features"] += 1
            
            if is_enabled:
                product_summary["enabled_count"] += 1
                summary["enabled_features"] += 1
            else:
                summary["disabled_features"] += 1
            
            summary["by_tier"][tier] = summary["by_tier"].get(tier, 0) + 1
        
        summary["products"].append(product_summary)
    
    summary["last_updated"] = datetime.now(timezone.utc).isoformat()
    return summary


@router.put("/admin/{product}/{feature}/toggle")
async def toggle_feature(
    product: str, 
    feature: str, 
    request: FeatureToggleRequest,
    x_internal_key: str = Header(None)
) -> Dict:
    """Toggle a feature on/off (admin only)"""
    verify_admin_key(x_internal_key)
    
    success = feature_flags.set_feature_enabled(product, feature, request.enabled)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Feature '{feature}' not found in product '{product}'")
    
    return {
        "success": True,
        "product": product,
        "feature": feature,
        "enabled": request.enabled,
        "message": f"Feature '{feature}' has been {'enabled' if request.enabled else 'disabled'}",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@router.put("/admin/{product}/{feature}/config")
async def update_feature_config(
    product: str,
    feature: str,
    config: FeatureConfigUpdate,
    x_internal_key: str = Header(None)
) -> Dict:
    """Update feature configuration (admin only)"""
    verify_admin_key(x_internal_key)
    
    success = feature_flags.update_feature_config(product, feature, config.model_dump(exclude_none=True))
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Feature '{feature}' not found in product '{product}'")
    
    return {
        "success": True,
        "product": product,
        "feature": feature,
        "config": config.model_dump(exclude_none=True),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@router.put("/admin/{product}/toggle")
async def toggle_product(
    product: str,
    request: FeatureToggleRequest,
    x_internal_key: str = Header(None)
) -> Dict:
    """Toggle an entire product on/off (admin only)"""
    verify_admin_key(x_internal_key)
    
    success = feature_flags.set_product_enabled(product, request.enabled)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Product '{product}' not found")
    
    return {
        "success": True,
        "product": product,
        "enabled": request.enabled,
        "message": f"Product '{product}' has been {'enabled' if request.enabled else 'disabled'}",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/admin/reload")
async def reload_features(x_internal_key: str = Header(None)) -> Dict:
    """Reload features from configuration source (admin only)"""
    verify_admin_key(x_internal_key)
    
    feature_flags.reload()
    
    return {
        "success": True,
        "message": "Feature flags reloaded from configuration",
        "reloaded_at": datetime.now(timezone.utc).isoformat()
    }


# ==================== TENANT-LEVEL FEATURE FLAGS ====================

class TenantFeatureOverride(BaseModel):
    feature_name: str
    enabled: bool
    custom_tier: Optional[str] = None
    custom_config: Optional[Dict] = None


class TenantFeatureConfig(BaseModel):
    tenant_id: str
    product: str
    overrides: List[TenantFeatureOverride]
    enabled_features: Optional[List[str]] = None
    disabled_features: Optional[List[str]] = None


@router.post("/tenant/configure")
async def configure_tenant_features(
    tenant_id: str,
    product: str,
    overrides: List[TenantFeatureOverride],
    x_internal_key: str = Header(None)
) -> Dict:
    """Configure feature overrides for a specific tenant/CSP customer (admin only)"""
    verify_admin_key(x_internal_key)
    
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    tenant_config = {
        "tenant_id": tenant_id,
        "product": product,
        "overrides": [o.model_dump() for o in overrides],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert tenant configuration
    await db.tenant_feature_flags.update_one(
        {"tenant_id": tenant_id, "product": product},
        {"$set": tenant_config},
        upsert=True
    )
    
    return {
        "success": True,
        "tenant_id": tenant_id,
        "product": product,
        "overrides_count": len(overrides),
        "message": f"Feature overrides configured for tenant '{tenant_id}'",
        "updated_at": tenant_config["updated_at"]
    }


@router.get("/tenant/{tenant_id}/{product}")
async def get_tenant_features(tenant_id: str, product: str) -> Dict:
    """Get features for a specific tenant with their overrides applied"""
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    # Get base product features
    base_features = feature_flags.get_product_features(product)
    
    # Get tenant-specific overrides
    tenant_config = await db.tenant_feature_flags.find_one(
        {"tenant_id": tenant_id, "product": product},
        {"_id": 0}
    )
    
    # Apply overrides
    tenant_features = {}
    override_map = {}
    
    if tenant_config and "overrides" in tenant_config:
        for override in tenant_config["overrides"]:
            override_map[override["feature_name"]] = override
    
    for feature_name, feature_config in base_features.items():
        tenant_feature = feature_config.copy()
        
        if feature_name in override_map:
            override = override_map[feature_name]
            tenant_feature["enabled"] = override["enabled"]
            if override.get("custom_tier"):
                tenant_feature["tier"] = override["custom_tier"]
            if override.get("custom_config"):
                tenant_feature.update(override["custom_config"])
            tenant_feature["overridden"] = True
        else:
            tenant_feature["overridden"] = False
        
        tenant_features[feature_name] = tenant_feature
    
    return {
        "tenant_id": tenant_id,
        "product": product,
        "features": tenant_features,
        "has_overrides": bool(override_map),
        "override_count": len(override_map)
    }


@router.get("/tenant/list")
async def list_tenant_configurations(
    x_internal_key: str = Header(None),
    limit: int = 100
) -> Dict:
    """List all tenant feature configurations (admin only)"""
    verify_admin_key(x_internal_key)
    
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    configs = await db.tenant_feature_flags.find({}, {"_id": 0}).to_list(limit)
    
    # Group by tenant
    tenants = {}
    for config in configs:
        tenant_id = config["tenant_id"]
        if tenant_id not in tenants:
            tenants[tenant_id] = {"products": [], "total_overrides": 0}
        tenants[tenant_id]["products"].append(config["product"])
        tenants[tenant_id]["total_overrides"] += len(config.get("overrides", []))
    
    return {
        "tenants": tenants,
        "total_tenants": len(tenants),
        "total_configurations": len(configs)
    }


@router.get("/tenant/{tenant_id}")
async def get_all_tenant_features(tenant_id: str) -> Dict:
    """Get all feature configurations for a tenant across all products"""
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    # Get all tenant configurations
    tenant_configs = await db.tenant_feature_flags.find(
        {"tenant_id": tenant_id},
        {"_id": 0}
    ).to_list(100)
    
    products = {}
    for config in tenant_configs:
        products[config["product"]] = {
            "overrides": config.get("overrides", []),
            "updated_at": config.get("updated_at")
        }
    
    return {
        "tenant_id": tenant_id,
        "products": products,
        "total_products": len(products)
    }


@router.delete("/tenant/{tenant_id}/{product}")
async def delete_tenant_overrides(
    tenant_id: str,
    product: str,
    x_internal_key: str = Header(None)
) -> Dict:
    """Delete all feature overrides for a tenant's product (admin only)"""
    verify_admin_key(x_internal_key)
    
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    result = await db.tenant_feature_flags.delete_one(
        {"tenant_id": tenant_id, "product": product}
    )
    
    return {
        "success": result.deleted_count > 0,
        "tenant_id": tenant_id,
        "product": product,
        "message": f"Feature overrides {'deleted' if result.deleted_count > 0 else 'not found'} for tenant '{tenant_id}'",
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/{product}")
async def get_product_features(product: str) -> Dict:
    """Get features for a specific product"""
    features = feature_flags.get_product_features(product)
    return {
        "product": product,
        "features": features
    }


@router.get("/{product}/{feature}")
async def get_feature_status(product: str, feature: str) -> Dict:
    """Check if a specific feature is enabled"""
    is_enabled = feature_flags.is_enabled(product, feature)
    config = feature_flags.get_feature(product, feature)
    
    return {
        "product": product,
        "feature": feature,
        "enabled": is_enabled,
        "config": config
    }


@router.get("/{product}/enabled/{tier}")
async def get_enabled_features_by_tier(product: str, tier: str = "free") -> Dict:
    """Get list of enabled features for a product and tier"""
    enabled = feature_flags.get_enabled_features(product, tier)
    
    return {
        "product": product,
        "tier": tier,
        "enabled_features": enabled,
        "count": len(enabled)
    }
