"""
Real-Time Threat Scoring API
Part of SecureSphere Mobile Security Module

Provides:
- Device security posture assessment
- Real-time threat score calculation
- Multi-factor risk analysis
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
from uuid import uuid4

from services.securesphere.ai_security_agent import security_agent
import dependencies

router = APIRouter(prefix="/securesphere/threat-score", tags=["SecureSphere - Threat Scoring"])


class DeviceSecurityData(BaseModel):
    device_id: str
    platform: str  # android, ios, windows, macos
    os_version: Optional[str] = None
    network: Optional[Dict] = None  # {type, vpn_active, public_wifi, encrypted}
    apps: Optional[List[Dict]] = None  # [{name, source, permissions}]
    behavior: Optional[Dict] = None  # {unusual_data_usage, background_activity_high}
    location: Optional[str] = None


class ThreatAlertRequest(BaseModel):
    device_id: str
    alert_type: str
    severity: str
    details: Dict


@router.post("/calculate")
async def calculate_threat_score(data: DeviceSecurityData):
    """
    Calculate real-time threat score for a device
    Analyzes network, apps, behavior, and contextual factors
    """
    try:
        # Calculate comprehensive threat score
        result = await security_agent.calculate_threat_score(data.dict())
        
        # Store score in database
        db = dependencies.get_db()
        score_record = {
            "id": result['score_id'],
            "device_id": data.device_id,
            "platform": data.platform,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.threat_scores.insert_one(score_record)
        
        # Update device's latest score
        await db.devices.update_one(
            {"device_id": data.device_id},
            {
                "$set": {
                    "latest_threat_score": result['overall_threat_score'],
                    "security_posture": result['posture'],
                    "last_scored": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/{device_id}")
async def get_device_threat_score(device_id: str):
    """
    Get current threat score for a specific device
    """
    db = dependencies.get_db()
    
    device = await db.devices.find_one(
        {"device_id": device_id},
        {"_id": 0}
    )
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get latest threat score details
    latest_score = await db.threat_scores.find_one(
        {"device_id": device_id},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    return {
        "device_id": device_id,
        "current_score": device.get('latest_threat_score', 50),
        "security_posture": device.get('security_posture', 'unknown'),
        "last_updated": device.get('last_scored'),
        "detailed_score": latest_score.get('result') if latest_score else None
    }


@router.get("/history/{device_id}")
async def get_threat_score_history(
    device_id: str,
    limit: int = Query(default=50, le=200)
):
    """
    Get threat score history for a device
    Useful for tracking security posture over time
    """
    db = dependencies.get_db()
    
    scores = await db.threat_scores.find(
        {"device_id": device_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "device_id": device_id,
        "total_records": len(scores),
        "history": scores
    }


@router.post("/alert")
async def create_threat_alert(alert: ThreatAlertRequest):
    """
    Create a new threat alert for a device
    """
    db = dependencies.get_db()
    
    alert_id = str(uuid4())
    alert_record = {
        "id": alert_id,
        "device_id": alert.device_id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "details": alert.details,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.threat_alerts.insert_one(alert_record)
    
    return {
        "alert_id": alert_id,
        "message": "Alert created successfully",
        "severity": alert.severity
    }


@router.get("/alerts/{device_id}")
async def get_device_alerts(
    device_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=20, le=100)
):
    """
    Get threat alerts for a device
    """
    db = dependencies.get_db()
    
    query = {"device_id": device_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity
    
    alerts = await db.threat_alerts.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "device_id": device_id,
        "total_alerts": len(alerts),
        "alerts": alerts
    }


@router.put("/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str):
    """
    Dismiss a threat alert
    """
    db = dependencies.get_db()
    
    result = await db.threat_alerts.update_one(
        {"id": alert_id},
        {
            "$set": {
                "status": "dismissed",
                "dismissed_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert dismissed", "alert_id": alert_id}


@router.get("/posture/summary")
async def get_security_posture_summary(user_id: Optional[str] = None):
    """
    Get security posture summary across all devices
    """
    db = dependencies.get_db()
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    # Aggregate device security stats
    pipeline = [
        {"$match": query},
        {
            "$group": {
                "_id": "$security_posture",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$latest_threat_score"}
            }
        }
    ]
    
    posture_stats = await db.devices.aggregate(pipeline).to_list(None)
    
    # Get active alerts count
    active_alerts = await db.threat_alerts.count_documents({"status": "active"})
    
    # Calculate overall posture
    total_devices = sum(p['count'] for p in posture_stats)
    secure_devices = next((p['count'] for p in posture_stats if p['_id'] == 'secure'), 0)
    
    overall_posture = "secure" if secure_devices > total_devices * 0.7 else "at_risk" if secure_devices > total_devices * 0.3 else "critical"
    
    return {
        "overall_posture": overall_posture,
        "total_devices": total_devices,
        "posture_breakdown": {p['_id']: p['count'] for p in posture_stats},
        "average_scores": {p['_id']: round(p['avg_score'], 2) for p in posture_stats if p['avg_score']},
        "active_alerts": active_alerts,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/factors")
async def get_scoring_factors():
    """
    Get list of factors used in threat scoring
    """
    return {
        "scoring_factors": [
            {
                "factor": "network_security",
                "weight": 0.25,
                "description": "Network connection security analysis",
                "considerations": ["VPN usage", "Public WiFi", "Encryption status", "Suspicious connections"]
            },
            {
                "factor": "app_security",
                "weight": 0.25,
                "description": "Installed applications security analysis",
                "considerations": ["App source (official store vs sideloaded)", "Dangerous permissions", "Known malware signatures"]
            },
            {
                "factor": "behavior_analysis",
                "weight": 0.20,
                "description": "Device behavior pattern analysis",
                "considerations": ["Unusual data usage", "Background activity", "Battery drain", "Crash frequency"]
            },
            {
                "factor": "ai_context",
                "weight": 0.30,
                "description": "AI-powered contextual threat analysis",
                "considerations": ["Historical patterns", "Known threat correlation", "Real-time threat intelligence"]
            }
        ],
        "threat_levels": [
            {"level": "low", "score_range": "0-24", "color": "green"},
            {"level": "medium", "score_range": "25-49", "color": "yellow"},
            {"level": "high", "score_range": "50-74", "color": "orange"},
            {"level": "critical", "score_range": "75-100", "color": "red"}
        ]
    }
