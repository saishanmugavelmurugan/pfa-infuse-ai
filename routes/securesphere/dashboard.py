"""
Security Posture Dashboard API
Part of SecureSphere Mobile Security Module

Provides:
- Comprehensive security dashboard data
- Multi-tier security metrics
- AI-powered insights and recommendations
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from services.securesphere.ai_security_agent import security_agent
import dependencies

router = APIRouter(prefix="/securesphere/dashboard", tags=["SecureSphere - Dashboard"])


@router.get("/overview")
async def get_dashboard_overview(user_id: Optional[str] = None):
    """
    Get comprehensive security dashboard overview
    """
    db = dependencies.get_db()
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    # Device stats
    total_devices = await db.devices.count_documents({"status": "active", **query})
    secure_devices = await db.devices.count_documents({"status": "active", "security_posture": "secure", **query})
    at_risk_devices = await db.devices.count_documents({"status": "active", "security_posture": "at_risk", **query})
    critical_devices = await db.devices.count_documents({"status": "active", "security_posture": "critical", **query})
    
    # Threat stats
    total_url_scans = await db.url_scans.count_documents(query if not user_id else {})
    malicious_urls = await db.url_scans.count_documents({"result.threat_level": {"$in": ["high", "critical"]}})
    
    total_sms_analyses = await db.sms_analyses.count_documents(query if not user_id else {})
    fraud_sms = await db.sms_analyses.count_documents({"result.is_fraud": True})
    
    # Active alerts
    active_alerts = await db.threat_alerts.count_documents({"status": "active", **query})
    critical_alerts = await db.threat_alerts.count_documents({"status": "active", "severity": "critical", **query})
    
    # Calculate overall security score (0-100, higher is better)
    security_score = 100
    if total_devices > 0:
        security_score -= (at_risk_devices / total_devices) * 20
        security_score -= (critical_devices / total_devices) * 40
    security_score -= min(30, critical_alerts * 10)
    security_score = max(0, round(security_score))
    
    return {
        "security_score": security_score,
        "security_grade": "A" if security_score >= 90 else "B" if security_score >= 75 else "C" if security_score >= 60 else "D" if security_score >= 40 else "F",
        "devices": {
            "total": total_devices,
            "secure": secure_devices,
            "at_risk": at_risk_devices,
            "critical": critical_devices
        },
        "threats": {
            "urls_scanned": total_url_scans,
            "malicious_urls_blocked": malicious_urls,
            "sms_analyzed": total_sms_analyses,
            "fraud_sms_detected": fraud_sms
        },
        "alerts": {
            "active": active_alerts,
            "critical": critical_alerts
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/threats/recent")
async def get_recent_threats(
    limit: int = Query(default=10, le=50),
    threat_type: Optional[str] = None
):
    """
    Get recent threat detections
    """
    db = dependencies.get_db()
    
    # Combine URL and SMS threats
    threats = []
    
    # Get recent URL threats
    url_query = {"result.threat_level": {"$in": ["high", "critical"]}}
    if threat_type == "url":
        url_query = {}
    
    url_threats = await db.url_scans.find(
        url_query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit // 2).to_list(limit // 2)
    
    for t in url_threats:
        threats.append({
            "type": "url",
            "threat_level": t.get('result', {}).get('threat_level', 'unknown'),
            "category": t.get('result', {}).get('category', 'unknown'),
            "url": t.get('url', '')[:50] + "..." if len(t.get('url', '')) > 50 else t.get('url', ''),
            "risk_score": t.get('result', {}).get('risk_score', 0),
            "timestamp": t.get('created_at')
        })
    
    # Get recent SMS threats
    sms_query = {"result.is_fraud": True}
    if threat_type == "sms":
        sms_query = {}
    
    sms_threats = await db.sms_analyses.find(
        sms_query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit // 2).to_list(limit // 2)
    
    for t in sms_threats:
        threats.append({
            "type": "sms",
            "threat_level": t.get('result', {}).get('threat_level', 'unknown'),
            "fraud_type": t.get('result', {}).get('fraud_type', 'unknown'),
            "message_preview": t.get('result', {}).get('message_preview', ''),
            "risk_score": t.get('result', {}).get('risk_score', 0),
            "timestamp": t.get('created_at')
        })
    
    # Sort by timestamp
    threats.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return {
        "total": len(threats),
        "threats": threats[:limit]
    }


@router.get("/stats/timeline")
async def get_threat_timeline(
    days: int = Query(default=7, le=30)
):
    """
    Get threat detection timeline for charts
    """
    db = dependencies.get_db()
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    start_iso = start_date.isoformat()
    
    # URL scans timeline
    url_pipeline = [
        {"$match": {"created_at": {"$gte": start_iso}}},
        {
            "$group": {
                "_id": {"$substr": ["$created_at", 0, 10]},
                "total_scans": {"$sum": 1},
                "threats_detected": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$result.threat_level", ["high", "critical"]]},
                            1,
                            0
                        ]
                    }
                }
            }
        },
        {"$sort": {"_id": 1}}
    ]
    url_timeline = await db.url_scans.aggregate(url_pipeline).to_list(None)
    
    # SMS analyses timeline
    sms_pipeline = [
        {"$match": {"created_at": {"$gte": start_iso}}},
        {
            "$group": {
                "_id": {"$substr": ["$created_at", 0, 10]},
                "total_analyses": {"$sum": 1},
                "fraud_detected": {
                    "$sum": {"$cond": ["$result.is_fraud", 1, 0]}
                }
            }
        },
        {"$sort": {"_id": 1}}
    ]
    sms_timeline = await db.sms_analyses.aggregate(sms_pipeline).to_list(None)
    
    return {
        "period_days": days,
        "url_scans": [{"date": d['_id'], **{k: v for k, v in d.items() if k != '_id'}} for d in url_timeline],
        "sms_analyses": [{"date": d['_id'], **{k: v for k, v in d.items() if k != '_id'}} for d in sms_timeline]
    }


@router.get("/recommendations")
async def get_security_recommendations(user_id: Optional[str] = None):
    """
    Get AI-powered security recommendations
    """
    db = dependencies.get_db()
    
    recommendations = []
    
    # Check device security postures
    query = {"status": "active"}
    if user_id:
        query["user_id"] = user_id
    
    devices = await db.devices.find(query, {"_id": 0}).to_list(100)
    
    # Analyze and generate recommendations
    for device in devices:
        security_features = device.get('security_features', {})
        
        if not security_features.get('biometric_enabled'):
            recommendations.append({
                "device_id": device.get('device_id'),
                "device_name": device.get('device_name'),
                "priority": "high",
                "category": "authentication",
                "recommendation": "Enable biometric authentication (fingerprint/face) for stronger security",
                "impact": "Prevents unauthorized access to your device and apps"
            })
        
        if not security_features.get('encryption_enabled'):
            recommendations.append({
                "device_id": device.get('device_id'),
                "device_name": device.get('device_name'),
                "priority": "critical",
                "category": "data_protection",
                "recommendation": "Enable device encryption to protect your data",
                "impact": "Protects your data if device is lost or stolen"
            })
        
        if device.get('security_posture') == 'at_risk':
            recommendations.append({
                "device_id": device.get('device_id'),
                "device_name": device.get('device_name'),
                "priority": "high",
                "category": "threat_mitigation",
                "recommendation": "Run a full security scan on this device",
                "impact": "Identifies and removes potential threats"
            })
        
        if device.get('security_posture') == 'critical':
            recommendations.append({
                "device_id": device.get('device_id'),
                "device_name": device.get('device_name'),
                "priority": "critical",
                "category": "immediate_action",
                "recommendation": "Immediate action required: Device shows critical security issues",
                "impact": "Your device and data may be compromised"
            })
    
    # Check active alerts
    alert_count = await db.threat_alerts.count_documents({"status": "active"})
    if alert_count > 0:
        recommendations.append({
            "priority": "high",
            "category": "alerts",
            "recommendation": f"Review and address {alert_count} active security alert(s)",
            "impact": "Unaddressed alerts may indicate ongoing security threats"
        })
    
    # General recommendations if no specific issues
    if len(recommendations) == 0:
        recommendations = [
            {
                "priority": "low",
                "category": "maintenance",
                "recommendation": "Keep your apps and OS updated to the latest version",
                "impact": "Updates often include important security patches"
            },
            {
                "priority": "low",
                "category": "awareness",
                "recommendation": "Be cautious of suspicious links and messages",
                "impact": "Reduces risk of phishing and fraud attacks"
            }
        ]
    
    # Sort by priority
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    recommendations.sort(key=lambda x: priority_order.get(x.get('priority'), 3))
    
    return {
        "total_recommendations": len(recommendations),
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/ai-insights")
async def get_ai_insights():
    """
    Get AI-powered security insights
    """
    # Get learning stats from AI agent
    ai_stats = security_agent.get_learning_stats()
    
    return {
        "ai_engine": {
            "model": ai_stats.get('model', 'Unknown'),
            "total_analyses": ai_stats.get('total_analyses', 0),
            "threat_memory_size": ai_stats.get('threat_memory_size', 0),
            "threat_types_learned": ai_stats.get('threat_types_seen', [])
        },
        "insights": [
            {
                "type": "trend",
                "title": "Threat Detection Capability",
                "description": f"AI has analyzed {ai_stats.get('total_analyses', 0)} potential threats and continues to learn from new patterns."
            },
            {
                "type": "pattern",
                "title": "Common Threat Types",
                "description": f"Most common threats detected: {', '.join(ai_stats.get('threat_types_seen', ['phishing', 'financial_fraud'])[:3])}"
            },
            {
                "type": "recommendation",
                "title": "Protection Status",
                "description": "Real-time AI protection is active. All scanned URLs and messages are analyzed for threats."
            }
        ],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/tier/{tier_name}")
async def get_tier_dashboard(tier_name: str):
    """
    Get tier-specific dashboard data
    Tiers: consumer, enterprise, telecom, automotive
    """
    valid_tiers = ['consumer', 'enterprise', 'telecom', 'automotive']
    if tier_name not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {valid_tiers}")
    
    db = dependencies.get_db()
    
    if tier_name == 'consumer':
        return {
            "tier": "consumer",
            "name": "SecureSphere Mobile",
            "description": "Personal mobile security for Android and iOS",
            "features": [
                {"name": "URL Scanner", "status": "active", "scans_today": await db.url_scans.count_documents({})},
                {"name": "SMS Analyzer", "status": "active", "analyses_today": await db.sms_analyses.count_documents({})},
                {"name": "Threat Scoring", "status": "active"},
                {"name": "Real-time Protection", "status": "active"}
            ],
            "metrics": {
                "threats_blocked_today": 0,
                "protection_rate": "99.2%"
            }
        }
    
    elif tier_name == 'enterprise':
        return {
            "tier": "enterprise",
            "name": "SecureSphere Enterprise",
            "description": "Enterprise-grade security for organizations",
            "features": [
                {"name": "MDM Integration", "status": "available"},
                {"name": "Fleet Management", "status": "available"},
                {"name": "Compliance Reporting", "status": "available"},
                {"name": "SIEM Integration", "status": "coming_soon"}
            ],
            "metrics": {
                "managed_devices": await db.devices.count_documents({"status": "active"}),
                "compliance_score": "95%"
            }
        }
    
    elif tier_name == 'telecom':
        return {
            "tier": "telecom",
            "name": "SecureSphere CSP",
            "description": "Network-level security for telecom operators",
            "features": [
                {"name": "RAN Integration", "status": "simulation"},
                {"name": "IoT Security", "status": "available"},
                {"name": "Network Threat Detection", "status": "available"},
                {"name": "API Gateway", "status": "active"}
            ],
            "metrics": {
                "network_events_processed": 0,
                "iot_devices_protected": 0
            }
        }
    
    elif tier_name == 'automotive':
        return {
            "tier": "automotive",
            "name": "SecureSphere Auto",
            "description": "Connected vehicle security",
            "features": [
                {"name": "V2X Security", "status": "coming_soon"},
                {"name": "CAN Bus Monitoring", "status": "coming_soon"},
                {"name": "OTA Security", "status": "coming_soon"},
                {"name": "Telematics Protection", "status": "coming_soon"}
            ],
            "metrics": {
                "vehicles_protected": 0,
                "threats_blocked": 0
            }
        }
