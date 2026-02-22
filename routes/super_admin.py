"""
Super Admin API
Comprehensive admin panel for platform management, reports, and support
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os

router = APIRouter(prefix="/admin", tags=["Super Admin"])

# Database connection
async def get_db():
    import dependencies
    return dependencies.get_db()

# Pydantic Models
class AdminLoginRequest(BaseModel):
    email: str
    password: str
    admin_code: Optional[str] = None

class DoctorApprovalRequest(BaseModel):
    doctor_id: str
    approved: bool
    rejection_reason: Optional[str] = None

class AnnouncementCreate(BaseModel):
    title: str
    message: str
    target_audience: str = "all"  # all, doctors, patients
    priority: str = "normal"  # low, normal, high, urgent
    expires_at: Optional[str] = None

class SupportTicketUpdate(BaseModel):
    status: str  # open, in_progress, resolved, closed
    assigned_to: Optional[str] = None
    response: Optional[str] = None
    priority: Optional[str] = None

class HealthSchemeConfig(BaseModel):
    country_code: str
    scheme_id: str
    enabled: bool
    custom_config: Optional[Dict] = None

class SubscriptionPlanUpdate(BaseModel):
    name: str
    price: float
    currency: str
    features: List[str]
    limits: Dict[str, int]
    active: bool = True

# Admin Authentication Helper
async def verify_admin(admin_id: str, db):
    """Verify admin user"""
    admin = await db.admin_users.find_one({"id": admin_id, "role": {"$in": ["super_admin", "admin"]}})
    return admin is not None

# ==========================================
# REPORTS
# ==========================================

@router.get("/reports/user-analytics")
async def get_user_analytics(days: int = 30):
    """Get user analytics - signups, active users, by region"""
    db = await get_db()
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Total users
    total_users = await db.users.count_documents({})
    
    # New signups in period
    new_signups = await db.users.count_documents({
        "created_at": {"$gte": cutoff_date.isoformat()}
    })
    
    # Users by role
    doctors = await db.users.count_documents({"role": "doctor"})
    patients = await db.users.count_documents({"role": "patient"})
    
    # Users by region (from language preferences)
    region_pipeline = [
        {"$lookup": {
            "from": "user_language_settings",
            "localField": "id",
            "foreignField": "user_id",
            "as": "lang_settings"
        }},
        {"$unwind": {"path": "$lang_settings", "preserveNullAndEmptyArrays": True}},
        {"$group": {
            "_id": {"$ifNull": ["$lang_settings.region", "unknown"]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    by_region = await db.users.aggregate(region_pipeline).to_list(50)
    
    # Active users (logged in within period)
    active_users = await db.users.count_documents({
        "last_login": {"$gte": cutoff_date.isoformat()}
    })
    
    # Daily signups trend
    daily_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff_date.isoformat()}}},
        {"$addFields": {"date": {"$substr": ["$created_at", 0, 10]}}},
        {"$group": {"_id": "$date", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    daily_signups = await db.users.aggregate(daily_pipeline).to_list(days)
    
    return {
        "period_days": days,
        "total_users": total_users,
        "new_signups": new_signups,
        "active_users": active_users,
        "by_role": {"doctors": doctors, "patients": patients},
        "by_region": by_region,
        "daily_signups": daily_signups,
        "growth_rate": round((new_signups / max(total_users - new_signups, 1)) * 100, 2)
    }

@router.get("/reports/health-scheme-usage")
async def get_health_scheme_usage():
    """Get health scheme usage statistics"""
    db = await get_db()
    
    # Eligibility checks by scheme
    eligibility_pipeline = [
        {"$group": {
            "_id": "$scheme",
            "checks": {"$sum": 1},
            "eligible_count": {"$sum": {"$cond": ["$is_eligible", 1, 0]}}
        }},
        {"$sort": {"checks": -1}}
    ]
    eligibility_stats = await db.abdm_eligibility_records.aggregate(eligibility_pipeline).to_list(20)
    
    # Claims by status
    claims_pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$amounts.estimated"}
        }}
    ]
    claims_stats = await db.abdm_claims.aggregate(claims_pipeline).to_list(10)
    
    # Scheme comparisons
    comparisons = await db.scheme_comparisons.count_documents({})
    
    # User-submitted schemes
    user_schemes = await db.user_health_schemes.count_documents({})
    pending_schemes = await db.user_health_schemes.count_documents({"status": "pending_review"})
    
    return {
        "eligibility_checks": eligibility_stats,
        "claims_statistics": claims_stats,
        "scheme_comparisons": comparisons,
        "user_submitted_schemes": {
            "total": user_schemes,
            "pending_review": pending_schemes
        }
    }

@router.get("/reports/claims-summary")
async def get_claims_summary():
    """Get comprehensive claims summary across all patients"""
    db = await get_db()
    
    # Total claims
    total_claims = await db.abdm_claims.count_documents({})
    
    # Claims by status
    status_pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "estimated_total": {"$sum": "$amounts.estimated"},
            "approved_total": {"$sum": {"$ifNull": ["$amounts.approved", 0]}},
            "settled_total": {"$sum": {"$ifNull": ["$amounts.settled", 0]}}
        }}
    ]
    by_status = await db.abdm_claims.aggregate(status_pipeline).to_list(10)
    
    # Claims by type
    type_pipeline = [
        {"$group": {
            "_id": "$claim_type",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$amounts.estimated"}
        }}
    ]
    by_type = await db.abdm_claims.aggregate(type_pipeline).to_list(10)
    
    # Monthly trend
    monthly_pipeline = [
        {"$addFields": {"month": {"$substr": ["$created_at", 0, 7]}}},
        {"$group": {
            "_id": "$month",
            "count": {"$sum": 1},
            "amount": {"$sum": "$amounts.estimated"}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": 12}
    ]
    monthly_trend = await db.abdm_claims.aggregate(monthly_pipeline).to_list(12)
    
    # Calculate totals
    total_estimated = sum(s.get("estimated_total", 0) for s in by_status)
    total_approved = sum(s.get("approved_total", 0) for s in by_status)
    total_settled = sum(s.get("settled_total", 0) for s in by_status)
    
    return {
        "total_claims": total_claims,
        "financial_summary": {
            "total_estimated": total_estimated,
            "total_approved": total_approved,
            "total_settled": total_settled,
            "approval_rate": round((total_approved / max(total_estimated, 1)) * 100, 2)
        },
        "by_status": by_status,
        "by_type": by_type,
        "monthly_trend": monthly_trend
    }

@router.get("/reports/revenue")
async def get_revenue_report(days: int = 30):
    """Get platform revenue/billing reports"""
    db = await get_db()
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Subscription revenue
    subscriptions = await db.subscriptions.find({
        "status": "active",
        "created_at": {"$gte": cutoff_date.isoformat()}
    }).to_list(1000)
    
    subscription_revenue = sum(s.get("amount", 0) for s in subscriptions)
    
    # Revenue by plan
    plan_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {
            "_id": "$plan",
            "count": {"$sum": 1},
            "revenue": {"$sum": "$amount"}
        }}
    ]
    by_plan = await db.subscriptions.aggregate(plan_pipeline).to_list(10)
    
    # Appointments revenue (if applicable)
    appointments = await db.healthtrack_appointments.find({
        "status": "completed",
        "appointment_date": {"$gte": cutoff_date.isoformat()}
    }).to_list(10000)
    
    appointment_revenue = sum(a.get("fee", 0) for a in appointments)
    
    return {
        "period_days": days,
        "subscription_revenue": subscription_revenue,
        "appointment_revenue": appointment_revenue,
        "total_revenue": subscription_revenue + appointment_revenue,
        "active_subscriptions": len(subscriptions),
        "revenue_by_plan": by_plan,
        "currency": "INR"
    }

@router.get("/reports/ai-usage")
async def get_ai_usage_metrics():
    """Get AI usage metrics"""
    db = await get_db()
    
    # AI Analytics usage
    ai_analyses = await db.healthtrack_ai_analyses.count_documents({})
    
    # Scheme comparisons (AI-powered)
    scheme_comparisons = await db.scheme_comparisons.count_documents({})
    
    # Best practices reports
    best_practices = await db.best_practices_reports.count_documents({})
    
    # Recommendations
    recommendations = await db.scheme_recommendations.count_documents({})
    
    # Government consultations
    consultations = await db.government_consultations.count_documents({})
    
    return {
        "ai_health_analyses": ai_analyses,
        "scheme_comparisons": scheme_comparisons,
        "best_practices_reports": best_practices,
        "ai_recommendations": recommendations,
        "government_consultations": consultations,
        "total_ai_operations": ai_analyses + scheme_comparisons + best_practices + recommendations + consultations
    }

# ==========================================
# SUPPORT
# ==========================================

@router.get("/support/users")
async def list_all_users(
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """View all patient/doctor accounts"""
    db = await get_db()
    
    query = {}
    if role:
        query["role"] = role
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(query, {"_id": 0, "password": 0}).skip(skip).limit(limit).to_list(limit)
    total = await db.users.count_documents(query)
    
    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/support/users/{user_id}")
async def get_user_details(user_id: str):
    """Get detailed user information for support"""
    db = await get_db()
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get related data
    if user.get("role") == "doctor":
        patients = await db.healthtrack_patients.count_documents({"doctor_id": user_id})
        appointments = await db.healthtrack_appointments.count_documents({"doctor_id": user_id})
        user["stats"] = {"patients": patients, "appointments": appointments}
    elif user.get("role") == "patient":
        appointments = await db.healthtrack_appointments.count_documents({"patient_id": user_id})
        prescriptions = await db.healthtrack_prescriptions.count_documents({"patient_id": user_id})
        user["stats"] = {"appointments": appointments, "prescriptions": prescriptions}
    
    return user

@router.post("/support/impersonate/{user_id}")
async def create_impersonation_token(user_id: str, admin_id: str):
    """Create impersonation token for debugging (admin only)"""
    db = await get_db()
    
    # Verify admin
    if not await verify_admin(admin_id, db):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create impersonation record
    impersonation = {
        "id": str(uuid4()),
        "admin_id": admin_id,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "active": True
    }
    await db.impersonation_sessions.insert_one(impersonation)
    
    # Generate token (simplified - in production use proper JWT)
    from utils.auth import create_access_token
    token = create_access_token(user_id, user.get("email", ""))
    
    return {
        "impersonation_id": impersonation["id"],
        "token": token,
        "user": {"id": user_id, "email": user.get("email"), "role": user.get("role")},
        "expires_in": 3600,
        "warning": "This token allows full access to the user's account. Use responsibly."
    }

@router.get("/support/tickets")
async def list_support_tickets(status: Optional[str] = None, priority: Optional[str] = None):
    """List support tickets"""
    db = await get_db()
    
    query = {}
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    
    tickets = await db.support_tickets.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Summary
    summary = {
        "open": await db.support_tickets.count_documents({"status": "open"}),
        "in_progress": await db.support_tickets.count_documents({"status": "in_progress"}),
        "resolved": await db.support_tickets.count_documents({"status": "resolved"}),
        "total": await db.support_tickets.count_documents({})
    }
    
    return {"tickets": tickets, "summary": summary}

@router.put("/support/tickets/{ticket_id}")
async def update_support_ticket(ticket_id: str, update: SupportTicketUpdate):
    """Update support ticket status"""
    db = await get_db()
    
    update_data = {
        "status": update.status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if update.assigned_to:
        update_data["assigned_to"] = update.assigned_to
    if update.priority:
        update_data["priority"] = update.priority
    
    if update.response:
        # Add response to history
        await db.support_tickets.update_one(
            {"id": ticket_id},
            {
                "$set": update_data,
                "$push": {
                    "responses": {
                        "message": update.response,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "by": update.assigned_to or "admin"
                    }
                }
            }
        )
    else:
        await db.support_tickets.update_one({"id": ticket_id}, {"$set": update_data})
    
    return {"success": True, "status": update.status}

@router.post("/support/announcements")
async def create_announcement(announcement: AnnouncementCreate):
    """Create a new announcement"""
    db = await get_db()
    
    record = {
        "id": str(uuid4()),
        "title": announcement.title,
        "message": announcement.message,
        "target_audience": announcement.target_audience,
        "priority": announcement.priority,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": announcement.expires_at,
        "active": True,
        "read_by": []
    }
    
    await db.announcements.insert_one(record)
    
    return {"success": True, "announcement_id": record["id"]}

@router.get("/support/announcements")
async def list_announcements(active_only: bool = True):
    """List all announcements"""
    db = await get_db()
    
    query = {}
    if active_only:
        query["active"] = True
    
    announcements = await db.announcements.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return {"announcements": announcements}

# ==========================================
# MANAGEMENT
# ==========================================

@router.get("/management/doctors/pending")
async def list_pending_doctors():
    """List doctors pending approval"""
    db = await get_db()
    
    pending = await db.users.find(
        {"role": "doctor", "status": "pending_approval"},
        {"_id": 0, "password": 0}
    ).to_list(100)
    
    return {"pending_doctors": pending, "count": len(pending)}

@router.post("/management/doctors/approve")
async def approve_doctor(request: DoctorApprovalRequest):
    """Approve or reject a doctor"""
    db = await get_db()
    
    update_data = {
        "status": "approved" if request.approved else "rejected",
        "reviewed_at": datetime.now(timezone.utc).isoformat()
    }
    
    if not request.approved and request.rejection_reason:
        update_data["rejection_reason"] = request.rejection_reason
    
    result = await db.users.update_one(
        {"id": request.doctor_id, "role": "doctor"},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    return {"success": True, "status": update_data["status"]}

@router.get("/management/health-schemes/config")
async def get_scheme_configurations():
    """Get health scheme configurations per region"""
    db = await get_db()
    
    configs = await db.scheme_configs.find({}, {"_id": 0}).to_list(100)
    
    return {"configurations": configs}

@router.put("/management/health-schemes/config")
async def update_scheme_config(config: HealthSchemeConfig):
    """Update health scheme configuration for a region"""
    db = await get_db()
    
    await db.scheme_configs.update_one(
        {"country_code": config.country_code, "scheme_id": config.scheme_id},
        {
            "$set": {
                "enabled": config.enabled,
                "custom_config": config.custom_config,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"success": True}

@router.get("/management/subscription-plans")
async def list_subscription_plans():
    """List all subscription plans"""
    db = await get_db()
    
    plans = await db.subscription_plans.find({}, {"_id": 0}).to_list(20)
    
    # Default plans if none exist
    if not plans:
        plans = [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "currency": "INR",
                "features": ["Basic patient records", "Up to 10 patients", "Email support"],
                "limits": {"patients": 10, "appointments_per_month": 50},
                "active": True
            },
            {
                "id": "professional",
                "name": "Professional",
                "price": 999,
                "currency": "INR",
                "features": ["Unlimited patients", "AI analytics", "Priority support", "ABDM integration"],
                "limits": {"patients": -1, "appointments_per_month": -1},
                "active": True
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 4999,
                "currency": "INR",
                "features": ["Everything in Professional", "Custom integrations", "Dedicated support", "White-label option"],
                "limits": {"patients": -1, "appointments_per_month": -1, "api_calls": -1},
                "active": True
            }
        ]
        # Insert default plans
        for plan in plans:
            await db.subscription_plans.update_one(
                {"id": plan["id"]},
                {"$set": plan},
                upsert=True
            )
    
    return {"plans": plans}

@router.put("/management/subscription-plans/{plan_id}")
async def update_subscription_plan(plan_id: str, plan: SubscriptionPlanUpdate):
    """Update a subscription plan"""
    db = await get_db()
    
    update_data = {
        "name": plan.name,
        "price": plan.price,
        "currency": plan.currency,
        "features": plan.features,
        "limits": plan.limits,
        "active": plan.active,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.subscription_plans.update_one(
        {"id": plan_id},
        {"$set": update_data}
    )
    
    return {"success": True}

# ==========================================
# DASHBOARD SUMMARY
# ==========================================

@router.get("/dashboard")
async def get_admin_dashboard():
    """Get comprehensive admin dashboard summary"""
    db = await get_db()
    
    # User stats
    total_users = await db.users.count_documents({})
    doctors = await db.users.count_documents({"role": "doctor"})
    patients = await db.users.count_documents({"role": "patient"})
    pending_doctors = await db.users.count_documents({"role": "doctor", "status": "pending_approval"})
    
    # Activity stats
    total_appointments = await db.healthtrack_appointments.count_documents({})
    total_prescriptions = await db.healthtrack_prescriptions.count_documents({})
    total_claims = await db.abdm_claims.count_documents({})
    
    # Support stats
    open_tickets = await db.support_tickets.count_documents({"status": "open"})
    
    # AI usage
    ai_operations = await db.scheme_comparisons.count_documents({})
    ai_operations += await db.best_practices_reports.count_documents({})
    ai_operations += await db.scheme_recommendations.count_documents({})
    
    return {
        "users": {
            "total": total_users,
            "doctors": doctors,
            "patients": patients,
            "pending_approval": pending_doctors
        },
        "activity": {
            "appointments": total_appointments,
            "prescriptions": total_prescriptions,
            "claims": total_claims
        },
        "support": {
            "open_tickets": open_tickets
        },
        "ai": {
            "total_operations": ai_operations
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
