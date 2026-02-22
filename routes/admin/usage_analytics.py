"""
Usage Analytics Dashboard
Track API usage, user activity, and system metrics
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4

router = APIRouter(prefix="/api/admin/analytics", tags=["Admin - Analytics"])

# Get database
from dependencies import get_database


@router.get("/overview")
async def get_analytics_overview(days: int = 30, db=Depends(get_database)):
    """Get overall platform analytics"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # User stats
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"last_login": {"$gte": date_from}})
    new_users = await db.users.count_documents({"created_at": {"$gte": date_from}})
    
    # API usage
    total_api_calls = await db.api_usage.count_documents({"timestamp": {"$gte": date_from}})
    
    # Product usage
    healthtrack_users = await db.users.count_documents({"active_products": "healthtrack"})
    securesphere_users = await db.users.count_documents({"active_products": "securesphere"})
    
    # Security stats
    url_scans = await db.url_scans.count_documents({"created_at": {"$gte": date_from}})
    threats_detected = await db.url_scans.count_documents({"created_at": {"$gte": date_from}, "is_safe": False})
    sms_analyses = await db.sms_analyses.count_documents({"created_at": {"$gte": date_from}})
    
    # Healthcare stats
    appointments = await db.appointments.count_documents({"created_at": {"$gte": date_from}})
    patients = await db.patients.count_documents({})
    prescriptions = await db.prescriptions.count_documents({"created_at": {"$gte": date_from}})
    
    return {
        "overview": {
            "period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "users": {
                "total": total_users,
                "active": active_users,
                "new": new_users,
                "growth_rate": round((new_users / max(total_users - new_users, 1)) * 100, 2)
            },
            "api": {
                "total_calls": total_api_calls,
                "avg_daily": round(total_api_calls / max(days, 1), 2)
            },
            "products": {
                "healthtrack": {
                    "users": healthtrack_users,
                    "appointments": appointments,
                    "patients": patients,
                    "prescriptions": prescriptions
                },
                "securesphere": {
                    "users": securesphere_users,
                    "url_scans": url_scans,
                    "threats_detected": threats_detected,
                    "sms_analyses": sms_analyses,
                    "threat_rate": round((threats_detected / max(url_scans, 1)) * 100, 2)
                }
            }
        }
    }


@router.get("/users")
async def get_user_analytics(days: int = 30, db=Depends(get_database)):
    """Get user-related analytics"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # User growth over time
    growth_pipeline = [
        {"$match": {"created_at": {"$gte": date_from}}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_signups = []
    async for doc in db.users.aggregate(growth_pipeline):
        daily_signups.append({"date": doc["_id"], "signups": doc["count"]})
    
    # User roles distribution
    role_pipeline = [
        {"$group": {"_id": "$role", "count": {"$sum": 1}}}
    ]
    role_distribution = {}
    async for doc in db.users.aggregate(role_pipeline):
        role_distribution[doc["_id"] or "user"] = doc["count"]
    
    # Active sessions
    active_sessions = await db.sessions.count_documents({"expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}})
    
    # Login frequency
    login_pipeline = [
        {"$match": {"event_type": "login", "timestamp": {"$gte": date_from}}},
        {"$group": {
            "_id": {"$substr": ["$timestamp", 0, 10]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_logins = []
    async for doc in db.audit_logs.aggregate(login_pipeline):
        daily_logins.append({"date": doc["_id"], "logins": doc["count"]})
    
    return {
        "period_days": days,
        "daily_signups": daily_signups,
        "role_distribution": role_distribution,
        "active_sessions": active_sessions,
        "daily_logins": daily_logins
    }


@router.get("/api-usage")
async def get_api_usage_analytics(days: int = 30, db=Depends(get_database)):
    """Get API usage analytics"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Endpoint usage
    endpoint_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}}},
        {"$group": {
            "_id": "$endpoint",
            "count": {"$sum": 1},
            "avg_response_time": {"$avg": "$response_time"}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    top_endpoints = []
    async for doc in db.api_usage.aggregate(endpoint_pipeline):
        top_endpoints.append({
            "endpoint": doc["_id"],
            "requests": doc["count"],
            "avg_response_time_ms": round(doc.get("avg_response_time", 0), 2)
        })
    
    # Status code distribution
    status_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}}},
        {"$group": {"_id": "$status_code", "count": {"$sum": 1}}}
    ]
    status_distribution = {}
    async for doc in db.api_usage.aggregate(status_pipeline):
        status_distribution[str(doc["_id"])] = doc["count"]
    
    # Hourly distribution
    hourly_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}}},
        {"$group": {
            "_id": {"$substr": ["$timestamp", 11, 2]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    hourly_distribution = {}
    async for doc in db.api_usage.aggregate(hourly_pipeline):
        hourly_distribution[doc["_id"]] = doc["count"]
    
    # API key usage
    api_key_pipeline = [
        {"$match": {"timestamp": {"$gte": date_from}, "api_key_id": {"$ne": None}}},
        {"$group": {
            "_id": "$api_key_id",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_api_keys = []
    async for doc in db.api_usage.aggregate(api_key_pipeline):
        top_api_keys.append({"key_id": doc["_id"], "requests": doc["count"]})
    
    return {
        "period_days": days,
        "top_endpoints": top_endpoints,
        "status_distribution": status_distribution,
        "hourly_distribution": hourly_distribution,
        "top_api_keys": top_api_keys
    }


@router.get("/security")
async def get_security_analytics(days: int = 30, db=Depends(get_database)):
    """Get security-related analytics for SecureSphere"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # URL scan statistics
    total_scans = await db.url_scans.count_documents({"created_at": {"$gte": date_from}})
    safe_urls = await db.url_scans.count_documents({"created_at": {"$gte": date_from}, "is_safe": True})
    threats = total_scans - safe_urls
    
    # Threat categories
    threat_pipeline = [
        {"$match": {"created_at": {"$gte": date_from}, "is_safe": False}},
        {"$group": {"_id": "$threat_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    threat_categories = {}
    async for doc in db.url_scans.aggregate(threat_pipeline):
        threat_categories[doc["_id"] or "unknown"] = doc["count"]
    
    # SMS fraud detection
    sms_total = await db.sms_analyses.count_documents({"created_at": {"$gte": date_from}})
    sms_fraud = await db.sms_analyses.count_documents({"created_at": {"$gte": date_from}, "is_fraud": True})
    
    # Device security
    total_devices = await db.devices.count_documents({})
    compromised_devices = await db.devices.count_documents({"status": "compromised"})
    
    # Daily threat trends
    trend_pipeline = [
        {"$match": {"created_at": {"$gte": date_from}, "is_safe": False}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_threats = []
    async for doc in db.url_scans.aggregate(trend_pipeline):
        daily_threats.append({"date": doc["_id"], "threats": doc["count"]})
    
    return {
        "period_days": days,
        "url_scanning": {
            "total_scans": total_scans,
            "safe": safe_urls,
            "threats": threats,
            "threat_rate": round((threats / max(total_scans, 1)) * 100, 2)
        },
        "threat_categories": threat_categories,
        "sms_analysis": {
            "total": sms_total,
            "fraud_detected": sms_fraud,
            "fraud_rate": round((sms_fraud / max(sms_total, 1)) * 100, 2)
        },
        "devices": {
            "total": total_devices,
            "compromised": compromised_devices
        },
        "daily_threats": daily_threats
    }


@router.get("/healthcare")
async def get_healthcare_analytics(days: int = 30, db=Depends(get_database)):
    """Get healthcare-related analytics for HealthTrack Pro"""
    date_from = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Patient statistics
    total_patients = await db.patients.count_documents({})
    new_patients = await db.patients.count_documents({"created_at": {"$gte": date_from}})
    
    # Appointment statistics
    total_appointments = await db.appointments.count_documents({"created_at": {"$gte": date_from}})
    completed = await db.appointments.count_documents({"created_at": {"$gte": date_from}, "status": "completed"})
    cancelled = await db.appointments.count_documents({"created_at": {"$gte": date_from}, "status": "cancelled"})
    
    # Prescription statistics
    prescriptions = await db.prescriptions.count_documents({"created_at": {"$gte": date_from}})
    
    # Lab tests
    lab_tests = await db.lab_tests.count_documents({"created_at": {"$gte": date_from}})
    
    # Daily appointments trend
    appt_pipeline = [
        {"$match": {"created_at": {"$gte": date_from}}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_appointments = []
    async for doc in db.appointments.aggregate(appt_pipeline):
        daily_appointments.append({"date": doc["_id"], "appointments": doc["count"]})
    
    return {
        "period_days": days,
        "patients": {
            "total": total_patients,
            "new": new_patients
        },
        "appointments": {
            "total": total_appointments,
            "completed": completed,
            "cancelled": cancelled,
            "completion_rate": round((completed / max(total_appointments, 1)) * 100, 2)
        },
        "prescriptions": prescriptions,
        "lab_tests": lab_tests,
        "daily_appointments": daily_appointments
    }


@router.get("/realtime")
async def get_realtime_metrics(db=Depends(get_database)):
    """Get real-time platform metrics"""
    now = datetime.now(timezone.utc)
    last_hour = (now - timedelta(hours=1)).isoformat()
    last_5_min = (now - timedelta(minutes=5)).isoformat()
    
    # Active users (logged in within last hour)
    active_users = await db.users.count_documents({"last_login": {"$gte": last_hour}})
    
    # API requests in last 5 minutes
    recent_requests = await db.api_usage.count_documents({"timestamp": {"$gte": last_5_min}})
    
    # Recent errors
    recent_errors = await db.api_usage.count_documents({
        "timestamp": {"$gte": last_5_min},
        "status_code": {"$gte": 400}
    })
    
    # Recent threats
    recent_threats = await db.url_scans.count_documents({
        "created_at": {"$gte": last_hour},
        "is_safe": False
    })
    
    return {
        "metrics": {
            "timestamp": now.isoformat(),
            "active_users": active_users,
            "requests_last_5min": recent_requests,
            "errors_last_5min": recent_errors,
            "error_rate": round((recent_errors / max(recent_requests, 1)) * 100, 2),
            "threats_last_hour": recent_threats,
            "status": "healthy" if recent_errors < recent_requests * 0.1 else "degraded"
        }
    }
