"""
GSM/Telecom Fraud Detection Module
Part of SecureSphere Platform

Provides:
- SIM swap attack detection and alerts
- OTP interception detection
- Caller ID spoofing detection
- GSM fraud dashboard
- Real-time fraud monitoring
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import random
import re

import dependencies

router = APIRouter(prefix="/securesphere/gsm-fraud", tags=["SecureSphere - GSM Fraud Detection"])


# Fraud Types and Patterns
FRAUD_TYPES = {
    "sim_swap": {
        "name": "SIM Swap Attack",
        "severity": "critical",
        "description": "Unauthorized transfer of phone number to a new SIM card",
        "indicators": ["sudden_signal_loss", "unexpected_carrier_change", "auth_failures", "location_anomaly"]
    },
    "otp_interception": {
        "name": "OTP Interception",
        "severity": "critical", 
        "description": "Interception of one-time passwords via SS7 or malware",
        "indicators": ["delayed_otp", "duplicate_otp_requests", "suspicious_ss7_activity", "imsi_catcher"]
    },
    "caller_id_spoofing": {
        "name": "Caller ID Spoofing",
        "severity": "high",
        "description": "Falsifying caller ID to impersonate trusted entities",
        "indicators": ["mismatched_ani_dnis", "impossible_origination", "known_spoof_pattern", "vishing_attempt"]
    },
    "wangiri": {
        "name": "Wangiri Fraud",
        "severity": "medium",
        "description": "One-ring scam to trick users into calling premium numbers",
        "indicators": ["single_ring", "international_premium_number", "high_call_back_rate"]
    },
    "irsf": {
        "name": "International Revenue Share Fraud",
        "severity": "high",
        "description": "Fraudulent calls to premium rate numbers for revenue sharing",
        "indicators": ["high_volume_international", "premium_destinations", "unusual_call_duration"]
    },
    "prs_fraud": {
        "name": "Premium Rate Service Fraud",
        "severity": "high",
        "description": "Unauthorized subscriptions to premium rate services",
        "indicators": ["unexpected_charges", "unknown_service_provider", "bulk_subscriptions"]
    }
}

# Known spoofed numbers database (mock)
KNOWN_SPOOF_PATTERNS = [
    r"^\+1800\d{7}$",  # Fake toll-free
    r"^\+91(100|101|112)$",  # Emergency number spoofing
    r"^\+1\d{3}555\d{4}$",  # Fictional numbers
]

# High-risk countries for GSM fraud
HIGH_RISK_DESTINATIONS = {
    "cuba": "+53",
    "somalia": "+252",
    "guinea": "+224",
    "sierra_leone": "+232",
    "latvia": "+371",
    "estonia": "+372"
}


class SIMSwapAlert(BaseModel):
    """SIM Swap Attack Alert"""
    subscriber_id: str
    phone_number: str
    old_imsi: Optional[str] = None
    new_imsi: Optional[str] = None
    old_imei: Optional[str] = None
    new_imei: Optional[str] = None
    carrier_change: bool = False
    location_before: Optional[str] = None
    location_after: Optional[str] = None
    timestamp: Optional[str] = None


class OTPEvent(BaseModel):
    """OTP Event for Interception Detection"""
    subscriber_id: str
    phone_number: str
    otp_type: str  # sms, voice, authenticator
    service_provider: str  # bank, social_media, email, etc.
    delivery_status: str  # sent, delivered, failed, delayed
    delivery_time_ms: int
    source_ip: Optional[str] = None
    device_fingerprint: Optional[str] = None
    timestamp: Optional[str] = None


class CallerIDCheck(BaseModel):
    """Caller ID Spoofing Check Request"""
    calling_number: str
    called_number: str
    ani: Optional[str] = None  # Automatic Number Identification
    originating_carrier: Optional[str] = None
    call_type: str = "voice"  # voice, sms, mms
    timestamp: Optional[str] = None


class FraudReport(BaseModel):
    """Manual Fraud Report"""
    subscriber_id: str
    phone_number: str
    fraud_type: str
    description: str
    evidence: Optional[Dict] = None
    reporter_contact: Optional[str] = None


class GSMActivityLog(BaseModel):
    """GSM Network Activity Log"""
    subscriber_id: str
    activity_type: str  # call, sms, data, location_update, auth
    details: Dict
    timestamp: Optional[str] = None


# ==================== SIM SWAP DETECTION ====================

@router.post("/sim-swap/detect")
async def detect_sim_swap(alert: SIMSwapAlert):
    """
    Detect and alert on potential SIM swap attacks
    """
    db = dependencies.get_db()
    alert_id = str(uuid4())
    
    risk_score = 0
    risk_factors = []
    
    # Check for IMSI change
    if alert.old_imsi and alert.new_imsi and alert.old_imsi != alert.new_imsi:
        risk_score += 40
        risk_factors.append({
            "factor": "imsi_change",
            "severity": "critical",
            "description": f"IMSI changed from {alert.old_imsi[:6]}*** to {alert.new_imsi[:6]}***"
        })
    
    # Check for IMEI change
    if alert.old_imei and alert.new_imei and alert.old_imei != alert.new_imei:
        risk_score += 30
        risk_factors.append({
            "factor": "imei_change",
            "severity": "high",
            "description": "Device IMEI changed - possible new device"
        })
    
    # Check for carrier change
    if alert.carrier_change:
        risk_score += 20
        risk_factors.append({
            "factor": "carrier_change",
            "severity": "high",
            "description": "Number ported to different carrier"
        })
    
    # Check for location anomaly
    if alert.location_before and alert.location_after:
        if alert.location_before != alert.location_after:
            risk_score += 10
            risk_factors.append({
                "factor": "location_anomaly",
                "severity": "medium",
                "description": f"Location changed from {alert.location_before} to {alert.location_after}"
            })
    
    # Determine threat level
    threat_level = "critical" if risk_score >= 70 else "high" if risk_score >= 40 else "medium" if risk_score >= 20 else "low"
    
    # Create alert record
    alert_record = {
        "id": alert_id,
        "type": "sim_swap",
        "subscriber_id": alert.subscriber_id,
        "phone_number": hashlib.sha256(alert.phone_number.encode()).hexdigest()[:16],
        "risk_score": risk_score,
        "threat_level": threat_level,
        "risk_factors": risk_factors,
        "status": "active" if risk_score >= 40 else "monitoring",
        "created_at": alert.timestamp or datetime.now(timezone.utc).isoformat(),
        "recommended_actions": []
    }
    
    # Add recommended actions based on risk
    if risk_score >= 70:
        alert_record["recommended_actions"] = [
            "Immediately freeze all financial accounts linked to this number",
            "Contact subscriber via alternative channel to verify identity",
            "Block all OTP-based authentications for 24 hours",
            "File regulatory report with TRAI/telecom authority",
            "Initiate SIM reversal procedure"
        ]
    elif risk_score >= 40:
        alert_record["recommended_actions"] = [
            "Send verification SMS to registered email",
            "Require additional authentication for sensitive operations",
            "Monitor account activity for 48 hours",
            "Alert subscriber via push notification"
        ]
    
    await db.gsm_fraud_alerts.insert_one(alert_record)
    
    return {
        "alert_id": alert_id,
        "threat_level": threat_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "is_sim_swap_detected": risk_score >= 40,
        "recommended_actions": alert_record["recommended_actions"],
        "status": alert_record["status"]
    }


@router.get("/sim-swap/alerts")
async def get_sim_swap_alerts(
    status: Optional[str] = None,
    threat_level: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    Get SIM swap attack alerts
    """
    db = dependencies.get_db()
    
    query = {"type": "sim_swap"}
    if status:
        query["status"] = status
    if threat_level:
        query["threat_level"] = threat_level
    
    alerts = await db.gsm_fraud_alerts.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "total": len(alerts),
        "alerts": alerts
    }


@router.post("/sim-swap/verify")
async def verify_sim_ownership(subscriber_id: str, phone_number: str, verification_code: str):
    """
    Verify SIM ownership after potential swap detection
    """
    # In production, this would trigger actual verification
    verification_id = str(uuid4())
    
    return {
        "verification_id": verification_id,
        "status": "pending",
        "verification_method": "callback",
        "expires_in": 300,  # 5 minutes
        "message": "Verification code sent to registered email. Please confirm within 5 minutes."
    }


# ==================== OTP INTERCEPTION DETECTION ====================

@router.post("/otp/monitor")
async def monitor_otp_event(event: OTPEvent):
    """
    Monitor OTP delivery for interception attempts
    """
    db = dependencies.get_db()
    event_id = str(uuid4())
    
    risk_indicators = []
    risk_score = 0
    
    # Check delivery time anomaly (normal: <5000ms)
    if event.delivery_time_ms > 30000:  # > 30 seconds
        risk_score += 30
        risk_indicators.append({
            "indicator": "delayed_delivery",
            "severity": "high",
            "description": f"OTP delivery took {event.delivery_time_ms}ms (expected <5000ms)"
        })
    elif event.delivery_time_ms > 10000:  # > 10 seconds
        risk_score += 15
        risk_indicators.append({
            "indicator": "slow_delivery",
            "severity": "medium",
            "description": f"OTP delivery slightly delayed: {event.delivery_time_ms}ms"
        })
    
    # Check for failed delivery
    if event.delivery_status == "failed":
        risk_score += 40
        risk_indicators.append({
            "indicator": "delivery_failed",
            "severity": "critical",
            "description": "OTP failed to deliver - possible interception or blocking"
        })
    
    # Check for suspicious source IP
    if event.source_ip:
        # Check if IP is from known VPN/proxy
        suspicious_prefixes = ["185.220.", "104.244.", "45.33."]
        if any(event.source_ip.startswith(prefix) for prefix in suspicious_prefixes):
            risk_score += 25
            risk_indicators.append({
                "indicator": "suspicious_ip",
                "severity": "high",
                "description": "Request originated from known VPN/proxy IP range"
            })
    
    # Check OTP request frequency (would need historical data)
    recent_requests = await db.otp_events.count_documents({
        "subscriber_id": event.subscriber_id,
        "created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()}
    })
    
    if recent_requests > 5:
        risk_score += 35
        risk_indicators.append({
            "indicator": "high_frequency",
            "severity": "critical",
            "description": f"{recent_requests + 1} OTP requests in last 10 minutes"
        })
    
    threat_level = "critical" if risk_score >= 60 else "high" if risk_score >= 40 else "medium" if risk_score >= 20 else "low"
    
    event_record = {
        "id": event_id,
        "type": "otp_event",
        "subscriber_id": event.subscriber_id,
        "phone_hash": hashlib.sha256(event.phone_number.encode()).hexdigest()[:16],
        "otp_type": event.otp_type,
        "service_provider": event.service_provider,
        "delivery_status": event.delivery_status,
        "delivery_time_ms": event.delivery_time_ms,
        "risk_score": risk_score,
        "threat_level": threat_level,
        "risk_indicators": risk_indicators,
        "created_at": event.timestamp or datetime.now(timezone.utc).isoformat()
    }
    
    await db.otp_events.insert_one(event_record)
    
    return {
        "event_id": event_id,
        "threat_level": threat_level,
        "risk_score": risk_score,
        "interception_suspected": risk_score >= 40,
        "risk_indicators": risk_indicators,
        "recommendation": "Use authenticator app instead of SMS OTP" if risk_score >= 40 else "OTP delivery normal"
    }


@router.get("/otp/alerts")
async def get_otp_interception_alerts(
    subscriber_id: Optional[str] = None,
    min_risk_score: int = Query(default=40, le=100),
    limit: int = Query(default=50, le=200)
):
    """
    Get OTP interception alerts
    """
    db = dependencies.get_db()
    
    query = {"type": "otp_event", "risk_score": {"$gte": min_risk_score}}
    if subscriber_id:
        query["subscriber_id"] = subscriber_id
    
    alerts = await db.otp_events.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "total": len(alerts),
        "min_risk_score": min_risk_score,
        "alerts": alerts
    }


@router.get("/otp/stats/{subscriber_id}")
async def get_otp_stats(subscriber_id: str, days: int = Query(default=30, le=90)):
    """
    Get OTP delivery statistics for a subscriber
    """
    db = dependencies.get_db()
    
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    events = await db.otp_events.find({
        "subscriber_id": subscriber_id,
        "created_at": {"$gte": since}
    }, {"_id": 0}).to_list(1000)
    
    if not events:
        return {
            "subscriber_id": subscriber_id,
            "period_days": days,
            "total_events": 0,
            "stats": {}
        }
    
    total = len(events)
    failed = sum(1 for e in events if e.get("delivery_status") == "failed")
    high_risk = sum(1 for e in events if e.get("risk_score", 0) >= 40)
    avg_delivery_time = sum(e.get("delivery_time_ms", 0) for e in events) / total
    
    return {
        "subscriber_id": subscriber_id,
        "period_days": days,
        "total_events": total,
        "stats": {
            "successful_deliveries": total - failed,
            "failed_deliveries": failed,
            "failure_rate": round((failed / total) * 100, 2),
            "high_risk_events": high_risk,
            "avg_delivery_time_ms": round(avg_delivery_time, 2)
        }
    }


# ==================== CALLER ID SPOOFING DETECTION ====================

@router.post("/caller-id/verify")
async def verify_caller_id(check: CallerIDCheck):
    """
    Verify caller ID authenticity and detect spoofing
    """
    db = dependencies.get_db()
    check_id = str(uuid4())
    
    spoof_indicators = []
    risk_score = 0
    
    # Check against known spoof patterns
    for pattern in KNOWN_SPOOF_PATTERNS:
        if re.match(pattern, check.calling_number):
            risk_score += 50
            spoof_indicators.append({
                "indicator": "known_spoof_pattern",
                "severity": "critical",
                "description": "Number matches known spoofed number pattern"
            })
            break
    
    # Check ANI mismatch
    if check.ani and check.ani != check.calling_number:
        risk_score += 40
        spoof_indicators.append({
            "indicator": "ani_mismatch",
            "severity": "critical",
            "description": f"ANI ({check.ani}) doesn't match displayed caller ID ({check.calling_number})"
        })
    
    # Check for emergency number spoofing
    emergency_patterns = [r"^\+91(100|101|112|108)$", r"^(100|101|112|911|999)$"]
    for pattern in emergency_patterns:
        if re.match(pattern, check.calling_number):
            risk_score += 60
            spoof_indicators.append({
                "indicator": "emergency_spoof",
                "severity": "critical",
                "description": "Attempt to spoof emergency services number"
            })
            break
    
    # Check for bank/official number spoofing
    official_prefixes = ["1800", "1860", "+911800"]
    for prefix in official_prefixes:
        if check.calling_number.startswith(prefix):
            risk_score += 25
            spoof_indicators.append({
                "indicator": "official_number_pattern",
                "severity": "high",
                "description": "Number resembles official/toll-free pattern - verify authenticity"
            })
            break
    
    # Geographic impossibility check
    if check.originating_carrier:
        # Simplified check - in production would use carrier routing tables
        if "international" in check.originating_carrier.lower() and check.calling_number.startswith("+91"):
            risk_score += 20
            spoof_indicators.append({
                "indicator": "geographic_anomaly",
                "severity": "medium",
                "description": "Call appears to originate internationally but shows local number"
            })
    
    is_spoofed = risk_score >= 40
    threat_level = "critical" if risk_score >= 70 else "high" if risk_score >= 40 else "medium" if risk_score >= 20 else "low"
    
    check_record = {
        "id": check_id,
        "type": "caller_id_check",
        "calling_number_hash": hashlib.sha256(check.calling_number.encode()).hexdigest()[:16],
        "called_number_hash": hashlib.sha256(check.called_number.encode()).hexdigest()[:16],
        "call_type": check.call_type,
        "risk_score": risk_score,
        "threat_level": threat_level,
        "is_spoofed": is_spoofed,
        "spoof_indicators": spoof_indicators,
        "created_at": check.timestamp or datetime.now(timezone.utc).isoformat()
    }
    
    await db.caller_id_checks.insert_one(check_record)
    
    return {
        "check_id": check_id,
        "is_spoofed": is_spoofed,
        "confidence": min(100, risk_score + 30) if is_spoofed else max(0, 100 - risk_score),
        "threat_level": threat_level,
        "risk_score": risk_score,
        "spoof_indicators": spoof_indicators,
        "recommendation": "Do not trust this caller - likely spoofed" if is_spoofed else "Caller ID appears legitimate"
    }


@router.get("/caller-id/blocked-numbers")
async def get_blocked_numbers(limit: int = Query(default=100, le=500)):
    """
    Get list of known spoofed/blocked numbers
    """
    db = dependencies.get_db()
    
    # Get numbers with high spoof scores
    blocked = await db.caller_id_checks.find(
        {"is_spoofed": True, "risk_score": {"$gte": 70}},
        {"_id": 0, "calling_number_hash": 1, "risk_score": 1, "threat_level": 1}
    ).sort("risk_score", -1).limit(limit).to_list(limit)
    
    return {
        "total": len(blocked),
        "blocked_numbers": blocked,
        "patterns": KNOWN_SPOOF_PATTERNS
    }


@router.post("/caller-id/report")
async def report_spoofed_number(
    calling_number: str,
    description: str,
    caller_claimed_identity: Optional[str] = None
):
    """
    Report a spoofed caller ID number
    """
    db = dependencies.get_db()
    
    report_id = str(uuid4())
    report = {
        "id": report_id,
        "type": "spoof_report",
        "calling_number_hash": hashlib.sha256(calling_number.encode()).hexdigest()[:16],
        "description": description,
        "caller_claimed_identity": caller_claimed_identity,
        "status": "under_review",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.fraud_reports.insert_one(report)
    
    return {
        "report_id": report_id,
        "status": "submitted",
        "message": "Report submitted for review. Thank you for helping protect the community."
    }


# ==================== GSM FRAUD DASHBOARD ====================

@router.get("/dashboard/overview")
async def get_gsm_fraud_dashboard():
    """
    Get comprehensive GSM fraud dashboard data
    """
    db = dependencies.get_db()
    
    # SIM swap alerts
    sim_swap_total = await db.gsm_fraud_alerts.count_documents({"type": "sim_swap"})
    sim_swap_critical = await db.gsm_fraud_alerts.count_documents({"type": "sim_swap", "threat_level": "critical"})
    sim_swap_active = await db.gsm_fraud_alerts.count_documents({"type": "sim_swap", "status": "active"})
    
    # OTP interception
    otp_total = await db.otp_events.count_documents({})
    otp_high_risk = await db.otp_events.count_documents({"risk_score": {"$gte": 40}})
    
    # Caller ID spoofing
    spoof_total = await db.caller_id_checks.count_documents({})
    spoof_detected = await db.caller_id_checks.count_documents({"is_spoofed": True})
    
    # Fraud reports
    reports_total = await db.fraud_reports.count_documents({})
    reports_pending = await db.fraud_reports.count_documents({"status": "under_review"})
    
    # Recent alerts (last 24 hours)
    since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_sim_swap = await db.gsm_fraud_alerts.count_documents({
        "type": "sim_swap",
        "created_at": {"$gte": since_24h}
    })
    recent_otp_alerts = await db.otp_events.count_documents({
        "risk_score": {"$gte": 40},
        "created_at": {"$gte": since_24h}
    })
    recent_spoof = await db.caller_id_checks.count_documents({
        "is_spoofed": True,
        "created_at": {"$gte": since_24h}
    })
    
    return {
        "summary": {
            "total_fraud_events": sim_swap_total + otp_high_risk + spoof_detected,
            "active_alerts": sim_swap_active,
            "pending_reports": reports_pending
        },
        "sim_swap": {
            "total_alerts": sim_swap_total,
            "critical_alerts": sim_swap_critical,
            "active_investigations": sim_swap_active,
            "last_24h": recent_sim_swap
        },
        "otp_interception": {
            "total_events": otp_total,
            "high_risk_events": otp_high_risk,
            "last_24h": recent_otp_alerts
        },
        "caller_id_spoofing": {
            "total_checks": spoof_total,
            "spoofed_detected": spoof_detected,
            "detection_rate": round((spoof_detected / max(1, spoof_total)) * 100, 2),
            "last_24h": recent_spoof
        },
        "fraud_reports": {
            "total": reports_total,
            "pending_review": reports_pending
        },
        "fraud_types": FRAUD_TYPES,
        "high_risk_destinations": HIGH_RISK_DESTINATIONS,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/dashboard/trends")
async def get_fraud_trends(days: int = Query(default=30, le=90)):
    """
    Get fraud trend analysis
    """
    db = dependencies.get_db()
    
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Aggregate fraud events by day
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {
            "$group": {
                "_id": {"$substr": ["$created_at", 0, 10]},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    sim_swap_trend = await db.gsm_fraud_alerts.aggregate(pipeline).to_list(None)
    otp_trend = await db.otp_events.aggregate([
        {"$match": {"created_at": {"$gte": since}, "risk_score": {"$gte": 40}}},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    return {
        "period_days": days,
        "sim_swap_trend": [{"date": t["_id"], "count": t["count"]} for t in sim_swap_trend],
        "otp_interception_trend": [{"date": t["_id"], "count": t["count"]} for t in otp_trend],
        "analysis": {
            "sim_swap_avg_per_day": round(sum(t["count"] for t in sim_swap_trend) / max(1, days), 2),
            "otp_alerts_avg_per_day": round(sum(t["count"] for t in otp_trend) / max(1, days), 2)
        }
    }


@router.get("/fraud-types")
async def get_fraud_types():
    """
    Get all GSM fraud types and their indicators
    """
    return {
        "fraud_types": [
            {
                "id": fid,
                **ftype
            }
            for fid, ftype in FRAUD_TYPES.items()
        ],
        "total": len(FRAUD_TYPES)
    }


@router.post("/activity/log")
async def log_gsm_activity(activity: GSMActivityLog):
    """
    Log GSM network activity for fraud analysis
    """
    db = dependencies.get_db()
    
    log_id = str(uuid4())
    log_record = {
        "id": log_id,
        "subscriber_id": activity.subscriber_id,
        "activity_type": activity.activity_type,
        "details": activity.details,
        "created_at": activity.timestamp or datetime.now(timezone.utc).isoformat()
    }
    
    await db.gsm_activity_logs.insert_one(log_record)
    
    return {
        "log_id": log_id,
        "status": "logged",
        "activity_type": activity.activity_type
    }


@router.post("/report")
async def submit_fraud_report(report: FraudReport):
    """
    Submit a fraud report for investigation
    """
    db = dependencies.get_db()
    
    if report.fraud_type not in FRAUD_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid fraud type. Valid types: {list(FRAUD_TYPES.keys())}")
    
    report_id = str(uuid4())
    report_record = {
        "id": report_id,
        "subscriber_id": report.subscriber_id,
        "phone_hash": hashlib.sha256(report.phone_number.encode()).hexdigest()[:16],
        "fraud_type": report.fraud_type,
        "description": report.description,
        "evidence": report.evidence,
        "reporter_contact": report.reporter_contact,
        "status": "under_review",
        "priority": FRAUD_TYPES[report.fraud_type]["severity"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.fraud_reports.insert_one(report_record)
    
    return {
        "report_id": report_id,
        "status": "submitted",
        "priority": report_record["priority"],
        "estimated_response_time": "24-48 hours" if report_record["priority"] == "critical" else "3-5 business days"
    }


@router.get("/reports")
async def get_fraud_reports(
    status: Optional[str] = None,
    fraud_type: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    Get fraud reports
    """
    db = dependencies.get_db()
    
    query = {}
    if status:
        query["status"] = status
    if fraud_type:
        query["fraud_type"] = fraud_type
    
    reports = await db.fraud_reports.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "total": len(reports),
        "reports": reports
    }
