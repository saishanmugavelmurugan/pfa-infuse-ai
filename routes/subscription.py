from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, timezone, timedelta
import uuid
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

# Subscription Tier Pricing (INR per user per month)
SUBSCRIPTION_TIERS = {
    "basic": {
        "name": "Basic",
        "price_per_user": 50.0,
        "features": [
            "Up to 10 users",
            "50GB storage",
            "50K API calls/month",
            "Email support",
            "Basic analytics"
        ],
        "limits": {
            "max_users": 10,
            "storage_gb": 50,
            "api_calls_monthly": 50000
        }
    },
    "pro": {
        "name": "Pro",
        "price_per_user": 100.0,
        "features": [
            "Up to 50 users",
            "200GB storage",
            "200K API calls/month",
            "Priority email support",
            "Advanced analytics",
            "Custom integrations"
        ],
        "limits": {
            "max_users": 50,
            "storage_gb": 200,
            "api_calls_monthly": 200000
        }
    },
    "enterprise": {
        "name": "Enterprise",
        "price_per_user": 250.0,
        "features": [
            "Unlimited users",
            "1TB storage",
            "Unlimited API calls",
            "24/7 phone & email support",
            "Advanced analytics & reports",
            "Custom integrations",
            "Dedicated account manager",
            "SLA guarantee"
        ],
        "limits": {
            "max_users": -1,  # Unlimited
            "storage_gb": 1000,
            "api_calls_monthly": -1  # Unlimited
        }
    }
}

# Request/Response Models
class SubscriptionChangeRequest(BaseModel):
    tier: str = Field(..., pattern="^(basic|pro|enterprise)$")
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|annual)$")

class SubscriptionResponse(BaseModel):
    organization_id: str
    subscription_tier: str
    subscription_status: str
    price_per_user: float
    total_users: int
    monthly_cost: float
    annual_cost: float
    next_billing_date: Optional[str]
    features: list
    limits: dict

# Routes
@router.get("/tiers")
async def get_subscription_tiers():
    """Get all available subscription tiers with pricing"""
    return {
        "tiers": SUBSCRIPTION_TIERS,
        "currency": "INR",
        "billing_cycles": ["monthly", "annual"],
        "annual_discount": 0.20  # 20% discount on annual billing
    }

@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get current subscription details for user's organization"""
    user_id = current_user["user_id"]
    
    # Find user's organization
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
    
    tier = org.get("subscription_tier", "basic")
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["basic"])
    
    total_users = len(org.get("team_members", []))
    price_per_user = tier_info["price_per_user"]
    monthly_cost = price_per_user * total_users
    annual_cost = monthly_cost * 12 * 0.8  # 20% discount
    
    # Calculate next billing date (assume monthly for now)
    subscription_start = org.get("subscription_start_date")
    if isinstance(subscription_start, str):
        subscription_start = datetime.fromisoformat(subscription_start)
    
    next_billing = subscription_start + timedelta(days=30)
    
    return SubscriptionResponse(
        organization_id=org["id"],
        subscription_tier=tier,
        subscription_status=org.get("subscription_status", "active"),
        price_per_user=price_per_user,
        total_users=total_users,
        monthly_cost=monthly_cost,
        annual_cost=annual_cost,
        next_billing_date=next_billing.isoformat(),
        features=tier_info["features"],
        limits=tier_info["limits"]
    )

@router.post("/upgrade")
async def upgrade_subscription(
    subscription_change: SubscriptionChangeRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Upgrade/change subscription tier - admin only"""
    user_id = current_user["user_id"]
    
    # Find user's organization (must be admin)
    org = await db.organizations.find_one(
        {"admin_user_id": user_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin can change subscription"
        )
    
    new_tier = subscription_change.tier
    if new_tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription tier"
        )
    
    # Get tier info
    tier_info = SUBSCRIPTION_TIERS[new_tier]
    
    # Update organization subscription
    update_data = {
        "subscription_tier": new_tier,
        "subscription_status": "active",
        "data_storage_limit_gb": tier_info["limits"]["storage_gb"],
        "api_calls_limit": tier_info["limits"]["api_calls_monthly"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.organizations.update_one(
        {"id": org["id"]},
        {"$set": update_data}
    )
    
    # Calculate pricing
    total_users = len(org.get("team_members", []))
    monthly_cost = tier_info["price_per_user"] * total_users
    
    # Create billing record for upgrade (will be handled by billing API)
    return {
        "message": f"Subscription upgraded to {tier_info['name']} plan",
        "organization_id": org["id"],
        "new_tier": new_tier,
        "monthly_cost": monthly_cost,
        "billing_cycle": subscription_change.billing_cycle,
        "effective_date": datetime.now(timezone.utc).isoformat()
    }

@router.post("/cancel")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Cancel subscription - admin only"""
    user_id = current_user["user_id"]
    
    # Find user's organization (must be admin)
    org = await db.organizations.find_one(
        {"admin_user_id": user_id},
        {"_id": 0}
    )
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admin can cancel subscription"
        )
    
    # Update subscription status
    await db.organizations.update_one(
        {"id": org["id"]},
        {
            "$set": {
                "subscription_status": "cancelled",
                "subscription_end_date": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "message": "Subscription cancelled successfully",
        "organization_id": org["id"],
        "effective_date": datetime.now(timezone.utc).isoformat()
    }

@router.get("/usage")
async def get_subscription_usage(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get current usage statistics for organization"""
    user_id = current_user["user_id"]
    
    # Find user's organization
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
    
    tier = org.get("subscription_tier", "basic")
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["basic"])
    limits = tier_info["limits"]
    
    storage_used = org.get("data_storage_used_gb", 0)
    storage_limit = limits["storage_gb"]
    storage_percentage = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    api_calls = org.get("api_calls_this_month", 0)
    api_limit = limits["api_calls_monthly"]
    api_percentage = (api_calls / api_limit * 100) if api_limit > 0 and api_limit != -1 else 0
    
    users_count = len(org.get("team_members", []))
    users_limit = limits["max_users"]
    users_percentage = (users_count / users_limit * 100) if users_limit > 0 and users_limit != -1 else 0
    
    return {
        "organization_id": org["id"],
        "subscription_tier": tier,
        "usage": {
            "storage": {
                "used_gb": storage_used,
                "limit_gb": storage_limit,
                "percentage": round(storage_percentage, 2)
            },
            "api_calls": {
                "used": api_calls,
                "limit": api_limit if api_limit != -1 else "unlimited",
                "percentage": round(api_percentage, 2) if api_limit != -1 else 0
            },
            "users": {
                "current": users_count,
                "limit": users_limit if users_limit != -1 else "unlimited",
                "percentage": round(users_percentage, 2) if users_limit != -1 else 0
            }
        }
    }
