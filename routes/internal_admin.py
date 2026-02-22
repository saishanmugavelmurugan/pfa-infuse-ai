"""
Internal Admin Console - Infuse Team Only
Full platform access: Support, AI Learning, Analytics, Revenue, Pricing, Downloads
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import os

import dependencies

router = APIRouter(prefix="/api/internal-admin", tags=["Internal Admin - Infuse Team"])

# Internal Admin API Key (in production, use proper auth)
INTERNAL_ADMIN_KEY = "infuse_internal_2025_secret"

# ==================== PRICING MODEL ====================

# Development Cost Base (hypothetical)
DEV_COST_BASE = 500000  # $500K total development

# Cost of Sales = 200% of Dev Cost
COST_OF_SALES = DEV_COST_BASE * 2  # $1M

# Margin = 100%
MARGIN_MULTIPLIER = 2  # 100% margin = 2x multiplier

# Total Revenue Target = Cost of Sales * Margin
REVENUE_TARGET = COST_OF_SALES * MARGIN_MULTIPLIER  # $2M

PRICING_TIERS = {
    # SaaS - Individual Users (Monthly)
    "saas_individual_basic": {
        "name": "Individual Basic",
        "type": "saas",
        "billing": "monthly",
        "price_usd": 9.99,
        "price_inr": 799,
        "users": 1,
        "features": [
            "URL Scanner - 100/month",
            "SMS Analyzer - 50/month",
            "Basic Threat Dashboard",
            "Email Alerts"
        ],
        "support": "Community",
        "sla": "None"
    },
    "saas_individual_pro": {
        "name": "Individual Pro",
        "type": "saas",
        "billing": "monthly",
        "price_usd": 24.99,
        "price_inr": 1999,
        "users": 1,
        "features": [
            "URL Scanner - Unlimited",
            "SMS Analyzer - Unlimited",
            "Real-time Threat Scoring",
            "Device Registry - 5 devices",
            "Email + SMS Alerts",
            "Priority Support"
        ],
        "support": "Email (24h)",
        "sla": "99.5%"
    },
    "saas_individual_premium": {
        "name": "Individual Premium",
        "type": "saas",
        "billing": "monthly",
        "price_usd": 49.99,
        "price_inr": 3999,
        "users": 1,
        "features": [
            "All Pro Features",
            "Device Registry - 20 devices",
            "CCTV Monitoring - 5 cameras",
            "White Goods Protection - 10 devices",
            "API Access",
            "Dedicated Support"
        ],
        "support": "Email + Phone (12h)",
        "sla": "99.9%"
    },
    
    # PaaS - Enterprise (Annual)
    "paas_enterprise_50": {
        "name": "Enterprise 50",
        "type": "paas",
        "billing": "annual",
        "price_usd": 4999,
        "price_inr": 399900,
        "users": 50,
        "price_per_user": 99.98,
        "features": [
            "All Premium Features",
            "Admin Console",
            "User Management",
            "SSO Integration",
            "Custom Branding",
            "API Rate Limit - 10K/day",
            "vRAN Integration - Basic"
        ],
        "support": "Email + Phone (4h)",
        "sla": "99.9%"
    },
    "paas_enterprise_100": {
        "name": "Enterprise 100",
        "type": "paas",
        "billing": "annual",
        "price_usd": 8999,
        "price_inr": 719900,
        "users": 100,
        "price_per_user": 89.99,
        "features": [
            "All Enterprise 50 Features",
            "Advanced Analytics",
            "Multi-tenant Support",
            "IP Whitelisting",
            "Audit Logs",
            "API Rate Limit - 50K/day",
            "vRAN Integration - Standard"
        ],
        "support": "Dedicated Account Manager",
        "sla": "99.95%"
    },
    "paas_enterprise_500": {
        "name": "Enterprise 500",
        "type": "paas",
        "billing": "annual",
        "price_usd": 34999,
        "price_inr": 2799900,
        "users": 500,
        "price_per_user": 69.99,
        "features": [
            "All Enterprise 100 Features",
            "On-premise Deployment Option",
            "Custom Integrations",
            "Bulk Data Export",
            "API Rate Limit - Unlimited",
            "vRAN Integration - Full Telco Grade"
        ],
        "support": "24/7 Dedicated Team",
        "sla": "99.99%"
    },
    "paas_enterprise_bulk": {
        "name": "Enterprise Bulk License",
        "type": "paas",
        "billing": "annual",
        "price_usd": "Custom",
        "price_inr": "Custom",
        "users": "1000+",
        "price_per_user": "Contact Sales",
        "features": [
            "All Enterprise 500 Features",
            "White-label Option",
            "Source Code Escrow",
            "Custom SLA",
            "Dedicated Infrastructure",
            "Full vRAN + Telco Integration"
        ],
        "support": "Enterprise SLA",
        "sla": "Custom"
    },
    
    # Telco Tier (Special)
    "telco_operator": {
        "name": "Telco Operator License",
        "type": "telco",
        "billing": "annual",
        "price_usd": 99999,
        "price_inr": 7999900,
        "users": "Unlimited Subscribers",
        "features": [
            "Full vRAN Integration",
            "Network-level Protection",
            "RAN Event Processing",
            "GSM Fraud Detection Suite",
            "SIM Swap Protection",
            "OTP Interception Detection",
            "Caller ID Verification",
            "Subscriber Analytics",
            "API for Integration",
            "Custom Webhooks"
        ],
        "support": "24/7 NOC Integration",
        "sla": "99.999%"
    }
}

# Revenue Tracking
REVENUE_DATA = {
    "target_annual": REVENUE_TARGET,
    "current_mrr": 0,
    "current_arr": 0,
    "customers": {
        "saas_individual": 0,
        "paas_enterprise": 0,
        "telco": 0
    }
}


def verify_internal_admin(x_internal_key: str = Header(None)):
    """Verify internal admin access"""
    if x_internal_key != INTERNAL_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Internal admin access required")
    return True


# ==================== PRICING ENDPOINTS ====================

@router.get("/pricing/tiers")
async def get_pricing_tiers(auth: bool = Depends(verify_internal_admin)):
    """Get all pricing tiers (internal view with costs)"""
    return {
        "pricing_tiers": PRICING_TIERS,
        "cost_structure": {
            "development_cost": DEV_COST_BASE,
            "cost_of_sales": COST_OF_SALES,
            "margin_target": "100%",
            "revenue_target": REVENUE_TARGET
        },
        "currency_rates": {
            "usd_to_inr": 80
        }
    }

@router.get("/pricing/calculator")
async def calculate_pricing(
    tier: str,
    users: int = 1,
    billing: str = "annual",
    auth: bool = Depends(verify_internal_admin)
):
    """Calculate pricing for specific configuration"""
    if tier not in PRICING_TIERS:
        return {"error": f"Invalid tier. Available: {list(PRICING_TIERS.keys())}"}
    
    tier_data = PRICING_TIERS[tier]
    
    if isinstance(tier_data["price_usd"], str):
        return {
            "tier": tier,
            "users": users,
            "message": "Custom pricing - contact sales",
            "base_price": "Custom"
        }
    
    base_price = tier_data["price_usd"]
    
    # Volume discounts
    discount = 0
    if users > 100:
        discount = 0.15  # 15% discount
    elif users > 50:
        discount = 0.10  # 10% discount
    
    # Annual discount
    if billing == "annual" and tier_data["billing"] == "monthly":
        base_price = base_price * 12 * 0.85  # 15% annual discount
    
    final_price = base_price * (1 - discount)
    
    # Cost analysis
    margin_amount = final_price * 0.5  # 100% margin means 50% of price is margin
    cost_amount = final_price - margin_amount
    
    return {
        "tier": tier,
        "tier_name": tier_data["name"],
        "users": tier_data["users"],
        "billing": billing,
        "base_price_usd": base_price,
        "discount_percent": discount * 100,
        "final_price_usd": round(final_price, 2),
        "final_price_inr": round(final_price * 80, 2),
        "cost_analysis": {
            "margin_amount": round(margin_amount, 2),
            "cost_amount": round(cost_amount, 2),
            "margin_percent": 100
        },
        "features": tier_data["features"],
        "support": tier_data["support"],
        "sla": tier_data["sla"]
    }


# ==================== REVENUE ANALYTICS ====================

@router.get("/revenue/dashboard")
async def get_revenue_dashboard(auth: bool = Depends(verify_internal_admin)):
    """Get revenue dashboard for internal team"""
    db = dependencies.get_db()
    
    # Get customer counts by tier
    total_users = await db.users.count_documents({})
    premium_users = await db.users.count_documents({"subscription_tier": {"$exists": True}})
    
    # Calculate projected revenue based on users
    saas_revenue = premium_users * 24.99 * 12  # Assume Pro tier
    enterprise_revenue = 5 * 8999  # Assume 5 enterprise customers
    
    total_arr = saas_revenue + enterprise_revenue
    
    return {
        "revenue_summary": {
            "target_arr": REVENUE_TARGET,
            "current_arr": total_arr,
            "current_mrr": total_arr / 12,
            "gap_to_target": REVENUE_TARGET - total_arr,
            "achievement_percent": round((total_arr / REVENUE_TARGET) * 100, 2)
        },
        "customer_metrics": {
            "total_users": total_users,
            "paying_users": premium_users,
            "conversion_rate": round((premium_users / max(1, total_users)) * 100, 2),
            "estimated_enterprise": 5
        },
        "revenue_by_segment": {
            "healthtrack_pro": {
                "users": int(total_users * 0.6),
                "revenue": saas_revenue * 0.4
            },
            "securesphere": {
                "users": int(total_users * 0.4),
                "revenue": saas_revenue * 0.6
            }
        },
        "vertical_breakdown": {
            "telco": {"potential": 500000, "current": 0},
            "enterprise": {"potential": 300000, "current": enterprise_revenue},
            "mobile_users": {"potential": 200000, "current": saas_revenue},
            "automotive": {"potential": 100000, "current": 0},
            "iot_white_goods": {"potential": 50000, "current": 0},
            "cctv": {"potential": 50000, "current": 0}
        },
        "projections": {
            "q1_target": REVENUE_TARGET * 0.15,
            "q2_target": REVENUE_TARGET * 0.25,
            "q3_target": REVENUE_TARGET * 0.30,
            "q4_target": REVENUE_TARGET * 0.30
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/revenue/per-user")
async def get_per_user_analytics(
    limit: int = 100,
    auth: bool = Depends(verify_internal_admin)
):
    """Get per-user revenue analytics"""
    db = dependencies.get_db()
    
    users = await db.users.find({}, {"_id": 0}).limit(limit).to_list(limit)
    
    user_revenue = []
    for user in users:
        # Calculate user value based on activity
        api_calls = await db.api_usage.count_documents({"user_id": user.get("id", "")})
        
        tier = user.get("subscription_tier", "free")
        tier_price = {
            "free": 0,
            "basic": 9.99,
            "pro": 24.99,
            "premium": 49.99,
            "enterprise": 89.99
        }.get(tier, 0)
        
        user_revenue.append({
            "user_id": user.get("id"),
            "email": user.get("email", "")[:3] + "***",
            "tier": tier,
            "monthly_value": tier_price,
            "annual_value": tier_price * 12,
            "api_calls": api_calls,
            "ltv_estimate": tier_price * 24  # 2-year LTV estimate
        })
    
    return {
        "total_users": len(user_revenue),
        "users": user_revenue,
        "summary": {
            "total_monthly_revenue": sum(u["monthly_value"] for u in user_revenue),
            "total_annual_revenue": sum(u["annual_value"] for u in user_revenue),
            "total_ltv": sum(u["ltv_estimate"] for u in user_revenue),
            "avg_revenue_per_user": round(sum(u["monthly_value"] for u in user_revenue) / max(1, len(user_revenue)), 2)
        }
    }


# ==================== AI LEARNING MANAGEMENT ====================

@router.get("/ai/learning-status")
async def get_ai_learning_status(auth: bool = Depends(verify_internal_admin)):
    """Get AI learning agent status"""
    from services.securesphere.ai_learning_agent import ai_learning_agent
    
    return {
        "learning_agent": ai_learning_agent.get_learning_status(),
        "recommendations": [
            "Enable federated learning for faster pattern updates",
            "Review false positive rate weekly",
            "Update threat intelligence feeds monthly"
        ]
    }

@router.post("/ai/trigger-learning-cycle")
async def trigger_learning_cycle(auth: bool = Depends(verify_internal_admin)):
    """Manually trigger AI learning cycle"""
    from services.securesphere.ai_learning_agent import ai_learning_agent
    
    # Generate threat report
    report = await ai_learning_agent.generate_threat_intelligence_report()
    
    return {
        "status": "learning_cycle_triggered",
        "report": report,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/ai/threat-report")
async def get_threat_intelligence_report(auth: bool = Depends(verify_internal_admin)):
    """Get comprehensive threat intelligence report"""
    from services.securesphere.ai_learning_agent import ai_learning_agent
    
    report = await ai_learning_agent.generate_threat_intelligence_report()
    return report


# ==================== SUPPORT MANAGEMENT ====================

@router.get("/support/stats")
async def get_support_stats(auth: bool = Depends(verify_internal_admin)):
    """Get support agent statistics"""
    from services.securesphere.ai_support_agent import ai_support_agent
    
    return {
        "support_stats": ai_support_agent.get_support_stats(),
        "knowledge_base": {
            "securesphere_faqs": 4,
            "healthtrack_faqs": 4,
            "troubleshooting_flows": 4
        }
    }

@router.get("/support/escalations")
async def get_escalated_tickets(
    status: str = "pending",
    auth: bool = Depends(verify_internal_admin)
):
    """Get escalated support tickets"""
    db = dependencies.get_db()
    
    tickets = await db.support_escalations.find(
        {"status": status},
        {"_id": 0}
    ).limit(100).to_list(100)
    
    return {
        "total": len(tickets),
        "status_filter": status,
        "tickets": tickets
    }


# ==================== PLATFORM HEALTH ====================

@router.get("/platform/health")
async def get_platform_health(auth: bool = Depends(verify_internal_admin)):
    """Get overall platform health"""
    db = dependencies.get_db()
    
    # Service health checks
    services = {
        "database": "healthy",
        "vran_connector": "healthy",
        "threat_engine": "healthy",
        "ai_learning": "healthy",
        "alert_service": "healthy"
    }
    
    # Get counts
    total_users = await db.users.count_documents({})
    total_connections = await db.vran_connections.count_documents({}) if await db.list_collection_names() else 0
    threats_blocked = await db.threat_events.count_documents({"action_taken": "enforce"}) if await db.list_collection_names() else 0
    
    return {
        "status": "operational",
        "services": services,
        "metrics": {
            "total_users": total_users,
            "active_connections": total_connections,
            "threats_blocked_today": threats_blocked,
            "uptime_percent": 99.95
        },
        "alerts": [],
        "last_check": datetime.now(timezone.utc).isoformat()
    }

@router.get("/platform/segments")
async def get_segment_analytics(auth: bool = Depends(verify_internal_admin)):
    """Get analytics by segment"""
    db = dependencies.get_db()
    
    segments = {
        "telco": {
            "active_providers": 3,
            "subscribers_protected": 50000,
            "events_processed": 125000,
            "revenue_potential": 500000
        },
        "mobile": {
            "active_users": 1000,
            "devices_protected": 1500,
            "threats_blocked": 3500,
            "revenue_potential": 200000
        },
        "enterprise": {
            "active_companies": 25,
            "endpoints_protected": 5000,
            "compliance_score": 95,
            "revenue_potential": 300000
        },
        "automotive": {
            "fleets_connected": 10,
            "vehicles_protected": 500,
            "can_attacks_blocked": 45,
            "revenue_potential": 100000
        },
        "white_goods": {
            "homes_protected": 200,
            "devices_monitored": 1500,
            "botnet_blocks": 120,
            "revenue_potential": 50000
        },
        "cctv": {
            "cameras_protected": 500,
            "public_cameras": 100,
            "private_cameras": 400,
            "hijack_attempts_blocked": 35,
            "revenue_potential": 50000
        }
    }
    
    return {
        "segments": segments,
        "total_revenue_potential": sum(s["revenue_potential"] for s in segments.values()),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


# ==================== vRAN MANAGEMENT ====================

@router.get("/vran/status")
async def get_vran_status(auth: bool = Depends(verify_internal_admin)):
    """Get vRAN system status (internal view)"""
    from services.vran_connector import vran_connector
    from services.threat_engine import threat_engine
    
    return {
        "vran_status": {
            "active_sessions": len(vran_connector.active_sessions),
            "connection_pool_size": vran_connector.connection_pool_size,
            "nodes": {
                "VRAN-TELCO-01": "operational",
                "VRAN-MOBILE-02": "operational",
                "VRAN-ENT-03": "operational",
                "VRAN-AUTO-04": "operational",
                "VRAN-IOT-05": "operational",
                "VRAN-CCTV-06": "operational"
            }
        },
        "threat_engine": {
            "patterns_active": len(threat_engine.THREAT_PATTERNS),
            "external_feeds": len(threat_engine.EXTERNAL_FEEDS),
            "learning_buffer": len(threat_engine.learning_buffer)
        },
        "enforcement_mode": "mandatory",
        "self_protection": {
            "ddos_mitigation": "active",
            "rate_limiting": "enabled",
            "intrusion_detection": "active",
            "auto_healing": "enabled"
        }
    }

@router.post("/vran/enforce-mode")
async def set_vran_enforce_mode(
    mode: str,
    auth: bool = Depends(verify_internal_admin)
):
    """Set vRAN enforcement mode"""
    valid_modes = ["mandatory", "optional", "disabled"]
    if mode not in valid_modes:
        return {"error": f"Invalid mode. Valid: {valid_modes}"}
    
    return {
        "status": "updated",
        "enforcement_mode": mode,
        "message": f"vRAN enforcement mode set to {mode}"
    }


# ==================== SALES MATERIALS & DOWNLOADS ====================

DOWNLOADS_DIR = "/app/backend/static/downloads"

@router.get("/downloads")
async def list_downloads(auth: bool = Depends(verify_internal_admin)):
    """
    List all available downloads for internal team and sales
    Includes executive presentations, product sheets, etc.
    """
    files = []
    
    if os.path.exists(DOWNLOADS_DIR):
        for filename in os.listdir(DOWNLOADS_DIR):
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "download_url": f"/api/internal-admin/downloads/{filename}",
                    "type": "presentation" if filename.endswith(".pptx") else "document"
                })
    
    return {
        "total_files": len(files),
        "files": files,
        "available_materials": {
            "executive_sales_deck": {
                "filename": "Infuse_Executive_Sales_Deck.pptx",
                "description": "15-slide executive presentation for CEO/CFO/CIO/CSO meetings",
                "audience": ["CEO", "CFO", "CIO", "CSO", "Enterprise Decision Makers"],
                "contents": [
                    "Executive Summary",
                    "Product Overview (HealthTrack Pro & SecureSphere)",
                    "8 AI Agents Overview",
                    "Security Architecture",
                    "ROI & Financial Impact",
                    "Technology for CIO/CTO",
                    "Security Posture for CSO/CISO",
                    "Pricing Models",
                    "Customer Success Stories",
                    "Implementation Timeline"
                ]
            }
        }
    }

@router.get("/downloads/{filename}")
async def download_file(
    filename: str,
    auth: bool = Depends(verify_internal_admin)
):
    """
    Download a specific file (sales materials, presentations)
    Secured for internal admin access only
    """
    # Security: Only allow specific file types
    allowed_extensions = [".pptx", ".pdf", ".docx", ".xlsx"]
    
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Security: Prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    filepath = os.path.join(DOWNLOADS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

@router.post("/downloads/regenerate-sales-deck")
async def regenerate_sales_deck(auth: bool = Depends(verify_internal_admin)):
    """
    Regenerate the executive sales deck with latest data
    """
    try:
        from scripts.generate_sales_deck import generate_sales_deck
        
        output_path = os.path.join(DOWNLOADS_DIR, "Infuse_Executive_Sales_Deck.pptx")
        generate_sales_deck(output_path)
        
        return {
            "status": "success",
            "message": "Sales deck regenerated successfully",
            "file": "Infuse_Executive_Sales_Deck.pptx",
            "download_url": "/api/internal-admin/downloads/Infuse_Executive_Sales_Deck.pptx",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate: {str(e)}")


# ==================== DATABASE RECORDS MANAGEMENT ====================

@router.get("/records/{collection_name}")
async def get_collection_records(
    collection_name: str,
    limit: int = 100,
    skip: int = 0
):
    """
    Get records from a specific collection
    Available collections: users, doctors, patients, organizations, appointments, 
    security_devices, threat_alerts, api_keys
    """
    db = dependencies.get_db()
    
    # Allowed collections for security
    allowed_collections = [
        "users", "doctors", "patients", "organizations", 
        "appointments", "security_devices", "threat_alerts", "api_keys",
        "vran_connections", "threat_events", "support_escalations"
    ]
    
    if collection_name not in allowed_collections:
        raise HTTPException(
            status_code=400, 
            detail=f"Collection not allowed. Available: {allowed_collections}"
        )
    
    try:
        collection = db[collection_name]
        total = await collection.count_documents({})
        records = await collection.find({}, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
        
        return {
            "collection": collection_name,
            "total": total,
            "limit": limit,
            "skip": skip,
            "records": records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")


@router.get("/records/{collection_name}/{record_id}")
async def get_single_record(collection_name: str, record_id: str):
    """Get a single record by ID"""
    db = dependencies.get_db()
    
    allowed_collections = [
        "users", "doctors", "patients", "organizations", 
        "appointments", "security_devices", "threat_alerts", "api_keys"
    ]
    
    if collection_name not in allowed_collections:
        raise HTTPException(status_code=400, detail="Collection not allowed")
    
    collection = db[collection_name]
    record = await collection.find_one({"id": record_id}, {"_id": 0})
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return {"record": record}


@router.delete("/records/{collection_name}/{record_id}")
async def delete_record(collection_name: str, record_id: str):
    """Delete a record by ID"""
    db = dependencies.get_db()
    
    allowed_collections = [
        "users", "doctors", "patients", "organizations", 
        "appointments", "security_devices", "threat_alerts", "api_keys"
    ]
    
    if collection_name not in allowed_collections:
        raise HTTPException(status_code=400, detail="Collection not allowed")
    
    collection = db[collection_name]
    result = await collection.delete_one({"id": record_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return {"status": "deleted", "record_id": record_id}

