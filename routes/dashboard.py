from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, List
from datetime import datetime, timezone, timedelta
from utils.auth import get_current_user
from dependencies import get_db
from utils.multi_tenant import get_user_organization

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/overview")
async def get_dashboard_overview(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get comprehensive dashboard overview for organization"""
    user_id = current_user["user_id"]
    
    # Get organization
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for this user"
        )
    
    org_id = org["id"]
    
    # Get subscription info
    from routes.subscription import SUBSCRIPTION_TIERS
    tier = org.get("subscription_tier", "basic")
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["basic"])
    
    # Calculate subscription cost
    total_users = len(org.get("team_members", []))
    monthly_cost = tier_info["price_per_user"] * total_users
    
    # Get invoice stats
    invoices = await db.invoices.find(
        {"organization_id": org_id},
        {"_id": 0}
    ).to_list(1000)
    
    pending_invoices = [inv for inv in invoices if inv["status"] == "pending"]
    paid_invoices = [inv for inv in invoices if inv["status"] == "paid"]
    
    total_due = sum(inv["total_amount"] for inv in pending_invoices)
    total_paid = sum(inv["total_amount"] for inv in paid_invoices)
    
    # Get usage stats
    storage_used = org.get("data_storage_used_gb", 0)
    storage_limit = tier_info["limits"]["storage_gb"]
    api_calls = org.get("api_calls_this_month", 0)
    api_limit = tier_info["limits"]["api_calls_monthly"]
    
    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_invoices = [inv for inv in invoices if datetime.fromisoformat(inv["invoice_date"]) > thirty_days_ago]
    
    return {
        "organization": {
            "id": org_id,
            "name": org["company_name"],
            "industry": org["industry"],
            "size": org["company_size"],
            "is_verified": org.get("is_verified", False)
        },
        "subscription": {
            "tier": tier,
            "tier_name": tier_info["name"],
            "status": org.get("subscription_status", "active"),
            "monthly_cost": monthly_cost,
            "total_users": total_users,
            "features": tier_info["features"]
        },
        "billing": {
            "total_invoices": len(invoices),
            "pending_invoices": len(pending_invoices),
            "paid_invoices": len(paid_invoices),
            "total_amount_due": total_due,
            "total_amount_paid": total_paid,
            "currency": "INR"
        },
        "usage": {
            "storage": {
                "used_gb": storage_used,
                "limit_gb": storage_limit if storage_limit != -1 else "unlimited",
                "percentage": round((storage_used / storage_limit * 100) if storage_limit > 0 else 0, 2)
            },
            "api_calls": {
                "used": api_calls,
                "limit": api_limit if api_limit != -1 else "unlimited",
                "percentage": round((api_calls / api_limit * 100) if api_limit > 0 and api_limit != -1 else 0, 2)
            },
            "users": {
                "current": total_users,
                "limit": tier_info["limits"]["max_users"] if tier_info["limits"]["max_users"] != -1 else "unlimited"
            }
        },
        "recent_activity": {
            "invoices_last_30_days": len(recent_invoices),
            "amount_billed_last_30_days": sum(inv["total_amount"] for inv in recent_invoices)
        }
    }

@router.get("/subscription")
async def get_subscription_dashboard(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get detailed subscription dashboard"""
    user_id = current_user["user_id"]
    
    # Get organization
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for this user"
        )
    
    from routes.subscription import SUBSCRIPTION_TIERS
    tier = org.get("subscription_tier", "basic")
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["basic"])
    
    total_users = len(org.get("team_members", []))
    monthly_cost = tier_info["price_per_user"] * total_users
    annual_cost = monthly_cost * 12 * 0.8  # 20% discount
    
    # Calculate next billing date
    subscription_start = org.get("subscription_start_date")
    if isinstance(subscription_start, str):
        subscription_start = datetime.fromisoformat(subscription_start)
    next_billing = subscription_start + timedelta(days=30)
    
    # Get all available tiers for comparison
    all_tiers = {}
    for tier_key, tier_data in SUBSCRIPTION_TIERS.items():
        all_tiers[tier_key] = {
            "name": tier_data["name"],
            "price_per_user": tier_data["price_per_user"],
            "monthly_cost": tier_data["price_per_user"] * total_users,
            "features": tier_data["features"],
            "is_current": tier_key == tier
        }
    
    return {
        "current_subscription": {
            "tier": tier,
            "tier_name": tier_info["name"],
            "status": org.get("subscription_status", "active"),
            "price_per_user": tier_info["price_per_user"],
            "total_users": total_users,
            "monthly_cost": monthly_cost,
            "annual_cost": annual_cost,
            "subscription_start_date": org.get("subscription_start_date"),
            "next_billing_date": next_billing.isoformat(),
            "features": tier_info["features"],
            "limits": tier_info["limits"]
        },
        "available_tiers": all_tiers,
        "usage": {
            "storage_used_gb": org.get("data_storage_used_gb", 0),
            "storage_limit_gb": tier_info["limits"]["storage_gb"],
            "api_calls_this_month": org.get("api_calls_this_month", 0),
            "api_calls_limit": tier_info["limits"]["api_calls_monthly"]
        }
    }

@router.get("/billing")
async def get_billing_dashboard(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get detailed billing dashboard"""
    user_id = current_user["user_id"]
    
    # Get organization
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for this user"
        )
    
    org_id = org["id"]
    
    # Get all invoices
    all_invoices = await db.invoices.find(
        {"organization_id": org_id},
        {"_id": 0}
    ).sort("invoice_date", -1).to_list(1000)
    
    # Calculate stats
    pending_invoices = [inv for inv in all_invoices if inv["status"] == "pending"]
    paid_invoices = [inv for inv in all_invoices if inv["status"] == "paid"]
    overdue_invoices = [
        inv for inv in pending_invoices
        if datetime.fromisoformat(inv["due_date"]) < datetime.now(timezone.utc)
    ]
    
    total_due = sum(inv["total_amount"] for inv in pending_invoices)
    total_paid = sum(inv["total_amount"] for inv in paid_invoices)
    total_overdue = sum(inv["total_amount"] for inv in overdue_invoices)
    
    # Monthly breakdown
    monthly_stats = {}
    for inv in all_invoices:
        inv_date = datetime.fromisoformat(inv["invoice_date"])
        month_key = inv_date.strftime("%Y-%m")
        
        if month_key not in monthly_stats:
            monthly_stats[month_key] = {
                "total": 0,
                "paid": 0,
                "pending": 0,
                "count": 0
            }
        
        monthly_stats[month_key]["total"] += inv["total_amount"]
        monthly_stats[month_key]["count"] += 1
        
        if inv["status"] == "paid":
            monthly_stats[month_key]["paid"] += inv["total_amount"]
        else:
            monthly_stats[month_key]["pending"] += inv["total_amount"]
    
    return {
        "organization_id": org_id,
        "organization_name": org["company_name"],
        "summary": {
            "total_invoices": len(all_invoices),
            "pending_invoices": len(pending_invoices),
            "paid_invoices": len(paid_invoices),
            "overdue_invoices": len(overdue_invoices),
            "total_amount_due": total_due,
            "total_amount_paid": total_paid,
            "total_amount_overdue": total_overdue,
            "currency": "INR"
        },
        "monthly_breakdown": dict(sorted(monthly_stats.items(), reverse=True)[:12]),
        "recent_invoices": all_invoices[:10],
        "payment_method": org.get("payment_method_id", "Not set")
    }

@router.get("/team")
async def get_team_dashboard(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get team management dashboard"""
    user_id = current_user["user_id"]
    
    # Get organization
    org = await get_user_organization(user_id, db)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found for this user"
        )
    
    # Get team member details
    team_member_ids = org.get("team_members", [])
    team_members = await db.users.find(
        {"id": {"$in": team_member_ids}},
        {"_id": 0, "password_hash": 0}
    ).to_list(100)
    
    # Add role information
    admin_id = org["admin_user_id"]
    for member in team_members:
        if member["id"] == admin_id:
            member["organization_role"] = "admin"
        else:
            member["organization_role"] = "member"
    
    from routes.subscription import SUBSCRIPTION_TIERS
    tier = org.get("subscription_tier", "basic")
    tier_info = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["basic"])
    max_users = tier_info["limits"]["max_users"]
    
    return {
        "organization_id": org["id"],
        "organization_name": org["company_name"],
        "team_stats": {
            "total_members": len(team_members),
            "max_members": max_users if max_users != -1 else "unlimited",
            "available_slots": (max_users - len(team_members)) if max_users != -1 else "unlimited",
            "admin_count": 1,
            "member_count": len(team_members) - 1
        },
        "team_members": team_members,
        "admin_user_id": admin_id
    }
