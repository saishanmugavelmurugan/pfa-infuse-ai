"""
Automotive Security API
Part of SecureSphere Automotive Tier

Provides:
- Connected vehicle security monitoring
- V2X (Vehicle-to-Everything) security
- CAN bus anomaly detection
- OTA update security
- Telematics protection
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
from uuid import uuid4

import dependencies

router = APIRouter(prefix="/securesphere/automotive", tags=["SecureSphere - Automotive Security"])


# Vehicle Types
VEHICLE_TYPES = {
    "ice": "Internal Combustion Engine",
    "bev": "Battery Electric Vehicle",
    "phev": "Plug-in Hybrid Electric Vehicle",
    "hev": "Hybrid Electric Vehicle",
    "fcev": "Fuel Cell Electric Vehicle"
}

# Threat Categories for Automotive
AUTO_THREAT_CATEGORIES = [
    "can_bus_injection",
    "telematics_breach",
    "ota_tampering",
    "keyless_relay",
    "gps_spoofing",
    "infotainment_exploit",
    "charging_station_attack",  # EV specific
    "v2x_spoofing"
]


class VehicleRegistration(BaseModel):
    """Connected Vehicle Registration"""
    vin: str  # Vehicle Identification Number
    vehicle_type: str  # ice, bev, phev, hev, fcev
    manufacturer: str
    model: str
    year: int
    owner_id: str
    telematics_provider: Optional[str] = None
    connectivity_type: Optional[str] = "4g"  # 4g, 5g, wifi


class VehicleEvent(BaseModel):
    """Vehicle Security Event"""
    vehicle_id: str
    event_type: str
    severity: str  # info, warning, critical
    data: Dict
    timestamp: Optional[str] = None


class CANBusData(BaseModel):
    """CAN Bus Data for Analysis"""
    vehicle_id: str
    can_messages: List[Dict]  # [{id, data, timestamp}]
    ecu_source: Optional[str] = None


@router.post("/vehicles/register")
async def register_vehicle(vehicle: VehicleRegistration):
    """
    Register a connected vehicle for security monitoring
    """
    if vehicle.vehicle_type not in VEHICLE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid vehicle type. Must be one of: {list(VEHICLE_TYPES.keys())}")
    
    db = dependencies.get_db()
    
    vehicle_id = str(uuid4())
    vehicle_record = {
        "id": vehicle_id,
        "vin_hash": hash(vehicle.vin) % 10**8,  # Store hash only for privacy
        "vehicle_type": vehicle.vehicle_type,
        "vehicle_type_name": VEHICLE_TYPES[vehicle.vehicle_type],
        "manufacturer": vehicle.manufacturer,
        "model": vehicle.model,
        "year": vehicle.year,
        "owner_id": vehicle.owner_id,
        "telematics_provider": vehicle.telematics_provider,
        "connectivity_type": vehicle.connectivity_type,
        "status": "active",
        "security_score": 100,
        "threat_level": "low",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat()
    }
    
    await db.vehicles.insert_one(vehicle_record)
    
    return {
        "vehicle_id": vehicle_id,
        "status": "registered",
        "monitoring_features": [
            "CAN Bus Monitoring",
            "Telematics Security",
            "OTA Update Verification",
            "GPS Integrity Check",
            "V2X Security" if vehicle.connectivity_type == "5g" else None
        ],
        "security_score": 100
    }


@router.get("/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    """
    Get vehicle details and security status
    """
    db = dependencies.get_db()
    
    vehicle = await db.vehicles.find_one(
        {"id": vehicle_id},
        {"_id": 0}
    )
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return vehicle


@router.get("/vehicles/owner/{owner_id}")
async def get_owner_vehicles(owner_id: str):
    """
    Get all vehicles for an owner
    """
    db = dependencies.get_db()
    
    vehicles = await db.vehicles.find(
        {"owner_id": owner_id, "status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    return {
        "owner_id": owner_id,
        "total_vehicles": len(vehicles),
        "vehicles": vehicles
    }


@router.post("/events/report")
async def report_vehicle_event(event: VehicleEvent):
    """
    Report a vehicle security event
    """
    db = dependencies.get_db()
    
    event_id = str(uuid4())
    event_record = {
        "id": event_id,
        "vehicle_id": event.vehicle_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "data": event.data,
        "status": "active",
        "created_at": event.timestamp or datetime.now(timezone.utc).isoformat()
    }
    
    await db.vehicle_events.insert_one(event_record)
    
    # Update vehicle threat level if critical
    if event.severity == "critical":
        await db.vehicles.update_one(
            {"id": event.vehicle_id},
            {
                "$set": {
                    "threat_level": "critical",
                    "security_score": 25
                }
            }
        )
    
    return {
        "event_id": event_id,
        "status": "reported",
        "severity": event.severity,
        "response_action": "alert_owner" if event.severity == "critical" else "logged"
    }


@router.get("/events/{vehicle_id}")
async def get_vehicle_events(
    vehicle_id: str,
    severity: Optional[str] = None,
    limit: int = Query(default=20, le=100)
):
    """
    Get security events for a vehicle
    """
    db = dependencies.get_db()
    
    query = {"vehicle_id": vehicle_id}
    if severity:
        query["severity"] = severity
    
    events = await db.vehicle_events.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "vehicle_id": vehicle_id,
        "total_events": len(events),
        "events": events
    }


@router.post("/can-bus/analyze")
async def analyze_can_bus(data: CANBusData):
    """
    Analyze CAN bus data for anomalies
    Detects potential injection attacks and unauthorized ECU commands
    """
    analysis_id = str(uuid4())
    anomalies = []
    
    # Simplified anomaly detection (in production, use ML models)
    for msg in data.can_messages:
        can_id = msg.get('id', '')
        can_data = msg.get('data', '')
        
        # Check for suspicious CAN IDs (diagnostic, safety-critical)
        suspicious_ids = ['7DF', '7E0', '7E8', '000', '001']  # Common diagnostic/safety IDs
        if any(s_id in str(can_id).upper() for s_id in suspicious_ids):
            anomalies.append({
                "type": "suspicious_can_id",
                "can_id": can_id,
                "severity": "warning",
                "description": "Access to diagnostic/safety-critical CAN ID detected"
            })
        
        # Check for abnormal message frequency (simplified)
        if len(data.can_messages) > 1000:
            anomalies.append({
                "type": "high_frequency",
                "severity": "warning",
                "description": "Unusually high CAN bus message frequency detected"
            })
            break
    
    threat_level = "critical" if len(anomalies) > 5 else "high" if len(anomalies) > 2 else "low" if anomalies else "none"
    
    # Store analysis
    db = dependencies.get_db()
    await db.can_analyses.insert_one({
        "id": analysis_id,
        "vehicle_id": data.vehicle_id,
        "messages_analyzed": len(data.can_messages),
        "anomalies_found": len(anomalies),
        "threat_level": threat_level,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "analysis_id": analysis_id,
        "messages_analyzed": len(data.can_messages),
        "anomalies_detected": len(anomalies),
        "threat_level": threat_level,
        "anomalies": anomalies,
        "recommendations": [
            "Review unauthorized diagnostic tool access",
            "Check for aftermarket devices on CAN bus",
            "Verify ECU firmware integrity"
        ] if anomalies else ["No immediate action required"]
    }


@router.post("/ota/verify")
async def verify_ota_update(
    vehicle_id: str,
    update_hash: str,
    update_version: str,
    update_size: int
):
    """
    Verify OTA update integrity before installation
    """
    verification_id = str(uuid4())
    
    # Simplified verification (in production, verify against manufacturer database)
    is_valid = len(update_hash) == 64  # Check if it looks like SHA-256
    is_size_reasonable = 1000 < update_size < 5000000000  # 1KB to 5GB
    
    # Check for known malicious hashes (mock database)
    known_malicious = ["abc123", "def456"]  # Mock malicious hashes
    is_clean = update_hash[:6] not in known_malicious
    
    verification_passed = is_valid and is_size_reasonable and is_clean
    
    db = dependencies.get_db()
    await db.ota_verifications.insert_one({
        "id": verification_id,
        "vehicle_id": vehicle_id,
        "update_version": update_version,
        "update_hash": update_hash[:16] + "...",  # Store partial hash
        "verification_passed": verification_passed,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "verification_id": verification_id,
        "update_version": update_version,
        "verification_passed": verification_passed,
        "checks": {
            "hash_format_valid": is_valid,
            "size_reasonable": is_size_reasonable,
            "not_in_blocklist": is_clean
        },
        "recommendation": "Safe to install" if verification_passed else "DO NOT INSTALL - Verification failed"
    }


@router.get("/threat-categories")
async def get_threat_categories():
    """
    Get automotive-specific threat categories
    """
    return {
        "categories": [
            {
                "id": "can_bus_injection",
                "name": "CAN Bus Injection",
                "description": "Unauthorized commands sent to vehicle ECUs via CAN bus",
                "severity": "critical",
                "affected_systems": ["Engine", "Brakes", "Steering", "ADAS"]
            },
            {
                "id": "telematics_breach",
                "name": "Telematics Breach",
                "description": "Unauthorized access to vehicle telematics unit",
                "severity": "high",
                "affected_systems": ["GPS", "Cellular", "Remote Access"]
            },
            {
                "id": "ota_tampering",
                "name": "OTA Update Tampering",
                "description": "Malicious modification of over-the-air software updates",
                "severity": "critical",
                "affected_systems": ["All ECUs", "Infotainment", "ADAS"]
            },
            {
                "id": "keyless_relay",
                "name": "Keyless Entry Relay Attack",
                "description": "Relay attack to unlock and start vehicle without key",
                "severity": "high",
                "affected_systems": ["Keyless Entry", "Immobilizer"]
            },
            {
                "id": "gps_spoofing",
                "name": "GPS Spoofing",
                "description": "Fake GPS signals to mislead navigation and tracking",
                "severity": "medium",
                "affected_systems": ["Navigation", "Fleet Tracking", "Geofencing"]
            },
            {
                "id": "charging_station_attack",
                "name": "EV Charging Station Attack",
                "description": "Attacks via compromised charging infrastructure (EV specific)",
                "severity": "high",
                "affected_systems": ["Battery Management", "Charging Controller"]
            },
            {
                "id": "v2x_spoofing",
                "name": "V2X Communication Spoofing",
                "description": "Fake vehicle-to-everything messages to cause accidents",
                "severity": "critical",
                "affected_systems": ["V2V", "V2I", "ADAS"]
            }
        ]
    }


@router.get("/stats")
async def get_automotive_stats():
    """
    Get automotive security statistics
    """
    db = dependencies.get_db()
    
    total_vehicles = await db.vehicles.count_documents({"status": "active"})
    
    # Vehicle type breakdown
    type_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$vehicle_type", "count": {"$sum": 1}}}
    ]
    types = await db.vehicles.aggregate(type_pipeline).to_list(None)
    
    # Events by severity
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}}
    ]
    severities = await db.vehicle_events.aggregate(severity_pipeline).to_list(None)
    
    total_events = await db.vehicle_events.count_documents({})
    critical_events = await db.vehicle_events.count_documents({"severity": "critical"})
    
    return {
        "total_vehicles_protected": total_vehicles,
        "by_vehicle_type": {t['_id']: t['count'] for t in types if t['_id']},
        "total_security_events": total_events,
        "critical_events": critical_events,
        "events_by_severity": {s['_id']: s['count'] for s in severities if s['_id']},
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
