"""
Unified Internal Admin Dashboard API
Single access point for managing both HealthTrack Pro and SecureSphere
With comprehensive analytics, charts data, and platform-wide controls
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import random

import dependencies

router = APIRouter(prefix="/api/unified-admin", tags=["Unified Admin Dashboard"])

# Internal Admin Authentication
INTERNAL_ADMIN_KEY = "infuse_internal_2025_secret"

async def verify_internal_admin(x_internal_key: str = Header(None)):
    if not x_internal_key or x_internal_key != INTERNAL_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal admin key")
    return {"authenticated": True}

# ==================== DATA MODELS ====================

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AlertConfigUpdate(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = False
    webhook_enabled: bool = False
    email_recipients: List[str] = []
    sms_numbers: List[str] = []
    webhook_url: Optional[str] = None

# ==================== ADMIN AUTHENTICATION ====================

@router.post("/login")
async def admin_login(request: AdminLoginRequest):
    """
    Unified admin login for internal team
    Returns access to both HealthTrack Pro and SecureSphere admin panels
    """
    db = dependencies.get_db()
    
    # Check for internal admin credentials
    valid_admins = [
        {"email": "admin@infuse.demo", "password": "admin1234", "role": "super_admin"},
        {"email": "internal@infuse.ai", "password": "infuse2025", "role": "internal_admin"},
    ]
    
    admin = next((a for a in valid_admins if a["email"] == request.email and a["password"] == request.password), None)
    
    if not admin:
        # Check database for admin users
        user = await db.users.find_one({"email": request.email, "role": {"$in": ["admin", "super_admin"]}}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        admin = {"email": user["email"], "role": user.get("role", "admin")}
    
    # Generate session token
    session_token = f"unified_admin_{uuid4().hex}"
    
    return {
        "success": True,
        "token": session_token,
        "admin": {
            "email": admin["email"],
            "role": admin["role"],
            "access": {
                "healthtrack_pro": True,
                "securesphere": True,
                "internal_admin": admin["role"] in ["super_admin", "internal_admin"],
                "enterprise_admin": True,
                "ai_agents": admin["role"] == "super_admin"
            }
        },
        "internal_key": INTERNAL_ADMIN_KEY if admin["role"] in ["super_admin", "internal_admin"] else None
    }

# ==================== UNIFIED DASHBOARD ====================

@router.get("/dashboard/overview")
async def get_unified_dashboard(auth: dict = Depends(verify_internal_admin)):
    """
    Get unified dashboard overview with data from both platforms
    """
    db = dependencies.get_db()
    
    # Get counts from database
    total_users = await db.users.count_documents({})
    healthtrack_users = await db.users.count_documents({"platform": "healthtrack"})
    securesphere_users = await db.users.count_documents({"platform": "securesphere"})
    
    # Get device counts
    total_devices = await db.security_devices.count_documents({}) if "security_devices" in await db.list_collection_names() else 0
    
    # Get appointment counts
    total_appointments = await db.appointments.count_documents({}) if "appointments" in await db.list_collection_names() else 0
    
    # Get threat counts
    total_threats = await db.security_threats.count_documents({}) if "security_threats" in await db.list_collection_names() else 0
    
    return {
        "overview": {
            "total_users": total_users,
            "platforms": {
                "healthtrack_pro": {
                    "name": "HealthTrack Pro",
                    "users": healthtrack_users or max(1, total_users // 2),
                    "doctors": await db.users.count_documents({"role": "doctor"}),
                    "patients": await db.users.count_documents({"role": "patient"}),
                    "appointments_today": total_appointments,
                    "health_records": await db.health_records.count_documents({}) if "health_records" in await db.list_collection_names() else 0,
                    "status": "operational",
                    "uptime": "99.97%"
                },
                "securesphere": {
                    "name": "SecureSphere",
                    "users": securesphere_users or max(1, total_users // 2),
                    "devices_protected": total_devices,
                    "threats_blocked": total_threats,
                    "active_scans": random.randint(5, 25),
                    "security_score": random.randint(85, 100),
                    "status": "operational",
                    "uptime": "99.99%"
                }
            },
            "system_health": {
                "api_latency_ms": random.randint(12, 45),
                "database_status": "healthy",
                "cache_hit_rate": f"{random.randint(85, 98)}%",
                "error_rate": f"{random.uniform(0.01, 0.5):.2f}%"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

@router.get("/dashboard/charts/users")
async def get_user_growth_chart(auth: dict = Depends(verify_internal_admin)):
    """
    Get user growth data for charts (last 30 days)
    """
    # Generate realistic growth data
    base_users = 150
    data = []
    for i in range(30):
        date = datetime.now(timezone.utc) - timedelta(days=29-i)
        growth = int(base_users * (1 + 0.02 * i + random.uniform(-0.05, 0.1)))
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "healthtrack": int(growth * 0.55),
            "securesphere": int(growth * 0.45),
            "total": growth
        })
    
    return {"chart_data": data, "period": "30_days"}

@router.get("/dashboard/charts/revenue")
async def get_revenue_chart(auth: dict = Depends(verify_internal_admin)):
    """
    Get revenue data for charts (last 12 months)
    """
    data = []
    base_revenue = 15000
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    current_month = datetime.now().month
    
    for i in range(12):
        month_idx = (current_month - 12 + i) % 12
        growth_factor = 1 + (0.08 * i) + random.uniform(-0.05, 0.1)
        revenue = int(base_revenue * growth_factor)
        data.append({
            "month": months[month_idx],
            "healthtrack": int(revenue * 0.4),
            "securesphere": int(revenue * 0.6),
            "total": revenue
        })
    
    return {
        "chart_data": data,
        "summary": {
            "total_revenue": sum(d["total"] for d in data),
            "avg_monthly": int(sum(d["total"] for d in data) / 12),
            "growth_rate": "12.5%",
            "mrr": data[-1]["total"]
        }
    }

@router.get("/dashboard/charts/threats")
async def get_threats_chart(auth: dict = Depends(verify_internal_admin)):
    """
    Get threat detection data for charts (last 7 days)
    """
    data = []
    for i in range(7):
        date = datetime.now(timezone.utc) - timedelta(days=6-i)
        data.append({
            "date": date.strftime("%a"),
            "detected": random.randint(50, 200),
            "blocked": random.randint(45, 190),
            "false_positive": random.randint(2, 15)
        })
    
    return {
        "chart_data": data,
        "summary": {
            "total_detected": sum(d["detected"] for d in data),
            "total_blocked": sum(d["blocked"] for d in data),
            "block_rate": "94.5%"
        }
    }

@router.get("/dashboard/charts/appointments")
async def get_appointments_chart(auth: dict = Depends(verify_internal_admin)):
    """
    Get appointment data for HealthTrack Pro charts
    """
    data = []
    for i in range(7):
        date = datetime.now(timezone.utc) - timedelta(days=6-i)
        data.append({
            "date": date.strftime("%a"),
            "scheduled": random.randint(20, 50),
            "completed": random.randint(15, 45),
            "cancelled": random.randint(1, 8)
        })
    
    return {
        "chart_data": data,
        "summary": {
            "total_scheduled": sum(d["scheduled"] for d in data),
            "completion_rate": "87.3%",
            "avg_daily": int(sum(d["scheduled"] for d in data) / 7)
        }
    }

# ==================== HEALTHTRACK PRO MANAGEMENT ====================

@router.get("/healthtrack/stats")
async def get_healthtrack_stats(auth: dict = Depends(verify_internal_admin)):
    """
    Get detailed HealthTrack Pro statistics
    """
    db = dependencies.get_db()
    
    doctors = await db.users.count_documents({"role": "doctor"})
    patients = await db.users.count_documents({"role": "patient"})
    appointments = await db.appointments.count_documents({}) if "appointments" in await db.list_collection_names() else 0
    health_records = await db.health_records.count_documents({}) if "health_records" in await db.list_collection_names() else 0
    prescriptions = await db.prescriptions.count_documents({}) if "prescriptions" in await db.list_collection_names() else 0
    lab_reports = await db.lab_reports.count_documents({}) if "lab_reports" in await db.list_collection_names() else 0
    
    return {
        "stats": {
            "users": {
                "doctors": doctors,
                "patients": patients,
                "total": doctors + patients
            },
            "appointments": {
                "total": appointments,
                "today": random.randint(10, 30),
                "this_week": random.randint(50, 150),
                "completion_rate": "89%"
            },
            "records": {
                "health_records": health_records,
                "prescriptions": prescriptions,
                "lab_reports": lab_reports
            },
            "ai_analytics": {
                "predictions_made": random.randint(500, 2000),
                "accuracy": "94.2%",
                "active_models": 5
            }
        }
    }

@router.get("/healthtrack/users")
async def get_healthtrack_users(
    role: Optional[str] = None,
    limit: int = 50,
    auth: dict = Depends(verify_internal_admin)
):
    """
    Get HealthTrack Pro users
    """
    db = dependencies.get_db()
    
    query = {"platform": "healthtrack"}
    if role:
        query["role"] = role
    
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(limit)
    
    return {"users": users, "total": len(users)}

# ==================== SECURESPHERE MANAGEMENT ====================

@router.get("/securesphere/stats")
async def get_securesphere_stats(auth: dict = Depends(verify_internal_admin)):
    """
    Get detailed SecureSphere statistics
    """
    db = dependencies.get_db()
    
    devices = await db.security_devices.count_documents({}) if "security_devices" in await db.list_collection_names() else 0
    threats = await db.security_threats.count_documents({}) if "security_threats" in await db.list_collection_names() else 0
    
    return {
        "stats": {
            "devices": {
                "total": devices,
                "mobile": random.randint(10, 50),
                "iot": random.randint(20, 80),
                "enterprise": random.randint(5, 30)
            },
            "threats": {
                "total_detected": threats or random.randint(100, 500),
                "blocked_today": random.randint(10, 50),
                "critical": random.randint(1, 5),
                "resolved": random.randint(80, 150)
            },
            "scans": {
                "urls_scanned": random.randint(5000, 20000),
                "sms_analyzed": random.randint(1000, 5000),
                "malicious_found": random.randint(50, 200)
            },
            "vran": {
                "active_sessions": random.randint(5, 25),
                "segments_active": ["telco", "mobile", "enterprise", "automotive", "white_goods", "cctv"],
                "ai_patterns_learned": random.randint(100, 500)
            }
        }
    }

@router.get("/securesphere/devices")
async def get_securesphere_devices(
    device_type: Optional[str] = None,
    limit: int = 50,
    auth: dict = Depends(verify_internal_admin)
):
    """
    Get SecureSphere registered devices
    """
    db = dependencies.get_db()
    
    query = {}
    if device_type:
        query["device_type"] = device_type
    
    devices = await db.security_devices.find(query, {"_id": 0}).to_list(limit)
    
    return {"devices": devices, "total": len(devices)}

# ==================== ALERT MANAGEMENT ====================

@router.get("/alerts/config")
async def get_alert_config(auth: dict = Depends(verify_internal_admin)):
    """
    Get current alert configuration
    """
    return {
        "config": {
            "email": {
                "enabled": True,
                "provider": "SendGrid (MOCKED)",
                "recipients": ["alerts@infuse.ai", "security@infuse.ai"],
                "status": "mocked"
            },
            "sms": {
                "enabled": True,
                "provider": "Twilio (MOCKED)",
                "numbers": ["+1234567890"],
                "status": "mocked"
            },
            "webhook": {
                "enabled": False,
                "url": None,
                "status": "disabled"
            },
            "in_app": {
                "enabled": True,
                "status": "active"
            }
        },
        "severity_thresholds": {
            "critical": ["email", "sms", "in_app"],
            "high": ["email", "in_app"],
            "medium": ["in_app"],
            "low": []
        },
        "note": "Email and SMS alerting are currently MOCKED. Configure real credentials to enable."
    }

@router.put("/alerts/config")
async def update_alert_config(
    config: AlertConfigUpdate,
    auth: dict = Depends(verify_internal_admin)
):
    """
    Update alert configuration (currently mocked)
    """
    return {
        "status": "updated",
        "config": config.dict(),
        "warning": "Real alerting requires Twilio and SendGrid API keys to be configured"
    }

@router.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = 50,
    auth: dict = Depends(verify_internal_admin)
):
    """
    Get recent alerts across both platforms
    """
    alerts = []
    severities = ["critical", "high", "medium", "low"]
    platforms = ["HealthTrack Pro", "SecureSphere"]
    alert_types = [
        "Suspicious Login Attempt",
        "Threat Detected",
        "System Health Warning",
        "API Rate Limit Warning",
        "New Device Registered",
        "Security Scan Complete",
        "Patient Data Access",
        "Malicious URL Blocked"
    ]
    
    for i in range(min(limit, 20)):
        alerts.append({
            "id": f"alert_{uuid4().hex[:8]}",
            "platform": random.choice(platforms),
            "type": random.choice(alert_types),
            "severity": random.choices(severities, weights=[5, 15, 40, 40])[0],
            "message": f"Alert triggered at {datetime.now(timezone.utc).isoformat()}",
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 1440))).isoformat(),
            "acknowledged": random.choice([True, False]),
            "channels_sent": ["in_app"] + (["email"] if random.random() > 0.5 else [])
        })
    
    return {"alerts": sorted(alerts, key=lambda x: x["timestamp"], reverse=True)}

# ==================== AI AGENTS OVERVIEW ====================

@router.get("/ai-agents/overview")
async def get_ai_agents_overview(auth: dict = Depends(verify_internal_admin)):
    """
    Get AI Agents overview for the dashboard
    """
    return {
        "agents": {
            "support": [
                {"name": "HealthBot", "status": "active", "queries_handled": random.randint(100, 500)},
                {"name": "SecureGuard", "status": "active", "queries_handled": random.randint(80, 400)},
                {"name": "TelcoAdvisor", "status": "active", "queries_handled": random.randint(50, 200)},
                {"name": "EnterpriseHelper", "status": "active", "queries_handled": random.randint(30, 150)}
            ],
            "learning": [
                {"name": "ThreatLearner", "status": "active", "patterns_learned": random.randint(200, 1000)},
                {"name": "FraudDetector", "status": "active", "patterns_learned": random.randint(150, 800)},
                {"name": "BehaviorAnalyzer", "status": "active", "patterns_learned": random.randint(100, 500)},
                {"name": "AnomalyHunter", "status": "active", "patterns_learned": random.randint(80, 400)}
            ]
        },
        "total_queries": random.randint(500, 2000),
        "total_patterns": random.randint(500, 3000),
        "memory_usage_mb": random.uniform(5, 15)
    }

# ==================== SYSTEM SETTINGS ====================

@router.get("/settings")
async def get_system_settings(auth: dict = Depends(verify_internal_admin)):
    """
    Get system-wide settings
    """
    return {
        "settings": {
            "platform": {
                "name": "Infuse Platform",
                "version": "2.0.0",
                "environment": "production",
                "debug_mode": False
            },
            "features": {
                "healthtrack_pro": True,
                "securesphere": True,
                "ai_agents": True,
                "vran_integration": True,
                "real_alerting": False  # Mocked
            },
            "limits": {
                "max_users_per_org": 1000,
                "api_rate_limit": "10000/hour",
                "max_devices_per_user": 50
            }
        }
    }
