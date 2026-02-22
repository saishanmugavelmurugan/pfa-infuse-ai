"""
IoT Security Module
Part of SecureSphere Platform

Provides:
- IoT endpoint monitoring
- Network traffic analysis
- Anomaly detection
- Firmware vulnerability scanning
- Access control monitoring
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import random

import dependencies

router = APIRouter(prefix="/securesphere/iot-security", tags=["SecureSphere - IoT Security"])


# IoT Device Categories
IOT_CATEGORIES = {
    "smart_home": ["thermostat", "camera", "doorbell", "smart_lock", "lighting", "speaker"],
    "industrial": ["plc", "scada", "sensor", "actuator", "gateway", "hmi"],
    "healthcare": ["monitor", "pump", "imaging", "wearable", "implant"],
    "automotive": ["telematics", "infotainment", "adas", "charging_station"],
    "infrastructure": ["smart_meter", "traffic_light", "water_sensor", "grid_monitor"]
}

# Known Vulnerabilities Database (Mock)
KNOWN_VULNERABILITIES = {
    "CVE-2024-1234": {
        "name": "Default Credentials Vulnerability",
        "severity": "critical",
        "affected_firmware": ["1.0.0", "1.0.1", "1.1.0"],
        "description": "Device ships with default credentials that are not changed"
    },
    "CVE-2024-2345": {
        "name": "Unencrypted Communication",
        "severity": "high",
        "affected_firmware": ["1.0.0", "1.0.1"],
        "description": "Device communicates over unencrypted channels"
    },
    "CVE-2024-3456": {
        "name": "Buffer Overflow in Firmware",
        "severity": "critical",
        "affected_firmware": ["1.2.0", "1.2.1"],
        "description": "Remote code execution via buffer overflow"
    },
    "CVE-2024-4567": {
        "name": "Weak Authentication Protocol",
        "severity": "medium",
        "affected_firmware": ["1.0.0", "1.1.0", "1.2.0"],
        "description": "Authentication can be bypassed with replay attacks"
    },
    "CVE-2024-5678": {
        "name": "Insecure OTA Updates",
        "severity": "high",
        "affected_firmware": ["1.0.0", "1.1.0"],
        "description": "OTA updates are not cryptographically signed"
    }
}


class IoTEndpointRegistration(BaseModel):
    """IoT Endpoint Registration"""
    device_name: str
    device_type: str
    category: str
    manufacturer: str
    model: str
    firmware_version: str
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    location: Optional[str] = None
    owner_id: str
    protocols: List[str] = ["mqtt", "http"]
    capabilities: List[str] = []


class NetworkTrafficData(BaseModel):
    """Network Traffic Analysis Data"""
    device_id: str
    traffic_samples: List[Dict]  # [{timestamp, bytes_in, bytes_out, protocol, destination}]
    duration_minutes: int = 60


class FirmwareScanRequest(BaseModel):
    """Firmware Vulnerability Scan Request"""
    device_id: str
    firmware_version: str
    firmware_hash: Optional[str] = None
    manufacturer: Optional[str] = None


class AccessControlRule(BaseModel):
    """Access Control Rule for IoT Device"""
    device_id: str
    rule_name: str
    rule_type: str  # allow, deny, rate_limit
    source: str  # ip, subnet, any
    destination: str
    protocol: str
    port: Optional[int] = None
    action: str
    priority: int = 100


class AnomalyReport(BaseModel):
    """Report an Anomaly"""
    device_id: str
    anomaly_type: str
    severity: str
    details: Dict
    timestamp: Optional[str] = None


# ==================== ENDPOINT MONITORING ====================

@router.post("/endpoints/register")
async def register_iot_endpoint(endpoint: IoTEndpointRegistration):
    """
    Register an IoT endpoint for comprehensive monitoring
    """
    if endpoint.category not in IOT_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid: {list(IOT_CATEGORIES.keys())}")
    
    db = dependencies.get_db()
    
    endpoint_id = str(uuid4())
    endpoint_record = {
        "id": endpoint_id,
        "device_name": endpoint.device_name,
        "device_type": endpoint.device_type,
        "category": endpoint.category,
        "manufacturer": endpoint.manufacturer,
        "model": endpoint.model,
        "firmware_version": endpoint.firmware_version,
        "ip_address": endpoint.ip_address,
        "mac_address": endpoint.mac_address,
        "mac_hash": hashlib.sha256(endpoint.mac_address.encode()).hexdigest()[:16] if endpoint.mac_address else None,
        "location": endpoint.location,
        "owner_id": endpoint.owner_id,
        "protocols": endpoint.protocols,
        "capabilities": endpoint.capabilities,
        "status": "active",
        "health_status": "healthy",
        "security_score": 100,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "monitoring_enabled": True,
        "anomaly_count": 0,
        "vulnerabilities_found": 0
    }
    
    await db.iot_endpoints.insert_one(endpoint_record)
    
    return {
        "endpoint_id": endpoint_id,
        "status": "registered",
        "monitoring_enabled": True,
        "features_enabled": [
            "endpoint_monitoring",
            "traffic_analysis",
            "anomaly_detection",
            "firmware_scanning",
            "access_control"
        ]
    }


@router.get("/endpoints/{endpoint_id}")
async def get_endpoint_details(endpoint_id: str):
    """
    Get detailed information about an IoT endpoint
    """
    db = dependencies.get_db()
    
    endpoint = await db.iot_endpoints.find_one(
        {"id": endpoint_id},
        {"_id": 0}
    )
    
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return endpoint


@router.get("/endpoints")
async def list_endpoints(
    owner_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    List all registered IoT endpoints
    """
    db = dependencies.get_db()
    
    query = {}
    if owner_id:
        query["owner_id"] = owner_id
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    
    endpoints = await db.iot_endpoints.find(
        query,
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    return {
        "total": len(endpoints),
        "endpoints": endpoints
    }


@router.post("/endpoints/{endpoint_id}/heartbeat")
async def endpoint_heartbeat(endpoint_id: str, metrics: Optional[Dict] = None):
    """
    Record endpoint heartbeat and health metrics
    """
    db = dependencies.get_db()
    
    update_data = {
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "health_status": "healthy"
    }
    
    if metrics:
        update_data["latest_metrics"] = metrics
    
    result = await db.iot_endpoints.update_one(
        {"id": endpoint_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {"status": "heartbeat_recorded", "timestamp": update_data["last_seen"]}


@router.get("/endpoints/{endpoint_id}/health")
async def get_endpoint_health(endpoint_id: str):
    """
    Get comprehensive health status for an endpoint
    """
    db = dependencies.get_db()
    
    endpoint = await db.iot_endpoints.find_one({"id": endpoint_id}, {"_id": 0})
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Calculate health score based on various factors
    health_factors = {
        "connectivity": 100,
        "security_posture": endpoint.get("security_score", 100),
        "firmware_status": 100 if endpoint.get("vulnerabilities_found", 0) == 0 else 50,
        "anomaly_status": 100 if endpoint.get("anomaly_count", 0) == 0 else 70,
        "last_seen_recency": 100  # Would calculate based on last_seen
    }
    
    overall_health = sum(health_factors.values()) // len(health_factors)
    
    return {
        "endpoint_id": endpoint_id,
        "overall_health": overall_health,
        "health_status": "healthy" if overall_health >= 80 else "degraded" if overall_health >= 50 else "critical",
        "factors": health_factors,
        "last_seen": endpoint.get("last_seen"),
        "uptime_percentage": 99.9,  # Would calculate from heartbeat history
        "recommendations": [] if overall_health >= 80 else [
            "Update firmware to latest version",
            "Review and resolve detected anomalies",
            "Strengthen access controls"
        ]
    }


# ==================== NETWORK TRAFFIC ANALYSIS ====================

@router.post("/traffic/analyze")
async def analyze_network_traffic(data: NetworkTrafficData):
    """
    Analyze network traffic patterns for an IoT device
    """
    db = dependencies.get_db()
    analysis_id = str(uuid4())
    
    # Simulated traffic analysis
    total_bytes_in = sum(s.get('bytes_in', 0) for s in data.traffic_samples)
    total_bytes_out = sum(s.get('bytes_out', 0) for s in data.traffic_samples)
    unique_destinations = list(set(s.get('destination', '') for s in data.traffic_samples if s.get('destination')))
    protocols_used = list(set(s.get('protocol', '') for s in data.traffic_samples if s.get('protocol')))
    
    # Detect suspicious patterns
    suspicious_patterns = []
    
    # Check for unusual data exfiltration
    if total_bytes_out > total_bytes_in * 10:
        suspicious_patterns.append({
            "type": "data_exfiltration",
            "severity": "high",
            "description": "Unusually high outbound traffic detected"
        })
    
    # Check for connections to unusual ports
    unusual_ports = [s.get('port') for s in data.traffic_samples if s.get('port', 0) > 10000]
    if unusual_ports:
        suspicious_patterns.append({
            "type": "unusual_ports",
            "severity": "medium",
            "description": f"Connections to unusual ports detected: {unusual_ports[:5]}"
        })
    
    # Check for encrypted vs unencrypted traffic
    unencrypted = [s for s in data.traffic_samples if s.get('protocol') in ['http', 'telnet', 'ftp']]
    if len(unencrypted) > len(data.traffic_samples) * 0.5:
        suspicious_patterns.append({
            "type": "unencrypted_communication",
            "severity": "high",
            "description": "More than 50% of traffic is unencrypted"
        })
    
    analysis_result = {
        "id": analysis_id,
        "device_id": data.device_id,
        "duration_minutes": data.duration_minutes,
        "samples_analyzed": len(data.traffic_samples),
        "summary": {
            "total_bytes_in": total_bytes_in,
            "total_bytes_out": total_bytes_out,
            "unique_destinations": len(unique_destinations),
            "protocols_used": protocols_used,
            "bandwidth_utilization": round((total_bytes_in + total_bytes_out) / (data.duration_minutes * 60 * 1024), 2)  # KB/s
        },
        "suspicious_patterns": suspicious_patterns,
        "threat_level": "high" if len(suspicious_patterns) > 2 else "medium" if suspicious_patterns else "low",
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Remove _id before inserting to let MongoDB generate one
    analysis_to_insert = {k: v for k, v in analysis_result.items() if k != "_id"}
    await db.traffic_analyses.insert_one(analysis_to_insert)
    
    return analysis_result


@router.get("/traffic/stats/{device_id}")
async def get_traffic_stats(device_id: str, hours: int = Query(default=24, le=168)):
    """
    Get traffic statistics for a device over a time period
    """
    # Simulated stats - in production, would aggregate from real traffic data
    return {
        "device_id": device_id,
        "period_hours": hours,
        "statistics": {
            "total_bytes_transferred": random.randint(1000000, 100000000),
            "average_bandwidth_kbps": round(random.uniform(10, 500), 2),
            "peak_bandwidth_kbps": round(random.uniform(500, 2000), 2),
            "connection_count": random.randint(100, 10000),
            "unique_destinations": random.randint(5, 50),
            "protocol_breakdown": {
                "mqtt": round(random.uniform(30, 50), 1),
                "https": round(random.uniform(20, 40), 1),
                "http": round(random.uniform(5, 15), 1),
                "other": round(random.uniform(5, 20), 1)
            }
        },
        "trends": {
            "traffic_trend": random.choice(["increasing", "stable", "decreasing"]),
            "anomaly_trend": random.choice(["improving", "stable", "worsening"])
        }
    }


# ==================== ANOMALY DETECTION ====================

@router.post("/anomalies/detect")
async def detect_anomalies(device_id: str, data_points: List[Dict]):
    """
    Run anomaly detection on device behavior data
    """
    db = dependencies.get_db()
    detection_id = str(uuid4())
    
    anomalies = []
    
    for point in data_points:
        # Simulated anomaly detection logic
        metric_type = point.get('type', 'unknown')
        value = point.get('value', 0)
        threshold = point.get('threshold', 100)
        
        if value > threshold * 1.5:
            anomalies.append({
                "id": str(uuid4()),
                "type": f"threshold_breach_{metric_type}",
                "severity": "high" if value > threshold * 2 else "medium",
                "metric": metric_type,
                "value": value,
                "threshold": threshold,
                "deviation_percent": round((value - threshold) / threshold * 100, 2),
                "detected_at": datetime.now(timezone.utc).isoformat()
            })
    
    # Additional behavioral anomalies
    if len(data_points) > 0:
        # Check for sudden spikes
        values = [p.get('value', 0) for p in data_points]
        avg = sum(values) / len(values)
        spikes = [v for v in values if v > avg * 3]
        
        if spikes:
            anomalies.append({
                "id": str(uuid4()),
                "type": "behavioral_spike",
                "severity": "medium",
                "description": f"Detected {len(spikes)} sudden spikes in metrics",
                "detected_at": datetime.now(timezone.utc).isoformat()
            })
    
    result = {
        "detection_id": detection_id,
        "device_id": device_id,
        "data_points_analyzed": len(data_points),
        "anomalies_found": len(anomalies),
        "anomalies": anomalies,
        "risk_level": "critical" if len(anomalies) > 5 else "high" if len(anomalies) > 2 else "medium" if anomalies else "low",
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Store anomalies
    if anomalies:
        await db.iot_anomalies.insert_many([{**a, "device_id": device_id} for a in anomalies])
        
        # Update device anomaly count
        await db.iot_endpoints.update_one(
            {"id": device_id},
            {"$inc": {"anomaly_count": len(anomalies)}}
        )
    
    return result


@router.post("/anomalies/report")
async def report_anomaly(report: AnomalyReport):
    """
    Manually report an observed anomaly
    """
    db = dependencies.get_db()
    
    anomaly_id = str(uuid4())
    anomaly_record = {
        "id": anomaly_id,
        "device_id": report.device_id,
        "anomaly_type": report.anomaly_type,
        "severity": report.severity,
        "details": report.details,
        "source": "manual_report",
        "status": "open",
        "reported_at": report.timestamp or datetime.now(timezone.utc).isoformat()
    }
    
    await db.iot_anomalies.insert_one(anomaly_record)
    
    return {
        "anomaly_id": anomaly_id,
        "status": "reported",
        "severity": report.severity
    }


@router.get("/anomalies/{device_id}")
async def get_device_anomalies(
    device_id: str,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    Get anomalies for a specific device
    """
    db = dependencies.get_db()
    
    query = {"device_id": device_id}
    if severity:
        query["severity"] = severity
    if status:
        query["status"] = status
    
    anomalies = await db.iot_anomalies.find(
        query,
        {"_id": 0}
    ).sort("reported_at", -1).limit(limit).to_list(limit)
    
    return {
        "device_id": device_id,
        "total": len(anomalies),
        "anomalies": anomalies
    }


# ==================== FIRMWARE VULNERABILITY SCANNING ====================

@router.post("/firmware/scan")
async def scan_firmware(request: FirmwareScanRequest):
    """
    Scan firmware for known vulnerabilities
    """
    db = dependencies.get_db()
    scan_id = str(uuid4())
    
    vulnerabilities = []
    
    # Check against known vulnerabilities
    for cve_id, vuln in KNOWN_VULNERABILITIES.items():
        if request.firmware_version in vuln["affected_firmware"]:
            vulnerabilities.append({
                "cve_id": cve_id,
                "name": vuln["name"],
                "severity": vuln["severity"],
                "description": vuln["description"],
                "remediation": f"Update firmware to version newer than {max(vuln['affected_firmware'])}"
            })
    
    # Additional security checks
    security_issues = []
    
    # Check firmware hash if provided
    if request.firmware_hash:
        # Simulated hash verification
        if len(request.firmware_hash) != 64:
            security_issues.append({
                "type": "invalid_hash",
                "severity": "medium",
                "description": "Firmware hash is not a valid SHA-256 hash"
            })
    
    # Check for outdated firmware patterns
    version_parts = request.firmware_version.split(".")
    if len(version_parts) >= 1 and version_parts[0] == "1":
        security_issues.append({
            "type": "outdated_major_version",
            "severity": "medium",
            "description": "Major version 1.x firmware may lack security updates"
        })
    
    scan_result = {
        "id": scan_id,
        "device_id": request.device_id,
        "firmware_version": request.firmware_version,
        "manufacturer": request.manufacturer,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "vulnerabilities_found": len(vulnerabilities),
        "vulnerabilities": vulnerabilities,
        "security_issues": security_issues,
        "overall_risk": "critical" if any(v["severity"] == "critical" for v in vulnerabilities) else "high" if vulnerabilities else "low",
        "recommendations": [
            "Update to the latest firmware version",
            "Enable automatic security updates",
            "Implement network segmentation for IoT devices"
        ] if vulnerabilities else ["Firmware appears up-to-date"]
    }
    
    # Remove _id before inserting to let MongoDB generate one
    scan_to_insert = {k: v for k, v in scan_result.items() if k != "_id"}
    await db.firmware_scans.insert_one(scan_to_insert)
    
    # Update device vulnerability count
    if vulnerabilities:
        await db.iot_endpoints.update_one(
            {"id": request.device_id},
            {
                "$set": {"vulnerabilities_found": len(vulnerabilities)},
                "$inc": {"security_score": -10 * len(vulnerabilities)}
            }
        )
    
    return scan_result


@router.get("/firmware/vulnerabilities")
async def get_known_vulnerabilities(severity: Optional[str] = None):
    """
    Get list of known IoT firmware vulnerabilities
    """
    vulnerabilities = []
    
    for cve_id, vuln in KNOWN_VULNERABILITIES.items():
        if severity and vuln["severity"] != severity:
            continue
        vulnerabilities.append({
            "cve_id": cve_id,
            **vuln
        })
    
    return {
        "total": len(vulnerabilities),
        "vulnerabilities": vulnerabilities
    }


@router.get("/firmware/scan-history/{device_id}")
async def get_firmware_scan_history(device_id: str, limit: int = Query(default=10, le=50)):
    """
    Get firmware scan history for a device
    """
    db = dependencies.get_db()
    
    scans = await db.firmware_scans.find(
        {"device_id": device_id},
        {"_id": 0}
    ).sort("scan_timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "device_id": device_id,
        "total_scans": len(scans),
        "scans": scans
    }


# ==================== ACCESS CONTROL MONITORING ====================

@router.post("/access-control/rules")
async def create_access_control_rule(rule: AccessControlRule):
    """
    Create an access control rule for an IoT device
    """
    db = dependencies.get_db()
    
    rule_id = str(uuid4())
    rule_record = {
        "id": rule_id,
        "device_id": rule.device_id,
        "rule_name": rule.rule_name,
        "rule_type": rule.rule_type,
        "source": rule.source,
        "destination": rule.destination,
        "protocol": rule.protocol,
        "port": rule.port,
        "action": rule.action,
        "priority": rule.priority,
        "status": "active",
        "hit_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.access_control_rules.insert_one(rule_record)
    
    return {
        "rule_id": rule_id,
        "status": "created",
        "rule_name": rule.rule_name
    }


@router.get("/access-control/rules/{device_id}")
async def get_access_control_rules(device_id: str):
    """
    Get access control rules for a device
    """
    db = dependencies.get_db()
    
    rules = await db.access_control_rules.find(
        {"device_id": device_id, "status": "active"},
        {"_id": 0}
    ).sort("priority", 1).to_list(100)
    
    return {
        "device_id": device_id,
        "total_rules": len(rules),
        "rules": rules
    }


@router.delete("/access-control/rules/{rule_id}")
async def delete_access_control_rule(rule_id: str):
    """
    Delete an access control rule
    """
    db = dependencies.get_db()
    
    result = await db.access_control_rules.update_one(
        {"id": rule_id},
        {"$set": {"status": "deleted"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"status": "deleted", "rule_id": rule_id}


@router.post("/access-control/audit")
async def audit_access_attempt(
    device_id: str,
    source_ip: str,
    destination: str,
    protocol: str,
    port: Optional[int] = None
):
    """
    Audit an access attempt against device rules
    """
    db = dependencies.get_db()
    
    # Get device rules
    rules = await db.access_control_rules.find(
        {"device_id": device_id, "status": "active"},
        {"_id": 0}
    ).sort("priority", 1).to_list(100)
    
    matched_rule = None
    decision = "allow"  # Default allow if no rules match
    
    for rule in rules:
        # Simplified rule matching
        if rule["source"] == "any" or rule["source"] == source_ip:
            if rule["destination"] == "any" or rule["destination"] == destination:
                if rule["protocol"] == "any" or rule["protocol"] == protocol:
                    matched_rule = rule
                    decision = rule["action"]
                    
                    # Update hit count
                    await db.access_control_rules.update_one(
                        {"id": rule["id"]},
                        {"$inc": {"hit_count": 1}}
                    )
                    break
    
    # Log the access attempt
    audit_record = {
        "id": str(uuid4()),
        "device_id": device_id,
        "source_ip": source_ip,
        "destination": destination,
        "protocol": protocol,
        "port": port,
        "decision": decision,
        "matched_rule": matched_rule["id"] if matched_rule else None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.access_audit_logs.insert_one(audit_record)
    
    return {
        "decision": decision,
        "matched_rule": matched_rule["rule_name"] if matched_rule else "default_policy",
        "audit_id": audit_record["id"]
    }


@router.get("/access-control/audit-logs/{device_id}")
async def get_audit_logs(
    device_id: str,
    decision: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """
    Get access audit logs for a device
    """
    db = dependencies.get_db()
    
    query = {"device_id": device_id}
    if decision:
        query["decision"] = decision
    
    logs = await db.access_audit_logs.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "device_id": device_id,
        "total_logs": len(logs),
        "logs": logs
    }


# ==================== DASHBOARD & STATISTICS ====================

@router.get("/dashboard/overview")
async def get_iot_security_overview():
    """
    Get comprehensive IoT security overview
    """
    db = dependencies.get_db()
    
    total_endpoints = await db.iot_endpoints.count_documents({"status": "active"})
    healthy_endpoints = await db.iot_endpoints.count_documents({"status": "active", "health_status": "healthy"})
    total_anomalies = await db.iot_anomalies.count_documents({"status": "open"})
    
    # Category breakdown
    category_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    categories = await db.iot_endpoints.aggregate(category_pipeline).to_list(None)
    
    # Recent scans
    recent_scans = await db.firmware_scans.count_documents({})
    vulnerable_devices = await db.iot_endpoints.count_documents({"vulnerabilities_found": {"$gt": 0}})
    
    return {
        "summary": {
            "total_endpoints": total_endpoints,
            "healthy_endpoints": healthy_endpoints,
            "health_percentage": round((healthy_endpoints / max(1, total_endpoints)) * 100, 1),
            "active_anomalies": total_anomalies,
            "vulnerable_devices": vulnerable_devices,
            "firmware_scans": recent_scans
        },
        "by_category": {c["_id"]: c["count"] for c in categories if c["_id"]},
        "risk_distribution": {
            "low": max(0, total_endpoints - vulnerable_devices - (total_anomalies // 2)),
            "medium": total_anomalies // 2,
            "high": vulnerable_devices
        },
        "recent_alerts": [],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/categories")
async def get_iot_categories():
    """
    Get all IoT device categories and types
    """
    return {
        "categories": IOT_CATEGORIES,
        "total_categories": len(IOT_CATEGORIES),
        "total_device_types": sum(len(types) for types in IOT_CATEGORIES.values())
    }
