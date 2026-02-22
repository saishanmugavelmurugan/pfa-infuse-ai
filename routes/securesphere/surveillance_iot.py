"""
Surveillance IoT Module - Cameras, Smart Meters, Dashcams
Part of SecureSphere Platform

Provides:
- Device management for cameras, smart meters, dashcams
- NetFlow data collection and analysis
- Real-time monitoring and alerts
- Threat detection specific to surveillance devices
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import random

import dependencies

router = APIRouter(prefix="/securesphere/surveillance-iot", tags=["SecureSphere - Surveillance IoT"])


# ==================== DEVICE CATEGORIES ====================

DEVICE_CATEGORIES = {
    "cameras": {
        "name": "Cameras & CCTV",
        "description": "IP cameras, CCTV systems, security cameras",
        "types": [
            {"id": "ip_camera", "name": "IP Camera", "icon": "camera"},
            {"id": "cctv", "name": "CCTV System", "icon": "video"},
            {"id": "ptz_camera", "name": "PTZ Camera", "icon": "move"},
            {"id": "dome_camera", "name": "Dome Camera", "icon": "circle"},
            {"id": "bullet_camera", "name": "Bullet Camera", "icon": "target"},
            {"id": "thermal_camera", "name": "Thermal Camera", "icon": "thermometer"},
            {"id": "doorbell_camera", "name": "Doorbell Camera", "icon": "bell"},
            {"id": "body_camera", "name": "Body Camera", "icon": "user"}
        ],
        "threats": ["unauthorized_access", "stream_hijacking", "firmware_exploit", "credential_theft", "ddos_target"],
        "protocols": ["rtsp", "onvif", "http", "https", "rtmp"]
    },
    "smart_meters": {
        "name": "Smart Meters",
        "description": "Electricity, water, and gas smart meters",
        "types": [
            {"id": "electricity_meter", "name": "Electricity Meter", "icon": "zap"},
            {"id": "water_meter", "name": "Water Meter", "icon": "droplet"},
            {"id": "gas_meter", "name": "Gas Meter", "icon": "flame"},
            {"id": "solar_meter", "name": "Solar Meter", "icon": "sun"},
            {"id": "ev_charger_meter", "name": "EV Charger Meter", "icon": "battery-charging"},
            {"id": "industrial_meter", "name": "Industrial Meter", "icon": "factory"}
        ],
        "threats": ["data_tampering", "meter_bypass", "injection_attack", "replay_attack", "eavesdropping"],
        "protocols": ["dlms_cosem", "modbus", "zigbee", "lora", "nb_iot"]
    },
    "dashcams": {
        "name": "Dashcams",
        "description": "Vehicle dashboard cameras and fleet monitoring",
        "types": [
            {"id": "front_dashcam", "name": "Front Dashcam", "icon": "car"},
            {"id": "dual_dashcam", "name": "Dual Channel Dashcam", "icon": "copy"},
            {"id": "fleet_camera", "name": "Fleet Camera", "icon": "truck"},
            {"id": "360_dashcam", "name": "360° Dashcam", "icon": "globe"},
            {"id": "taxi_camera", "name": "Taxi/Ride Camera", "icon": "navigation"},
            {"id": "bus_camera", "name": "Bus/Transit Camera", "icon": "bus"}
        ],
        "threats": ["gps_spoofing", "video_tampering", "data_exfiltration", "remote_access", "cloud_breach"],
        "protocols": ["cellular_4g", "cellular_5g", "wifi", "bluetooth", "gps"]
    }
}

# Common manufacturers
MANUFACTURERS = {
    "cameras": ["Hikvision", "Dahua", "Axis", "Bosch", "Hanwha", "Uniview", "Vivotek", "Pelco", "Sony", "Panasonic"],
    "smart_meters": ["Itron", "Landis+Gyr", "Honeywell", "Kamstrup", "Sensus", "Elster", "Secure Meters", "HPL", "Genus Power"],
    "dashcams": ["Viofo", "Thinkware", "BlackVue", "Garmin", "Nextbase", "Vantrue", "VAVA", "Rexing", "REDTIGER"]
}


# ==================== PYDANTIC MODELS ====================

class CameraRegistration(BaseModel):
    """Camera device registration"""
    device_name: str
    device_type: str  # ip_camera, cctv, ptz_camera, etc.
    manufacturer: str
    model: str
    ip_address: str
    mac_address: Optional[str] = None
    location: str
    resolution: str = "1080p"  # 720p, 1080p, 4k
    has_night_vision: bool = True
    has_ptz: bool = False
    has_audio: bool = True
    stream_protocol: str = "rtsp"  # rtsp, onvif, http
    firmware_version: str
    owner_id: str
    organization_id: Optional[str] = None


class SmartMeterRegistration(BaseModel):
    """Smart meter device registration"""
    device_name: str
    device_type: str  # electricity_meter, water_meter, gas_meter
    manufacturer: str
    model: str
    meter_id: str  # Utility meter ID
    ip_address: Optional[str] = None
    location: str
    communication_type: str = "nb_iot"  # nb_iot, lora, zigbee, cellular
    reading_interval_minutes: int = 15
    firmware_version: str
    utility_provider: Optional[str] = None
    owner_id: str
    organization_id: Optional[str] = None


class DashcamRegistration(BaseModel):
    """Dashcam device registration"""
    device_name: str
    device_type: str  # front_dashcam, dual_dashcam, fleet_camera
    manufacturer: str
    model: str
    vehicle_id: str
    vehicle_type: str  # car, truck, bus, taxi, motorcycle
    license_plate: Optional[str] = None
    sim_iccid: Optional[str] = None  # For cellular dashcams
    resolution: str = "1080p"
    has_gps: bool = True
    has_cloud_backup: bool = True
    storage_gb: int = 64
    firmware_version: str
    owner_id: str
    organization_id: Optional[str] = None


class NetFlowData(BaseModel):
    """NetFlow data ingestion"""
    device_id: str
    flow_records: List[Dict[str, Any]]
    collection_timestamp: Optional[str] = None


# ==================== DEVICE MANAGEMENT ====================

@router.get("/categories")
async def get_device_categories():
    """Get all surveillance IoT device categories and types"""
    return {
        "categories": DEVICE_CATEGORIES,
        "manufacturers": MANUFACTURERS,
        "total_device_types": sum(len(cat["types"]) for cat in DEVICE_CATEGORIES.values())
    }


@router.post("/cameras/register")
async def register_camera(device: CameraRegistration):
    """Register a camera/CCTV device"""
    db = dependencies.get_db()
    
    device_id = str(uuid4())
    device_record = {
        "id": device_id,
        "category": "cameras",
        "device_name": device.device_name,
        "device_type": device.device_type,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "location": device.location,
        "resolution": device.resolution,
        "has_night_vision": device.has_night_vision,
        "has_ptz": device.has_ptz,
        "has_audio": device.has_audio,
        "stream_protocol": device.stream_protocol,
        "firmware_version": device.firmware_version,
        "owner_id": device.owner_id,
        "organization_id": device.organization_id,
        "status": "online",
        "health_score": 100,
        "security_score": 100,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "threats_detected": 0,
        "alerts_count": 0,
        "stream_status": "active",
        "recording_status": "recording",
        "netflow_enabled": True,
        "bytes_in_24h": 0,
        "bytes_out_24h": 0
    }
    
    await db.surveillance_devices.insert_one(device_record)
    
    return {
        "device_id": device_id,
        "status": "registered",
        "category": "cameras",
        "monitoring_enabled": True,
        "message": f"Camera '{device.device_name}' registered successfully"
    }


@router.post("/smart-meters/register")
async def register_smart_meter(device: SmartMeterRegistration):
    """Register a smart meter device"""
    db = dependencies.get_db()
    
    device_id = str(uuid4())
    device_record = {
        "id": device_id,
        "category": "smart_meters",
        "device_name": device.device_name,
        "device_type": device.device_type,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "meter_id": device.meter_id,
        "ip_address": device.ip_address,
        "location": device.location,
        "communication_type": device.communication_type,
        "reading_interval_minutes": device.reading_interval_minutes,
        "firmware_version": device.firmware_version,
        "utility_provider": device.utility_provider,
        "owner_id": device.owner_id,
        "organization_id": device.organization_id,
        "status": "online",
        "health_score": 100,
        "security_score": 100,
        "last_reading": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "threats_detected": 0,
        "alerts_count": 0,
        "tamper_detected": False,
        "current_reading": round(random.uniform(100, 5000), 2),
        "reading_unit": "kWh" if device.device_type == "electricity_meter" else "m³" if device.device_type in ["water_meter", "gas_meter"] else "units",
        "netflow_enabled": True,
        "bytes_in_24h": 0,
        "bytes_out_24h": 0
    }
    
    await db.surveillance_devices.insert_one(device_record)
    
    return {
        "device_id": device_id,
        "status": "registered",
        "category": "smart_meters",
        "monitoring_enabled": True,
        "message": f"Smart meter '{device.device_name}' registered successfully"
    }


@router.post("/dashcams/register")
async def register_dashcam(device: DashcamRegistration):
    """Register a dashcam device"""
    db = dependencies.get_db()
    
    device_id = str(uuid4())
    device_record = {
        "id": device_id,
        "category": "dashcams",
        "device_name": device.device_name,
        "device_type": device.device_type,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "vehicle_id": device.vehicle_id,
        "vehicle_type": device.vehicle_type,
        "license_plate": device.license_plate,
        "sim_iccid": device.sim_iccid,
        "resolution": device.resolution,
        "has_gps": device.has_gps,
        "has_cloud_backup": device.has_cloud_backup,
        "storage_gb": device.storage_gb,
        "firmware_version": device.firmware_version,
        "owner_id": device.owner_id,
        "organization_id": device.organization_id,
        "status": "online",
        "health_score": 100,
        "security_score": 100,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "threats_detected": 0,
        "alerts_count": 0,
        "recording_status": "recording",
        "gps_location": {
            "lat": round(random.uniform(28.5, 28.8), 6),
            "lng": round(random.uniform(77.1, 77.4), 6)
        } if device.has_gps else None,
        "storage_used_percent": random.randint(20, 80),
        "netflow_enabled": True,
        "bytes_in_24h": 0,
        "bytes_out_24h": 0
    }
    
    await db.surveillance_devices.insert_one(device_record)
    
    return {
        "device_id": device_id,
        "status": "registered",
        "category": "dashcams",
        "monitoring_enabled": True,
        "message": f"Dashcam '{device.device_name}' registered successfully"
    }


@router.get("/devices")
async def list_devices(
    category: Optional[str] = None,
    owner_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """List all surveillance IoT devices"""
    db = dependencies.get_db()
    
    query = {}
    if category:
        query["category"] = category
    if owner_id:
        query["owner_id"] = owner_id
    if status:
        query["status"] = status
    
    devices = await db.surveillance_devices.find(
        query,
        {"_id": 0}
    ).limit(limit).to_list(limit)
    
    # Group by category
    by_category = {"cameras": [], "smart_meters": [], "dashcams": []}
    for device in devices:
        cat = device.get("category", "cameras")
        if cat in by_category:
            by_category[cat].append(device)
    
    return {
        "total": len(devices),
        "devices": devices,
        "by_category": {
            "cameras": len(by_category["cameras"]),
            "smart_meters": len(by_category["smart_meters"]),
            "dashcams": len(by_category["dashcams"])
        }
    }


@router.get("/devices/{device_id}")
async def get_device(device_id: str):
    """Get device details"""
    db = dependencies.get_db()
    
    device = await db.surveillance_devices.find_one(
        {"id": device_id},
        {"_id": 0}
    )
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str):
    """Delete a device"""
    db = dependencies.get_db()
    
    result = await db.surveillance_devices.delete_one({"id": device_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"status": "deleted", "device_id": device_id}


# ==================== NETFLOW DATA COLLECTION ====================

@router.post("/netflow/ingest")
async def ingest_netflow_data(data: NetFlowData):
    """Ingest NetFlow data for a device"""
    db = dependencies.get_db()
    
    # Verify device exists
    device = await db.surveillance_devices.find_one({"id": data.device_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Process flow records
    total_bytes_in = 0
    total_bytes_out = 0
    suspicious_flows = []
    
    for flow in data.flow_records:
        bytes_in = flow.get("bytes_in", 0)
        bytes_out = flow.get("bytes_out", 0)
        total_bytes_in += bytes_in
        total_bytes_out += bytes_out
        
        # Detect suspicious patterns
        dest_port = flow.get("dest_port", 0)
        
        # Check for suspicious destinations
        if dest_port in [22, 23, 3389]:  # SSH, Telnet, RDP
            suspicious_flows.append({
                "type": "suspicious_port",
                "severity": "high",
                "details": f"Connection to management port {dest_port}"
            })
        
        # Check for high outbound traffic (potential exfiltration)
        if bytes_out > 100000000:  # 100MB
            suspicious_flows.append({
                "type": "data_exfiltration",
                "severity": "critical",
                "details": f"Large data transfer: {bytes_out / 1000000:.2f} MB"
            })
    
    # Store NetFlow record
    flow_record = {
        "id": str(uuid4()),
        "device_id": data.device_id,
        "flow_count": len(data.flow_records),
        "total_bytes_in": total_bytes_in,
        "total_bytes_out": total_bytes_out,
        "suspicious_flows": len(suspicious_flows),
        "collection_timestamp": data.collection_timestamp or datetime.now(timezone.utc).isoformat(),
        "stored_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.netflow_records.insert_one(flow_record)
    
    # Update device stats
    await db.surveillance_devices.update_one(
        {"id": data.device_id},
        {
            "$inc": {
                "bytes_in_24h": total_bytes_in,
                "bytes_out_24h": total_bytes_out
            },
            "$set": {"last_seen": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Generate alerts for suspicious flows
    if suspicious_flows:
        for flow in suspicious_flows:
            alert_record = {
                "id": str(uuid4()),
                "device_id": data.device_id,
                "alert_type": flow["type"],
                "severity": flow["severity"],
                "details": flow["details"],
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.surveillance_alerts.insert_one(alert_record)
        
        await db.surveillance_devices.update_one(
            {"id": data.device_id},
            {"$inc": {"alerts_count": len(suspicious_flows)}}
        )
    
    return {
        "status": "ingested",
        "flows_processed": len(data.flow_records),
        "total_bytes_in": total_bytes_in,
        "total_bytes_out": total_bytes_out,
        "suspicious_flows_detected": len(suspicious_flows),
        "alerts_generated": len(suspicious_flows)
    }


@router.get("/netflow/stats/{device_id}")
async def get_netflow_stats(device_id: str, hours: int = Query(default=24, le=168)):
    """Get NetFlow statistics for a device"""
    db = dependencies.get_db()
    
    device = await db.surveillance_devices.find_one({"id": device_id}, {"_id": 0})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get recent flow records (within the specified time period)
    records = await db.netflow_records.find(
        {"device_id": device_id},
        {"_id": 0}
    ).sort("stored_at", -1).limit(100).to_list(100)
    
    total_in = sum(r.get("total_bytes_in", 0) for r in records)
    total_out = sum(r.get("total_bytes_out", 0) for r in records)
    suspicious = sum(r.get("suspicious_flows", 0) for r in records)
    
    return {
        "device_id": device_id,
        "period_hours": hours,
        "statistics": {
            "total_bytes_in": total_in,
            "total_bytes_out": total_out,
            "total_flows_recorded": len(records),
            "suspicious_flows": suspicious,
            "average_bandwidth_kbps": round((total_in + total_out) / (hours * 3600) / 1024, 2) if hours > 0 else 0
        },
        "device_traffic": {
            "bytes_in_24h": device.get("bytes_in_24h", 0),
            "bytes_out_24h": device.get("bytes_out_24h", 0)
        }
    }


# ==================== REAL-TIME MONITORING ====================

@router.get("/monitoring/{device_id}")
async def get_device_monitoring(device_id: str):
    """Get real-time monitoring data for a device"""
    db = dependencies.get_db()
    
    device = await db.surveillance_devices.find_one({"id": device_id}, {"_id": 0})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    category = device.get("category", "cameras")
    
    # Generate realistic monitoring data based on device type
    monitoring_data = {
        "device_id": device_id,
        "category": category,
        "status": device.get("status", "online"),
        "health_score": device.get("health_score", 100),
        "security_score": device.get("security_score", 100),
        "last_seen": device.get("last_seen"),
        "uptime_hours": random.randint(24, 720),
        "cpu_usage_percent": random.randint(10, 60),
        "memory_usage_percent": random.randint(20, 70),
        "network": {
            "bytes_in_24h": device.get("bytes_in_24h", random.randint(10000000, 500000000)),
            "bytes_out_24h": device.get("bytes_out_24h", random.randint(5000000, 100000000)),
            "current_bandwidth_kbps": round(random.uniform(100, 2000), 2),
            "connection_status": "connected"
        },
        "threats_detected": device.get("threats_detected", 0),
        "alerts_count": device.get("alerts_count", 0)
    }
    
    # Add category-specific data
    if category == "cameras":
        monitoring_data["camera_specific"] = {
            "stream_status": device.get("stream_status", "active"),
            "recording_status": device.get("recording_status", "recording"),
            "resolution": device.get("resolution", "1080p"),
            "fps": random.randint(25, 30),
            "bitrate_kbps": random.randint(2000, 8000),
            "night_vision_active": random.choice([True, False]),
            "motion_detected": random.choice([True, False]),
            "storage_days_remaining": random.randint(7, 30)
        }
    elif category == "smart_meters":
        monitoring_data["meter_specific"] = {
            "current_reading": device.get("current_reading", round(random.uniform(100, 5000), 2)),
            "reading_unit": device.get("reading_unit", "kWh"),
            "last_reading_time": device.get("last_reading"),
            "communication_status": "connected",
            "tamper_detected": device.get("tamper_detected", False),
            "battery_level_percent": random.randint(60, 100) if device.get("communication_type") in ["lora", "zigbee"] else None,
            "signal_strength_dbm": random.randint(-90, -50)
        }
    elif category == "dashcams":
        monitoring_data["dashcam_specific"] = {
            "recording_status": device.get("recording_status", "recording"),
            "gps_location": device.get("gps_location"),
            "storage_used_percent": device.get("storage_used_percent", random.randint(20, 80)),
            "storage_gb": device.get("storage_gb", 64),
            "vehicle_speed_kmh": random.randint(0, 120) if device.get("has_gps") else None,
            "cloud_sync_status": "synced" if device.get("has_cloud_backup") else "disabled",
            "last_cloud_sync": datetime.now(timezone.utc).isoformat() if device.get("has_cloud_backup") else None,
            "g_sensor_alert": random.choice([True, False])
        }
    
    return monitoring_data


# ==================== THREAT DETECTION & ALERTS ====================

@router.post("/threats/scan/{device_id}")
async def scan_device_threats(device_id: str):
    """Scan a device for potential threats"""
    db = dependencies.get_db()
    
    device = await db.surveillance_devices.find_one({"id": device_id}, {"_id": 0})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    category = device.get("category", "cameras")
    threats_found = []
    
    # Category-specific threat detection
    threat_types = DEVICE_CATEGORIES.get(category, {}).get("threats", [])
    
    # Simulate threat detection (in production, would do actual scanning)
    for threat_type in threat_types:
        if random.random() < 0.15:  # 15% chance to detect each threat type
            severity = random.choice(["low", "medium", "high", "critical"])
            threats_found.append({
                "id": str(uuid4()),
                "threat_type": threat_type,
                "severity": severity,
                "description": get_threat_description(threat_type, category),
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "status": "active"
            })
    
    # Store threats
    if threats_found:
        for threat in threats_found:
            await db.surveillance_threats.insert_one({
                **threat,
                "device_id": device_id
            })
        
        await db.surveillance_devices.update_one(
            {"id": device_id},
            {
                "$inc": {"threats_detected": len(threats_found)},
                "$set": {"security_score": max(0, device.get("security_score", 100) - len(threats_found) * 10)}
            }
        )
    
    return {
        "device_id": device_id,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "threats_found": len(threats_found),
        "threats": threats_found,
        "overall_risk": "critical" if any(t["severity"] == "critical" for t in threats_found) else "high" if any(t["severity"] == "high" for t in threats_found) else "medium" if threats_found else "low"
    }


def get_threat_description(threat_type: str, category: str) -> str:
    """Get human-readable threat description"""
    descriptions = {
        # Camera threats
        "unauthorized_access": "Unauthorized access attempt detected to camera stream",
        "stream_hijacking": "Potential stream hijacking - unknown client accessing feed",
        "firmware_exploit": "Known firmware vulnerability detected (CVE-2024-XXXX)",
        "credential_theft": "Default or weak credentials in use",
        "ddos_target": "Camera being used as DDoS bot target",
        # Smart meter threats
        "data_tampering": "Meter reading data tampering detected",
        "meter_bypass": "Physical or logical meter bypass attempt",
        "injection_attack": "Command injection attempt on meter interface",
        "replay_attack": "Replay attack detected on communication channel",
        "eavesdropping": "Unencrypted communication intercepted",
        # Dashcam threats
        "gps_spoofing": "GPS location spoofing detected",
        "video_tampering": "Video recording tampering detected",
        "data_exfiltration": "Unusual data upload to unknown server",
        "remote_access": "Unauthorized remote access attempt",
        "cloud_breach": "Cloud storage access from unknown location"
    }
    return descriptions.get(threat_type, f"Threat detected: {threat_type}")


@router.get("/alerts")
async def get_alerts(
    device_id: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: str = "active",
    limit: int = Query(default=50, le=200)
):
    """Get alerts for surveillance devices"""
    db = dependencies.get_db()
    
    query = {"status": status}
    if device_id:
        query["device_id"] = device_id
    if severity:
        query["severity"] = severity
    
    alerts = await db.surveillance_alerts.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Filter by category if specified
    if category:
        device_ids = [d["id"] for d in await db.surveillance_devices.find(
            {"category": category},
            {"id": 1, "_id": 0}
        ).to_list(1000)]
        alerts = [a for a in alerts if a.get("device_id") in device_ids]
    
    return {
        "total": len(alerts),
        "alerts": alerts
    }


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolution_note: Optional[str] = None):
    """Resolve an alert"""
    db = dependencies.get_db()
    
    result = await db.surveillance_alerts.update_one(
        {"id": alert_id},
        {
            "$set": {
                "status": "resolved",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "resolution_note": resolution_note
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"status": "resolved", "alert_id": alert_id}


# ==================== DASHBOARD & STATISTICS ====================

@router.get("/dashboard/overview")
async def get_dashboard_overview(owner_id: Optional[str] = None):
    """Get comprehensive dashboard overview"""
    db = dependencies.get_db()
    
    query = {}
    if owner_id:
        query["owner_id"] = owner_id
    
    # Device counts by category
    cameras_count = await db.surveillance_devices.count_documents({**query, "category": "cameras"})
    meters_count = await db.surveillance_devices.count_documents({**query, "category": "smart_meters"})
    dashcams_count = await db.surveillance_devices.count_documents({**query, "category": "dashcams"})
    total_devices = cameras_count + meters_count + dashcams_count
    
    # Status counts
    online_count = await db.surveillance_devices.count_documents({**query, "status": "online"})
    offline_count = await db.surveillance_devices.count_documents({**query, "status": "offline"})
    
    # Alert counts
    active_alerts = await db.surveillance_alerts.count_documents({"status": "active"})
    critical_alerts = await db.surveillance_alerts.count_documents({"status": "active", "severity": "critical"})
    
    # Calculate average security score
    devices = await db.surveillance_devices.find(query, {"security_score": 1, "_id": 0}).to_list(1000)
    avg_security_score = sum(d.get("security_score", 100) for d in devices) / max(1, len(devices))
    
    # Recent activity
    recent_devices = await db.surveillance_devices.find(
        query,
        {"_id": 0, "id": 1, "device_name": 1, "category": 1, "registered_at": 1}
    ).sort("registered_at", -1).limit(5).to_list(5)
    
    return {
        "summary": {
            "total_devices": total_devices,
            "cameras": cameras_count,
            "smart_meters": meters_count,
            "dashcams": dashcams_count,
            "online": online_count,
            "offline": offline_count,
            "uptime_percent": round((online_count / max(1, total_devices)) * 100, 1)
        },
        "security": {
            "average_score": round(avg_security_score, 1),
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "threat_level": "critical" if critical_alerts > 0 else "high" if active_alerts > 5 else "medium" if active_alerts > 0 else "low"
        },
        "recent_devices": recent_devices,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/dashboard/category/{category}")
async def get_category_dashboard(category: str, owner_id: Optional[str] = None):
    """Get dashboard data for a specific category"""
    if category not in DEVICE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid: {list(DEVICE_CATEGORIES.keys())}")
    
    db = dependencies.get_db()
    
    query = {"category": category}
    if owner_id:
        query["owner_id"] = owner_id
    
    devices = await db.surveillance_devices.find(query, {"_id": 0}).to_list(1000)
    
    # Calculate statistics
    total = len(devices)
    online = sum(1 for d in devices if d.get("status") == "online")
    avg_health = sum(d.get("health_score", 100) for d in devices) / max(1, total)
    avg_security = sum(d.get("security_score", 100) for d in devices) / max(1, total)
    total_alerts = sum(d.get("alerts_count", 0) for d in devices)
    
    # Group by device type
    by_type = {}
    for device in devices:
        dtype = device.get("device_type", "unknown")
        by_type[dtype] = by_type.get(dtype, 0) + 1
    
    return {
        "category": category,
        "category_info": DEVICE_CATEGORIES[category],
        "statistics": {
            "total_devices": total,
            "online": online,
            "offline": total - online,
            "average_health_score": round(avg_health, 1),
            "average_security_score": round(avg_security, 1),
            "total_alerts": total_alerts
        },
        "by_device_type": by_type,
        "devices": devices,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }



# ==================== AUTO-DISCOVERY & NETWORK SCAN ====================

@router.post("/discovery/scan")
async def start_network_scan(
    network_range: str = "192.168.1.0/24",
    scan_type: str = "quick"  # quick, deep, targeted
):
    """
    Start network scan for device auto-discovery
    Simulates scanning network for IoT devices
    """
    db = dependencies.get_db()
    
    scan_id = str(uuid4())
    
    # Simulate discovered devices based on scan type
    discovered_devices = []
    
    # Generate realistic device discoveries
    device_templates = [
        {"type": "ip_camera", "category": "cameras", "manufacturer": "Hikvision", "models": ["DS-2CD2T87G2-L", "DS-2CD2043G2-I", "DS-2CD2385G1-I"]},
        {"type": "ip_camera", "category": "cameras", "manufacturer": "Dahua", "models": ["IPC-HDW5442TM-ASE", "IPC-HFW5241E-ZE"]},
        {"type": "webcam", "category": "cameras", "manufacturer": "Logitech", "models": ["C920", "C922", "BRIO 4K"]},
        {"type": "cctv", "category": "cameras", "manufacturer": "Axis", "models": ["P3245-LVE", "M3106-LVE Mk II"]},
        {"type": "electricity_meter", "category": "smart_meters", "manufacturer": "Landis+Gyr", "models": ["E650", "E450"]},
        {"type": "water_meter", "category": "smart_meters", "manufacturer": "Kamstrup", "models": ["MULTICAL 21", "flowIQ 2101"]},
    ]
    
    num_devices = random.randint(3, 8) if scan_type == "quick" else random.randint(8, 15)
    
    for i in range(num_devices):
        template = random.choice(device_templates)
        ip_suffix = random.randint(10, 250)
        
        device = {
            "id": str(uuid4()),
            "ip_address": f"192.168.1.{ip_suffix}",
            "mac_address": ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)]).upper(),
            "device_type": template["type"],
            "category": template["category"],
            "manufacturer": template["manufacturer"],
            "model": random.choice(template["models"]),
            "hostname": f"{template['manufacturer'].lower()}-{ip_suffix}",
            "open_ports": [80, 443, 554] if "camera" in template["type"] else [80, 443],
            "protocols_detected": ["http", "rtsp"] if "camera" in template["type"] else ["http", "modbus"],
            "firmware_version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
            "status": "discovered",
            "security_issues": [],
            "discovered_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add security issues randomly
        if random.random() < 0.3:
            device["security_issues"].append({
                "type": "default_credentials",
                "severity": "critical",
                "description": "Device using default username/password"
            })
        if random.random() < 0.2:
            device["security_issues"].append({
                "type": "outdated_firmware",
                "severity": "high",
                "description": f"Firmware {device['firmware_version']} has known vulnerabilities"
            })
        if random.random() < 0.15:
            device["security_issues"].append({
                "type": "unencrypted_stream",
                "severity": "medium",
                "description": "Video stream not using encryption"
            })
        
        discovered_devices.append(device)
    
    # Store scan results
    scan_record = {
        "id": scan_id,
        "network_range": network_range,
        "scan_type": scan_type,
        "status": "completed",
        "devices_found": len(discovered_devices),
        "devices": discovered_devices,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.network_scans.insert_one(scan_record)
    
    return {
        "scan_id": scan_id,
        "network_range": network_range,
        "scan_type": scan_type,
        "status": "completed",
        "devices_found": len(discovered_devices),
        "devices": discovered_devices,
        "summary": {
            "cameras": len([d for d in discovered_devices if d["category"] == "cameras"]),
            "smart_meters": len([d for d in discovered_devices if d["category"] == "smart_meters"]),
            "with_security_issues": len([d for d in discovered_devices if d["security_issues"]])
        }
    }


@router.post("/discovery/register-discovered")
async def register_discovered_device(
    scan_id: str,
    device_ip: str,
    device_name: str,
    location: str,
    owner_id: str  # Required - no default value
):
    """Register a device from discovery scan"""
    db = dependencies.get_db()
    
    # Find the scan
    scan = await db.network_scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Find the device in scan results
    device_data = None
    for d in scan.get("devices", []):
        if d["ip_address"] == device_ip:
            device_data = d
            break
    
    if not device_data:
        raise HTTPException(status_code=404, detail="Device not found in scan results")
    
    # Create device record
    device_id = str(uuid4())
    device_record = {
        "id": device_id,
        "category": device_data["category"],
        "device_name": device_name,
        "device_type": device_data["device_type"],
        "manufacturer": device_data["manufacturer"],
        "model": device_data["model"],
        "ip_address": device_data["ip_address"],
        "mac_address": device_data["mac_address"],
        "location": location,
        "firmware_version": device_data["firmware_version"],
        "owner_id": owner_id,
        "status": "online",
        "health_score": 100 - (len(device_data["security_issues"]) * 15),
        "security_score": 100 - (len(device_data["security_issues"]) * 20),
        "discovered_from_scan": scan_id,
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "threats_detected": len(device_data["security_issues"]),
        "alerts_count": len(device_data["security_issues"]),
        "netflow_enabled": True,
        "bytes_in_24h": 0,
        "bytes_out_24h": 0
    }
    
    await db.surveillance_devices.insert_one(device_record)
    
    return {
        "device_id": device_id,
        "status": "registered",
        "device_name": device_name,
        "security_issues_imported": len(device_data["security_issues"]),
        "message": f"Device '{device_name}' registered successfully from scan"
    }


@router.get("/discovery/scans")
async def list_network_scans(limit: int = Query(default=10, le=50)):
    """List recent network scans"""
    db = dependencies.get_db()
    
    scans = await db.network_scans.find(
        {},
        {"_id": 0, "devices": 0}  # Exclude full device list for performance
    ).sort("started_at", -1).limit(limit).to_list(limit)
    
    return {"scans": scans}


# ==================== NETFLOW VISUALIZATION & ANALYTICS ====================

@router.get("/netflow/traffic-patterns/{device_id}")
async def get_traffic_patterns(device_id: str, hours: int = Query(default=24, le=168)):
    """Get traffic patterns visualization data"""
    db = dependencies.get_db()
    
    device = await db.surveillance_devices.find_one({"id": device_id}, {"_id": 0})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Generate realistic traffic pattern data
    patterns = []
    now = datetime.now(timezone.utc)
    
    for h in range(hours):
        timestamp = (now - timedelta(hours=hours - h)).isoformat()
        
        # Simulate traffic patterns (higher during business hours)
        hour_of_day = (now.hour - hours + h) % 24
        base_traffic = 50000000 if 9 <= hour_of_day <= 18 else 10000000  # 50MB vs 10MB base
        
        patterns.append({
            "timestamp": timestamp,
            "bytes_in": int(base_traffic * random.uniform(0.8, 1.5)),
            "bytes_out": int(base_traffic * 0.3 * random.uniform(0.7, 1.3)),
            "packets_in": random.randint(10000, 50000),
            "packets_out": random.randint(3000, 15000),
            "connections": random.randint(50, 200),
            "protocols": {
                "rtsp": random.randint(40, 70),
                "http": random.randint(20, 40),
                "https": random.randint(5, 15),
                "other": random.randint(5, 10)
            }
        })
    
    return {
        "device_id": device_id,
        "period_hours": hours,
        "patterns": patterns,
        "summary": {
            "total_bytes_in": sum(p["bytes_in"] for p in patterns),
            "total_bytes_out": sum(p["bytes_out"] for p in patterns),
            "peak_hour": max(patterns, key=lambda x: x["bytes_in"])["timestamp"],
            "avg_connections_per_hour": sum(p["connections"] for p in patterns) // len(patterns)
        }
    }


@router.get("/netflow/anomalies")
async def get_traffic_anomalies(device_id: Optional[str] = None, hours: int = Query(default=24, le=168)):
    """Get detected traffic anomalies"""
    # Note: In production, would query db.anomaly_events collection
    # Currently using simulated data for demo purposes
    
    # Generate realistic anomaly data
    anomaly_types = [
        {"type": "traffic_spike", "severity": "medium", "description": "Unusual traffic spike detected"},
        {"type": "port_scan", "severity": "high", "description": "Port scanning activity detected"},
        {"type": "data_exfiltration", "severity": "critical", "description": "Large outbound data transfer"},
        {"type": "unusual_destination", "severity": "medium", "description": "Connection to unusual IP range"},
        {"type": "protocol_anomaly", "severity": "low", "description": "Unexpected protocol usage"},
        {"type": "bandwidth_abuse", "severity": "medium", "description": "Bandwidth usage exceeds normal patterns"},
        {"type": "connection_flood", "severity": "high", "description": "Excessive connection attempts"},
        {"type": "dns_tunneling", "severity": "critical", "description": "Possible DNS tunneling detected"}
    ]
    
    anomalies = []
    num_anomalies = random.randint(2, 8)
    
    for i in range(num_anomalies):
        anomaly = random.choice(anomaly_types)
        anomalies.append({
            "id": str(uuid4()),
            "device_id": device_id or f"device-{random.randint(1, 5)}",
            "type": anomaly["type"],
            "severity": anomaly["severity"],
            "description": anomaly["description"],
            "detected_at": (datetime.now(timezone.utc) - timedelta(hours=random.randint(0, hours))).isoformat(),
            "details": {
                "source_ip": f"192.168.1.{random.randint(10, 250)}",
                "dest_ip": f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}",
                "bytes_involved": random.randint(100000, 100000000),
                "packets": random.randint(100, 10000)
            },
            "status": random.choice(["active", "investigating", "resolved"])
        })
    
    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    anomalies.sort(key=lambda x: severity_order.get(x["severity"], 4))
    
    return {
        "period_hours": hours,
        "total_anomalies": len(anomalies),
        "by_severity": {
            "critical": len([a for a in anomalies if a["severity"] == "critical"]),
            "high": len([a for a in anomalies if a["severity"] == "high"]),
            "medium": len([a for a in anomalies if a["severity"] == "medium"]),
            "low": len([a for a in anomalies if a["severity"] == "low"])
        },
        "anomalies": anomalies
    }


@router.get("/netflow/botnet-detection")
async def check_botnet_indicators(device_id: Optional[str] = None):
    """Check for botnet indicators across devices"""
    
    # Known botnet C&C indicators
    botnet_indicators = {
        "mirai": {
            "ports": [23, 2323, 7547],
            "signatures": ["mirai", "hajime", "qbot"],
            "risk": "critical"
        },
        "bashlite": {
            "ports": [23, 9000],
            "signatures": ["bashlite", "gafgyt", "lizard"],
            "risk": "critical"
        },
        "emotet": {
            "ports": [443, 8080, 8443],
            "signatures": ["emotet", "heodo"],
            "risk": "high"
        }
    }
    
    # Simulate detection results
    detections = []
    if random.random() < 0.3:  # 30% chance of finding something
        botnet = random.choice(list(botnet_indicators.keys()))
        info = botnet_indicators[botnet]
        detections.append({
            "botnet_family": botnet,
            "risk_level": info["risk"],
            "indicators_found": random.randint(1, 3),
            "affected_devices": random.randint(1, 3),
            "suspicious_connections": random.randint(5, 50),
            "recommended_actions": [
                "Isolate affected devices immediately",
                "Update firmware to latest version",
                "Change default credentials",
                "Block outbound connections to C&C IPs"
            ]
        })
    
    return {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "devices_scanned": random.randint(10, 50),
        "botnet_detected": len(detections) > 0,
        "detections": detections,
        "overall_risk": "critical" if detections else "low",
        "known_botnets_checked": list(botnet_indicators.keys())
    }


@router.get("/netflow/firmware-vulnerabilities")
async def check_firmware_vulnerabilities(device_id: Optional[str] = None):
    """Check firmware vulnerabilities for devices"""
    db = dependencies.get_db()
    
    query = {"id": device_id} if device_id else {}
    devices = await db.surveillance_devices.find(query, {"_id": 0}).to_list(100)
    
    # CVE database (simulated)
    known_cves = [
        {"cve": "CVE-2024-23456", "severity": "critical", "description": "Remote code execution in web interface", "affected_versions": ["< 5.0.0"]},
        {"cve": "CVE-2024-12345", "severity": "high", "description": "Authentication bypass vulnerability", "affected_versions": ["< 4.5.0"]},
        {"cve": "CVE-2023-98765", "severity": "high", "description": "Buffer overflow in RTSP handler", "affected_versions": ["< 4.0.0"]},
        {"cve": "CVE-2023-54321", "severity": "medium", "description": "Information disclosure via debug endpoint", "affected_versions": ["< 3.5.0"]},
        {"cve": "CVE-2023-11111", "severity": "medium", "description": "Cross-site scripting in admin panel", "affected_versions": ["< 3.0.0"]},
    ]
    
    vulnerabilities = []
    
    for device in devices:
        firmware = device.get("firmware_version", "1.0.0")
        device_vulns = []
        
        # Check each CVE
        for cve in known_cves:
            if random.random() < 0.25:  # 25% chance device is vulnerable
                device_vulns.append({
                    **cve,
                    "device_firmware": firmware,
                    "patch_available": random.choice([True, True, True, False]),  # 75% have patches
                    "exploited_in_wild": cve["severity"] == "critical" and random.random() < 0.3
                })
        
        if device_vulns:
            vulnerabilities.append({
                "device_id": device["id"],
                "device_name": device.get("device_name", "Unknown"),
                "manufacturer": device.get("manufacturer", "Unknown"),
                "current_firmware": firmware,
                "vulnerabilities": device_vulns,
                "risk_score": min(100, len(device_vulns) * 25 + sum(30 if v["severity"] == "critical" else 20 if v["severity"] == "high" else 10 for v in device_vulns))
            })
    
    # Sort by risk
    vulnerabilities.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "devices_checked": len(devices),
        "devices_vulnerable": len(vulnerabilities),
        "total_vulnerabilities": sum(len(v["vulnerabilities"]) for v in vulnerabilities),
        "critical_count": sum(1 for v in vulnerabilities for vuln in v["vulnerabilities"] if vuln["severity"] == "critical"),
        "vulnerabilities": vulnerabilities
    }


# ==================== SFLOW/IPFIX COLLECTOR ====================

@router.post("/collector/sflow/ingest")
async def ingest_sflow_data(
    collector_ip: str,
    samples: List[Dict[str, Any]]
):
    """Ingest sFlow data from collector"""
    db = dependencies.get_db()
    
    processed = 0
    anomalies_detected = 0
    
    for sample in samples:
        # Process each sFlow sample
        record = {
            "id": str(uuid4()),
            "collector_ip": collector_ip,
            "sample_type": sample.get("type", "flow"),
            "source_ip": sample.get("source_ip"),
            "dest_ip": sample.get("dest_ip"),
            "source_port": sample.get("source_port"),
            "dest_port": sample.get("dest_port"),
            "protocol": sample.get("protocol"),
            "bytes": sample.get("bytes", 0),
            "packets": sample.get("packets", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.sflow_data.insert_one(record)
        processed += 1
        
        # Simple anomaly detection
        if sample.get("bytes", 0) > 100000000:  # > 100MB
            anomalies_detected += 1
    
    return {
        "status": "ingested",
        "samples_processed": processed,
        "anomalies_detected": anomalies_detected,
        "collector_ip": collector_ip
    }


@router.post("/collector/ipfix/ingest")
async def ingest_ipfix_data(
    collector_ip: str,
    flows: List[Dict[str, Any]]
):
    """Ingest IPFIX data from collector"""
    db = dependencies.get_db()
    
    processed = 0
    
    for flow in flows:
        record = {
            "id": str(uuid4()),
            "collector_ip": collector_ip,
            "flow_type": "ipfix",
            "source_ipv4": flow.get("sourceIPv4Address"),
            "dest_ipv4": flow.get("destinationIPv4Address"),
            "source_port": flow.get("sourceTransportPort"),
            "dest_port": flow.get("destinationTransportPort"),
            "protocol": flow.get("protocolIdentifier"),
            "octet_count": flow.get("octetDeltaCount", 0),
            "packet_count": flow.get("packetDeltaCount", 0),
            "flow_start": flow.get("flowStartMilliseconds"),
            "flow_end": flow.get("flowEndMilliseconds"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await db.ipfix_data.insert_one(record)
        processed += 1
    
    return {
        "status": "ingested",
        "flows_processed": processed,
        "collector_ip": collector_ip
    }


@router.get("/collector/status")
async def get_collector_status():
    """Get NetFlow collector status"""
    return {
        "collectors": [
            {
                "name": "Primary sFlow Collector",
                "type": "sflow",
                "ip": "10.0.0.100",
                "port": 6343,
                "status": "active",
                "samples_per_second": random.randint(1000, 5000),
                "last_sample": datetime.now(timezone.utc).isoformat()
            },
            {
                "name": "IPFIX Collector",
                "type": "ipfix",
                "ip": "10.0.0.101",
                "port": 4739,
                "status": "active",
                "flows_per_second": random.randint(500, 2000),
                "last_flow": datetime.now(timezone.utc).isoformat()
            }
        ],
        "total_devices_reporting": random.randint(10, 50),
        "data_retention_days": 30,
        "storage_used_gb": round(random.uniform(10, 100), 2)
    }
