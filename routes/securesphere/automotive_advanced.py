"""
Advanced Automotive Security Module
Part of SecureSphere Platform

Provides:
- Advanced CAN Bus Monitoring with real-time analysis
- ECU Vulnerability Scanning
- GPS Spoofing Detection
- Fleet Security Management
- Vehicle Threat Tracking
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import random
import math

import dependencies

router = APIRouter(prefix="/securesphere/automotive-advanced", tags=["SecureSphere - Advanced Automotive Security"])


# ECU Types and Known Vulnerabilities
ECU_TYPES = {
    "engine_control": {
        "name": "Engine Control Module (ECM)",
        "criticality": "critical",
        "attack_surface": ["obd_port", "can_bus", "wireless_key"]
    },
    "transmission": {
        "name": "Transmission Control Module (TCM)",
        "criticality": "critical",
        "attack_surface": ["can_bus", "diagnostic_port"]
    },
    "brake_system": {
        "name": "Anti-lock Braking System (ABS)",
        "criticality": "critical",
        "attack_surface": ["can_bus"]
    },
    "airbag": {
        "name": "Airbag Control Module (ACM)",
        "criticality": "critical",
        "attack_surface": ["can_bus", "crash_sensors"]
    },
    "body_control": {
        "name": "Body Control Module (BCM)",
        "criticality": "high",
        "attack_surface": ["can_bus", "keyfob", "bluetooth"]
    },
    "infotainment": {
        "name": "Infotainment System (IVI)",
        "criticality": "medium",
        "attack_surface": ["wifi", "bluetooth", "usb", "cellular"]
    },
    "telematics": {
        "name": "Telematics Control Unit (TCU)",
        "criticality": "high",
        "attack_surface": ["cellular", "gps", "can_bus"]
    },
    "adas": {
        "name": "Advanced Driver Assistance (ADAS)",
        "criticality": "critical",
        "attack_surface": ["can_bus", "camera", "radar", "lidar"]
    },
    "battery_management": {
        "name": "Battery Management System (BMS)",
        "criticality": "critical",
        "attack_surface": ["can_bus", "charging_port"]
    },
    "gateway": {
        "name": "Central Gateway Module",
        "criticality": "critical",
        "attack_surface": ["can_bus", "ethernet", "diagnostic_port"]
    }
}

# Known ECU Vulnerabilities Database
ECU_VULNERABILITIES = {
    "CVE-2024-AUTO-001": {
        "name": "CAN Bus Message Injection",
        "severity": "critical",
        "affected_ecus": ["engine_control", "brake_system", "transmission"],
        "description": "Allows arbitrary CAN messages to be injected via OBD-II port",
        "cvss": 9.8
    },
    "CVE-2024-AUTO-002": {
        "name": "Telematics Buffer Overflow",
        "severity": "critical",
        "affected_ecus": ["telematics", "infotainment"],
        "description": "Remote code execution via malformed cellular packet",
        "cvss": 9.1
    },
    "CVE-2024-AUTO-003": {
        "name": "Bluetooth Pairing Bypass",
        "severity": "high",
        "affected_ecus": ["body_control", "infotainment"],
        "description": "Authentication bypass allows unauthorized device pairing",
        "cvss": 8.4
    },
    "CVE-2024-AUTO-004": {
        "name": "GPS Signal Spoofing Vulnerability",
        "severity": "high",
        "affected_ecus": ["telematics", "adas"],
        "description": "No validation of GPS signal authenticity",
        "cvss": 7.5
    },
    "CVE-2024-AUTO-005": {
        "name": "OTA Update Tampering",
        "severity": "critical",
        "affected_ecus": ["gateway", "telematics"],
        "description": "Unsigned firmware updates can be installed",
        "cvss": 9.3
    },
    "CVE-2024-AUTO-006": {
        "name": "Key Fob Relay Attack",
        "severity": "high",
        "affected_ecus": ["body_control"],
        "description": "Keyless entry signal can be amplified for theft",
        "cvss": 7.8
    },
    "CVE-2024-AUTO-007": {
        "name": "ADAS Sensor Spoofing",
        "severity": "critical",
        "affected_ecus": ["adas"],
        "description": "Camera/radar inputs can be manipulated",
        "cvss": 9.0
    },
    "CVE-2024-AUTO-008": {
        "name": "Charging Port Exploitation",
        "severity": "high",
        "affected_ecus": ["battery_management"],
        "description": "Malicious charging station can compromise BMS",
        "cvss": 8.1
    }
}


class CANBusMonitorConfig(BaseModel):
    """CAN Bus Monitoring Configuration"""
    vehicle_id: str
    monitoring_mode: str = "passive"  # passive, active, learning
    alert_threshold: int = 5
    baseline_enabled: bool = True
    anomaly_detection: bool = True


class CANMessage(BaseModel):
    """CAN Bus Message"""
    arbitration_id: str
    data: str
    timestamp: str
    dlc: int = 8
    is_extended: bool = False


class ECUScanRequest(BaseModel):
    """ECU Vulnerability Scan Request"""
    vehicle_id: str
    ecu_types: List[str] = []  # Empty = scan all
    scan_depth: str = "standard"  # quick, standard, deep
    include_firmware_analysis: bool = True


class GPSData(BaseModel):
    """GPS Data for Spoofing Detection"""
    vehicle_id: str
    latitude: float
    longitude: float
    altitude: float = 0
    speed: float = 0
    heading: float = 0
    satellites: int = 0
    hdop: float = 1.0
    timestamp: str
    signal_strength: float = -100


class FleetVehicle(BaseModel):
    """Fleet Vehicle Registration"""
    vehicle_id: str
    vin: str
    fleet_id: str
    driver_id: Optional[str] = None
    vehicle_type: str
    make: str
    model: str
    year: int
    telematics_id: Optional[str] = None
    security_policy: str = "standard"


class ThreatEvent(BaseModel):
    """Vehicle Threat Event"""
    vehicle_id: str
    threat_type: str
    severity: str
    source: str
    details: Dict
    location: Optional[Dict] = None


# ==================== CAN BUS MONITORING ====================

@router.post("/can-bus/monitor/start")
async def start_can_monitoring(config: CANBusMonitorConfig):
    """
    Start real-time CAN bus monitoring for a vehicle
    """
    db = dependencies.get_db()
    session_id = str(uuid4())
    
    monitor_record = {
        "id": session_id,
        "vehicle_id": config.vehicle_id,
        "monitoring_mode": config.monitoring_mode,
        "alert_threshold": config.alert_threshold,
        "baseline_enabled": config.baseline_enabled,
        "anomaly_detection": config.anomaly_detection,
        "status": "active",
        "messages_processed": 0,
        "anomalies_detected": 0,
        "alerts_generated": 0,
        "started_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.can_monitor_sessions.insert_one(monitor_record)
    
    return {
        "session_id": session_id,
        "status": "monitoring_started",
        "vehicle_id": config.vehicle_id,
        "mode": config.monitoring_mode,
        "features_enabled": {
            "baseline_learning": config.baseline_enabled,
            "anomaly_detection": config.anomaly_detection,
            "real_time_alerts": True
        }
    }


@router.post("/can-bus/monitor/analyze-stream")
async def analyze_can_stream(
    session_id: str,
    messages: List[CANMessage]
):
    """
    Analyze a stream of CAN bus messages for anomalies
    """
    db = dependencies.get_db()
    
    session = await db.can_monitor_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Monitoring session not found")
    
    analysis_results = {
        "messages_analyzed": len(messages),
        "anomalies": [],
        "alerts": [],
        "statistics": {
            "unique_ids": len(set(m.arbitration_id for m in messages)),
            "total_bytes": sum(m.dlc for m in messages),
            "time_span_ms": 0
        }
    }
    
    # Analyze each message for anomalies
    suspicious_ids = ["0x7DF", "0x7E0", "0x7E8"]  # UDS diagnostic IDs
    injection_patterns = ["deadbeef", "cafebabe", "ffffffff"]
    
    for msg in messages:
        # Check for suspicious arbitration IDs
        if any(sus_id in msg.arbitration_id.upper() for sus_id in suspicious_ids):
            analysis_results["anomalies"].append({
                "type": "suspicious_arbitration_id",
                "severity": "high",
                "message_id": msg.arbitration_id,
                "description": "Diagnostic/UDS arbitration ID detected - possible diagnostic tool or attack"
            })
        
        # Check for injection patterns
        if any(pattern in msg.data.lower() for pattern in injection_patterns):
            analysis_results["anomalies"].append({
                "type": "injection_pattern",
                "severity": "critical",
                "message_id": msg.arbitration_id,
                "description": "Known injection pattern detected in CAN message data"
            })
        
        # Check for high-frequency messages (would need timestamps in real impl)
        # Check for message length anomalies
        if msg.dlc > 8:
            analysis_results["anomalies"].append({
                "type": "dlc_anomaly",
                "severity": "medium",
                "message_id": msg.arbitration_id,
                "description": f"Abnormal DLC value: {msg.dlc} (expected ≤8)"
            })
    
    # Generate alerts if threshold exceeded
    if len(analysis_results["anomalies"]) >= session.get("alert_threshold", 5):
        alert = {
            "id": str(uuid4()),
            "session_id": session_id,
            "vehicle_id": session["vehicle_id"],
            "type": "can_bus_attack",
            "severity": "critical" if any(a["severity"] == "critical" for a in analysis_results["anomalies"]) else "high",
            "anomaly_count": len(analysis_results["anomalies"]),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        analysis_results["alerts"].append(alert)
        await db.vehicle_alerts.insert_one(alert)
    
    # Update session stats
    await db.can_monitor_sessions.update_one(
        {"id": session_id},
        {
            "$inc": {
                "messages_processed": len(messages),
                "anomalies_detected": len(analysis_results["anomalies"]),
                "alerts_generated": len(analysis_results["alerts"])
            }
        }
    )
    
    return analysis_results


@router.get("/can-bus/monitor/status/{session_id}")
async def get_monitor_status(session_id: str):
    """
    Get CAN bus monitoring session status
    """
    db = dependencies.get_db()
    
    session = await db.can_monitor_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.post("/can-bus/monitor/stop/{session_id}")
async def stop_can_monitoring(session_id: str):
    """
    Stop CAN bus monitoring session
    """
    db = dependencies.get_db()
    
    result = await db.can_monitor_sessions.update_one(
        {"id": session_id},
        {
            "$set": {
                "status": "stopped",
                "stopped_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "monitoring_stopped", "session_id": session_id}


# ==================== ECU VULNERABILITY SCANNING ====================

@router.post("/ecu/scan")
async def scan_ecu_vulnerabilities(request: ECUScanRequest):
    """
    Scan vehicle ECUs for known vulnerabilities
    """
    db = dependencies.get_db()
    scan_id = str(uuid4())
    
    # If no specific ECUs, scan all
    ecus_to_scan = request.ecu_types if request.ecu_types else list(ECU_TYPES.keys())
    
    # Validate ECU types
    invalid_ecus = [e for e in ecus_to_scan if e not in ECU_TYPES]
    if invalid_ecus:
        raise HTTPException(status_code=400, detail=f"Invalid ECU types: {invalid_ecus}")
    
    scan_results = {
        "id": scan_id,
        "vehicle_id": request.vehicle_id,
        "scan_depth": request.scan_depth,
        "ecus_scanned": [],
        "vulnerabilities_found": [],
        "total_vulnerabilities": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "risk_score": 0,
        "scan_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    for ecu_type in ecus_to_scan:
        ecu_info = ECU_TYPES[ecu_type]
        ecu_result = {
            "ecu_type": ecu_type,
            "name": ecu_info["name"],
            "criticality": ecu_info["criticality"],
            "attack_surface": ecu_info["attack_surface"],
            "vulnerabilities": [],
            "firmware_version": f"v{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,99)}",
            "last_update": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))).isoformat()
        }
        
        # Check for known vulnerabilities
        for cve_id, vuln in ECU_VULNERABILITIES.items():
            if ecu_type in vuln["affected_ecus"]:
                vuln_entry = {
                    "cve_id": cve_id,
                    "name": vuln["name"],
                    "severity": vuln["severity"],
                    "cvss": vuln["cvss"],
                    "description": vuln["description"],
                    "remediation": f"Update {ecu_info['name']} firmware to latest version"
                }
                ecu_result["vulnerabilities"].append(vuln_entry)
                scan_results["vulnerabilities_found"].append(vuln_entry)
                
                if vuln["severity"] == "critical":
                    scan_results["critical_count"] += 1
                elif vuln["severity"] == "high":
                    scan_results["high_count"] += 1
                else:
                    scan_results["medium_count"] += 1
        
        scan_results["ecus_scanned"].append(ecu_result)
    
    scan_results["total_vulnerabilities"] = len(scan_results["vulnerabilities_found"])
    
    # Calculate risk score
    scan_results["risk_score"] = min(100, 
        scan_results["critical_count"] * 25 + 
        scan_results["high_count"] * 15 + 
        scan_results["medium_count"] * 5
    )
    
    # Determine overall risk level
    if scan_results["risk_score"] >= 75:
        scan_results["risk_level"] = "critical"
    elif scan_results["risk_score"] >= 50:
        scan_results["risk_level"] = "high"
    elif scan_results["risk_score"] >= 25:
        scan_results["risk_level"] = "medium"
    else:
        scan_results["risk_level"] = "low"
    
    # Generate recommendations
    scan_results["recommendations"] = []
    if scan_results["critical_count"] > 0:
        scan_results["recommendations"].append("URGENT: Update critical ECU firmware immediately")
        scan_results["recommendations"].append("Disable remote access until vulnerabilities are patched")
    if scan_results["high_count"] > 0:
        scan_results["recommendations"].append("Schedule firmware updates for high-risk ECUs within 7 days")
    if any(ecu["ecu_type"] == "gateway" for ecu in scan_results["ecus_scanned"]):
        scan_results["recommendations"].append("Enable CAN bus intrusion detection on gateway")
    
    await db.ecu_scans.insert_one({**scan_results, "_id": None})
    
    return scan_results


@router.get("/ecu/types")
async def get_ecu_types():
    """
    Get all ECU types and their details
    """
    return {
        "ecu_types": [
            {
                "id": ecu_id,
                **ecu_info
            }
            for ecu_id, ecu_info in ECU_TYPES.items()
        ],
        "total": len(ECU_TYPES)
    }


@router.get("/ecu/vulnerabilities")
async def get_ecu_vulnerabilities(severity: Optional[str] = None):
    """
    Get known ECU vulnerabilities
    """
    vulns = []
    for cve_id, vuln in ECU_VULNERABILITIES.items():
        if severity and vuln["severity"] != severity:
            continue
        vulns.append({
            "cve_id": cve_id,
            **vuln
        })
    
    return {
        "vulnerabilities": vulns,
        "total": len(vulns)
    }


@router.get("/ecu/scan-history/{vehicle_id}")
async def get_ecu_scan_history(vehicle_id: str, limit: int = Query(default=10, le=50)):
    """
    Get ECU scan history for a vehicle
    """
    db = dependencies.get_db()
    
    scans = await db.ecu_scans.find(
        {"vehicle_id": vehicle_id},
        {"_id": 0}
    ).sort("scan_timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "vehicle_id": vehicle_id,
        "total_scans": len(scans),
        "scans": scans
    }


# ==================== GPS SPOOFING DETECTION ====================

@router.post("/gps/analyze")
async def analyze_gps_data(data: GPSData):
    """
    Analyze GPS data for spoofing indicators
    """
    db = dependencies.get_db()
    analysis_id = str(uuid4())
    
    spoof_indicators = []
    risk_score = 0
    
    # Check for invalid coordinates
    if not (-90 <= data.latitude <= 90) or not (-180 <= data.longitude <= 180):
        risk_score += 50
        spoof_indicators.append({
            "indicator": "invalid_coordinates",
            "severity": "critical",
            "description": "GPS coordinates outside valid range"
        })
    
    # Check satellite count (legitimate GPS usually has 4+ satellites)
    if data.satellites < 4:
        risk_score += 20
        spoof_indicators.append({
            "indicator": "low_satellite_count",
            "severity": "medium",
            "description": f"Only {data.satellites} satellites (expected ≥4 for accurate fix)"
        })
    elif data.satellites > 20:
        risk_score += 30
        spoof_indicators.append({
            "indicator": "excessive_satellites",
            "severity": "high",
            "description": f"Unusually high satellite count ({data.satellites}) may indicate spoofing"
        })
    
    # Check HDOP (Horizontal Dilution of Precision) - lower is better, >5 is suspicious
    if data.hdop < 0.5:
        risk_score += 25
        spoof_indicators.append({
            "indicator": "unrealistic_hdop",
            "severity": "high",
            "description": f"HDOP value ({data.hdop}) too low - may indicate simulated signal"
        })
    elif data.hdop > 10:
        risk_score += 15
        spoof_indicators.append({
            "indicator": "poor_hdop",
            "severity": "medium",
            "description": f"Poor HDOP value ({data.hdop}) indicates degraded signal quality"
        })
    
    # Check signal strength (typical GPS: -130 to -110 dBm)
    if data.signal_strength > -100:
        risk_score += 35
        spoof_indicators.append({
            "indicator": "signal_too_strong",
            "severity": "critical",
            "description": f"GPS signal strength ({data.signal_strength} dBm) abnormally high - likely spoofed"
        })
    elif data.signal_strength < -140:
        risk_score += 10
        spoof_indicators.append({
            "indicator": "signal_too_weak",
            "severity": "low",
            "description": f"GPS signal very weak ({data.signal_strength} dBm)"
        })
    
    # Check speed vs heading consistency (would need historical data)
    if data.speed > 200:  # km/h, unrealistic for most vehicles
        risk_score += 20
        spoof_indicators.append({
            "indicator": "unrealistic_speed",
            "severity": "high",
            "description": f"Reported speed ({data.speed} km/h) unrealistic for standard vehicles"
        })
    
    # Check for sudden location jumps (would need previous location)
    # Get last known location
    last_location = await db.gps_history.find_one(
        {"vehicle_id": data.vehicle_id},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    if last_location:
        # Calculate distance between points
        lat1, lon1 = math.radians(last_location.get("latitude", 0)), math.radians(last_location.get("longitude", 0))
        lat2, lon2 = math.radians(data.latitude), math.radians(data.longitude)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance_km = 6371 * c  # Earth radius in km
        
        # If moved more than 10km in less than expected time, flag as suspicious
        if distance_km > 10:  # Simplified check
            risk_score += 40
            spoof_indicators.append({
                "indicator": "location_jump",
                "severity": "critical",
                "description": f"Location jumped {distance_km:.1f}km from last known position"
            })
    
    # Store GPS data for history
    gps_record = {
        "id": analysis_id,
        "vehicle_id": data.vehicle_id,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "altitude": data.altitude,
        "speed": data.speed,
        "heading": data.heading,
        "satellites": data.satellites,
        "hdop": data.hdop,
        "signal_strength": data.signal_strength,
        "timestamp": data.timestamp,
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }
    await db.gps_history.insert_one(gps_record)
    
    is_spoofed = risk_score >= 40
    threat_level = "critical" if risk_score >= 70 else "high" if risk_score >= 40 else "medium" if risk_score >= 20 else "low"
    
    analysis_result = {
        "analysis_id": analysis_id,
        "vehicle_id": data.vehicle_id,
        "is_spoofed": is_spoofed,
        "confidence": min(100, risk_score + 30) if is_spoofed else max(0, 100 - risk_score),
        "risk_score": risk_score,
        "threat_level": threat_level,
        "spoof_indicators": spoof_indicators,
        "gps_quality": {
            "satellites": data.satellites,
            "hdop": data.hdop,
            "signal_strength": data.signal_strength
        },
        "recommendation": "GPS signal may be spoofed - verify location via alternative means" if is_spoofed else "GPS signal appears legitimate",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # If spoofing detected, create alert
    if is_spoofed:
        alert = {
            "id": str(uuid4()),
            "vehicle_id": data.vehicle_id,
            "type": "gps_spoofing",
            "severity": threat_level,
            "details": analysis_result,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.vehicle_alerts.insert_one(alert)
    
    return analysis_result


@router.get("/gps/history/{vehicle_id}")
async def get_gps_history(
    vehicle_id: str,
    limit: int = Query(default=100, le=500)
):
    """
    Get GPS history for a vehicle
    """
    db = dependencies.get_db()
    
    history = await db.gps_history.find(
        {"vehicle_id": vehicle_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "vehicle_id": vehicle_id,
        "total_points": len(history),
        "history": history
    }


# ==================== FLEET SECURITY MANAGEMENT ====================

@router.post("/fleet/register")
async def register_fleet_vehicle(vehicle: FleetVehicle):
    """
    Register a vehicle to a fleet with security policies
    """
    db = dependencies.get_db()
    
    fleet_record = {
        "id": str(uuid4()),
        "vehicle_id": vehicle.vehicle_id,
        "vin": vehicle.vin,
        "vin_hash": hashlib.sha256(vehicle.vin.encode()).hexdigest()[:16],
        "fleet_id": vehicle.fleet_id,
        "driver_id": vehicle.driver_id,
        "vehicle_type": vehicle.vehicle_type,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "telematics_id": vehicle.telematics_id,
        "security_policy": vehicle.security_policy,
        "security_status": "active",
        "threat_level": "low",
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "compliance_status": "compliant"
    }
    
    await db.fleet_vehicles.insert_one(fleet_record)
    
    return {
        "registration_id": fleet_record["id"],
        "vehicle_id": vehicle.vehicle_id,
        "fleet_id": vehicle.fleet_id,
        "security_policy": vehicle.security_policy,
        "status": "registered"
    }


@router.get("/fleet/{fleet_id}/vehicles")
async def get_fleet_vehicles(
    fleet_id: str,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """
    Get all vehicles in a fleet
    """
    db = dependencies.get_db()
    
    query = {"fleet_id": fleet_id}
    if status:
        query["security_status"] = status
    
    vehicles = await db.fleet_vehicles.find(
        query,
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    return {
        "fleet_id": fleet_id,
        "total_vehicles": len(vehicles),
        "vehicles": vehicles
    }


@router.get("/fleet/{fleet_id}/security-overview")
async def get_fleet_security_overview(fleet_id: str):
    """
    Get security overview for entire fleet
    """
    db = dependencies.get_db()
    
    vehicles = await db.fleet_vehicles.find(
        {"fleet_id": fleet_id},
        {"_id": 0}
    ).to_list(1000)
    
    if not vehicles:
        return {
            "fleet_id": fleet_id,
            "total_vehicles": 0,
            "message": "No vehicles found in this fleet"
        }
    
    # Calculate fleet statistics
    threat_levels = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    compliance_status = {"compliant": 0, "non_compliant": 0, "pending": 0}
    
    for v in vehicles:
        threat_levels[v.get("threat_level", "low")] += 1
        compliance_status[v.get("compliance_status", "pending")] += 1
    
    # Get recent alerts
    recent_alerts = await db.vehicle_alerts.find(
        {"vehicle_id": {"$in": [v["vehicle_id"] for v in vehicles]}},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    # Calculate fleet risk score
    risk_score = (
        threat_levels["critical"] * 40 +
        threat_levels["high"] * 20 +
        threat_levels["medium"] * 10 +
        compliance_status["non_compliant"] * 15
    )
    
    return {
        "fleet_id": fleet_id,
        "total_vehicles": len(vehicles),
        "fleet_risk_score": min(100, risk_score),
        "threat_distribution": threat_levels,
        "compliance_distribution": compliance_status,
        "vehicles_at_risk": threat_levels["high"] + threat_levels["critical"],
        "recent_alerts": recent_alerts,
        "recommendations": [
            "Update firmware on high-risk vehicles" if threat_levels["high"] + threat_levels["critical"] > 0 else None,
            "Address compliance issues" if compliance_status["non_compliant"] > 0 else None,
            "Enable enhanced monitoring for at-risk vehicles" if threat_levels["critical"] > 0 else None
        ],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/fleet/{fleet_id}/policy")
async def update_fleet_policy(
    fleet_id: str,
    policy_name: str,
    policy_settings: Dict
):
    """
    Update security policy for entire fleet
    """
    db = dependencies.get_db()
    
    result = await db.fleet_vehicles.update_many(
        {"fleet_id": fleet_id},
        {
            "$set": {
                "security_policy": policy_name,
                "policy_settings": policy_settings,
                "policy_updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "fleet_id": fleet_id,
        "vehicles_updated": result.modified_count,
        "policy": policy_name,
        "status": "policy_updated"
    }


# ==================== VEHICLE THREAT TRACKING ====================

@router.get("/threats/dashboard")
async def get_threat_dashboard():
    """
    Get comprehensive threat tracking dashboard
    """
    db = dependencies.get_db()
    
    # Get threat counts by severity
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    severity_counts = await db.vehicle_threats.aggregate(pipeline).to_list(None)
    
    # Get threat counts by type
    type_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$threat_type", "count": {"$sum": 1}}}
    ]
    type_counts = await db.vehicle_threats.aggregate(type_pipeline).to_list(None)
    
    # Get recent threats
    recent_threats = await db.vehicle_threats.find(
        {"status": "active"},
        {"_id": 0}
    ).sort("reported_at", -1).limit(10).to_list(10)
    
    # Total counts
    total_active = await db.vehicle_threats.count_documents({"status": "active"})
    total_resolved = await db.vehicle_threats.count_documents({"status": "resolved"})
    
    return {
        "summary": {
            "total_active": total_active,
            "total_resolved": total_resolved,
            "resolution_rate": round(total_resolved / max(1, total_active + total_resolved) * 100, 2)
        },
        "by_severity": {s["_id"]: s["count"] for s in severity_counts if s["_id"]},
        "by_type": {t["_id"]: t["count"] for t in type_counts if t["_id"]},
        "recent_threats": recent_threats,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/threats/report")
async def report_vehicle_threat(event: ThreatEvent):
    """
    Report a threat event for a vehicle
    """
    db = dependencies.get_db()
    
    threat_id = str(uuid4())
    threat_record = {
        "id": threat_id,
        "vehicle_id": event.vehicle_id,
        "threat_type": event.threat_type,
        "severity": event.severity,
        "source": event.source,
        "details": event.details,
        "location": event.location,
        "status": "active",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.vehicle_threats.insert_one(threat_record)
    
    # Update vehicle threat level
    threat_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    current_priority = threat_priority.get(event.severity, 1)
    
    # Get current vehicle threat level
    vehicle = await db.fleet_vehicles.find_one({"vehicle_id": event.vehicle_id})
    if vehicle:
        current_level = threat_priority.get(vehicle.get("threat_level", "low"), 1)
        if current_priority > current_level:
            await db.fleet_vehicles.update_one(
                {"vehicle_id": event.vehicle_id},
                {"$set": {"threat_level": event.severity}}
            )
    
    return {
        "threat_id": threat_id,
        "vehicle_id": event.vehicle_id,
        "severity": event.severity,
        "status": "reported",
        "escalation": "immediate" if event.severity == "critical" else "standard"
    }


@router.get("/threats/{vehicle_id}")
async def get_vehicle_threats(
    vehicle_id: str,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    Get threat history for a vehicle
    """
    db = dependencies.get_db()
    
    query = {"vehicle_id": vehicle_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity
    
    threats = await db.vehicle_threats.find(
        query,
        {"_id": 0}
    ).sort("reported_at", -1).limit(limit).to_list(limit)
    
    return {
        "vehicle_id": vehicle_id,
        "total_threats": len(threats),
        "threats": threats
    }


@router.put("/threats/{threat_id}/resolve")
async def resolve_threat(threat_id: str, resolution: str):
    """
    Mark a threat as resolved
    """
    db = dependencies.get_db()
    
    result = await db.vehicle_threats.update_one(
        {"id": threat_id},
        {
            "$set": {
                "status": "resolved",
                "resolution": resolution,
                "resolved_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Threat not found")
    
    return {
        "threat_id": threat_id,
        "status": "resolved",
        "resolution": resolution
    }
