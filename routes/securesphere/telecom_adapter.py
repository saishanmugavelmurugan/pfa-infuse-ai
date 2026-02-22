"""
Telecom Adapter API - CSP Integration Layer
Part of SecureSphere Telecom Tier

Provides:
- Mock RAN interface for demo/testing
- Webhook endpoints for real telecom integration
- Adapter pattern for different telecom providers
"""

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
from uuid import uuid4
import hashlib

import dependencies

router = APIRouter(prefix="/securesphere/telecom", tags=["SecureSphere - Telecom Integration"])


# Supported Telecom Providers (Adapter Pattern)
SUPPORTED_PROVIDERS = {
    "airtel": {
        "name": "Airtel",
        "country": "India",
        "api_version": "v2",
        "supported_features": ["sms_filtering", "url_scanning", "subscriber_alerts"]
    },
    "jio": {
        "name": "Reliance Jio",
        "country": "India",
        "api_version": "v1",
        "supported_features": ["sms_filtering", "url_scanning", "volte_security"]
    },
    "vodafone": {
        "name": "Vodafone Idea",
        "country": "India",
        "api_version": "v1",
        "supported_features": ["sms_filtering", "subscriber_alerts"]
    },
    "bsnl": {
        "name": "BSNL",
        "country": "India",
        "api_version": "v1",
        "supported_features": ["sms_filtering"]
    },
    "generic": {
        "name": "Generic Provider",
        "country": "Global",
        "api_version": "v1",
        "supported_features": ["sms_filtering", "url_scanning"]
    }
}


class RANEvent(BaseModel):
    """RAN Network Event Structure"""
    event_type: str  # sms_intercept, url_request, data_transfer, voice_call
    subscriber_id: str  # MSISDN or IMSI (anonymized)
    timestamp: str
    payload: Dict
    metadata: Optional[Dict] = None


class ProviderConfig(BaseModel):
    """Telecom Provider Configuration"""
    provider_id: str
    api_key: str
    webhook_url: Optional[str] = None
    features_enabled: List[str]
    rate_limit: Optional[int] = 1000  # requests per minute


class IoTDeviceRegistration(BaseModel):
    """IoT Device Registration for CSP Programs"""
    device_imei: str
    device_type: str  # sensor, gateway, tracker, smart_meter, etc.
    subscriber_id: str
    provider_id: str
    security_profile: Optional[str] = "standard"  # standard, enhanced, critical


@router.get("/providers")
async def list_supported_providers():
    """
    List all supported telecom providers
    """
    return {
        "providers": SUPPORTED_PROVIDERS,
        "total": len(SUPPORTED_PROVIDERS)
    }


@router.post("/providers/configure")
async def configure_provider(config: ProviderConfig):
    """
    Configure a telecom provider integration
    """
    if config.provider_id not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider. Supported: {list(SUPPORTED_PROVIDERS.keys())}")
    
    db = dependencies.get_db()
    
    config_id = str(uuid4())
    config_record = {
        "id": config_id,
        "provider_id": config.provider_id,
        "api_key_hash": hashlib.sha256(config.api_key.encode()).hexdigest()[:16],
        "webhook_url": config.webhook_url,
        "features_enabled": config.features_enabled,
        "rate_limit": config.rate_limit,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.telecom_configs.insert_one(config_record)
    
    return {
        "config_id": config_id,
        "provider": SUPPORTED_PROVIDERS[config.provider_id]['name'],
        "status": "configured",
        "features_enabled": config.features_enabled,
        "message": "Provider configured successfully. Use the config_id for API calls."
    }


@router.post("/ran/event")
async def process_ran_event(event: RANEvent, x_provider_id: Optional[str] = Header(None)):
    """
    Process RAN network event
    This is the main webhook for receiving network events from telecom providers
    """
    from services.securesphere.ai_security_agent import security_agent
    
    db = dependencies.get_db()
    event_id = str(uuid4())
    
    # Process based on event type
    result = {
        "event_id": event_id,
        "event_type": event.event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "allowed",
        "threat_detected": False
    }
    
    if event.event_type == "sms_intercept":
        # Analyze SMS content for fraud
        sms_content = event.payload.get('content', '')
        sender = event.payload.get('sender', '')
        
        analysis = await security_agent.analyze_sms(sms_content, sender)
        
        if analysis.get('is_fraud') or analysis.get('risk_score', 0) > 70:
            result['action'] = "blocked"
            result['threat_detected'] = True
            result['threat_details'] = {
                "type": "fraudulent_sms",
                "risk_score": analysis.get('risk_score'),
                "fraud_type": analysis.get('fraud_type')
            }
    
    elif event.event_type == "url_request":
        # Analyze URL for threats
        url = event.payload.get('url', '')
        
        analysis = await security_agent.analyze_url(url)
        
        if analysis.get('risk_score', 0) > 60:
            result['action'] = "blocked"
            result['threat_detected'] = True
            result['threat_details'] = {
                "type": "malicious_url",
                "risk_score": analysis.get('risk_score'),
                "category": analysis.get('category')
            }
    
    elif event.event_type == "data_transfer":
        # Analyze data transfer patterns
        data_size = event.payload.get('size_bytes', 0)
        destination = event.payload.get('destination', '')
        
        # Flag large transfers to suspicious destinations
        if data_size > 100000000:  # > 100MB
            result['action'] = "flagged"
            result['threat_details'] = {
                "type": "large_data_transfer",
                "size_bytes": data_size
            }
    
    # Store event for analysis
    event_record = {
        "id": event_id,
        "provider_id": x_provider_id or "unknown",
        "event": event.dict(),
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.ran_events.insert_one(event_record)
    
    return result


@router.post("/ran/simulate")
async def simulate_ran_event(event_type: str, count: int = Query(default=1, le=10)):
    """
    Simulate RAN events for testing (Demo mode)
    """
    import random
    
    simulated_events = []
    
    for _ in range(count):
        if event_type == "sms_intercept":
            # Simulate different types of SMS
            sms_types = [
                {"content": "Your OTP is 123456. Do not share with anyone.", "sender": "HDFC-BK"},
                {"content": "Congratulations! You won Rs.50 lakhs. Click here to claim: bit.ly/fake", "sender": "PRIZE"},
                {"content": "Your account has been suspended. Verify now: http://fake-bank.com", "sender": "ALERT"},
                {"content": "Dear customer, your order #12345 has been shipped.", "sender": "AMAZON"},
                {"content": "Share your OTP to complete KYC update for your bank account", "sender": "+91987654321"}
            ]
            payload = random.choice(sms_types)
            
        elif event_type == "url_request":
            urls = [
                {"url": "https://www.google.com"},
                {"url": "http://fake-login-bank.xyz/verify"},
                {"url": "https://bit.ly/suspicious"},
                {"url": "https://www.amazon.in"},
                {"url": "http://192.168.1.1/admin"}
            ]
            payload = random.choice(urls)
            
        else:
            payload = {"type": event_type, "data": "simulated"}
        
        event = RANEvent(
            event_type=event_type,
            subscriber_id=f"MSISDN-{random.randint(1000000000, 9999999999)}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload
        )
        
        result = await process_ran_event(event, "simulation")
        simulated_events.append(result)
    
    return {
        "simulated": True,
        "count": count,
        "events": simulated_events
    }


@router.post("/iot/register")
async def register_iot_device(device: IoTDeviceRegistration):
    """
    Register an IoT device for CSP security program
    """
    db = dependencies.get_db()
    
    device_id = str(uuid4())
    device_record = {
        "id": device_id,
        "imei": device.device_imei,
        "imei_hash": hashlib.sha256(device.device_imei.encode()).hexdigest()[:16],
        "device_type": device.device_type,
        "subscriber_id": device.subscriber_id,
        "provider_id": device.provider_id,
        "security_profile": device.security_profile,
        "status": "active",
        "threat_score": 0,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat()
    }
    
    await db.iot_devices.insert_one(device_record)
    
    return {
        "device_id": device_id,
        "status": "registered",
        "security_profile": device.security_profile,
        "monitoring_enabled": True
    }


@router.get("/iot/devices")
async def list_iot_devices(
    provider_id: Optional[str] = None,
    device_type: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    List registered IoT devices
    """
    db = dependencies.get_db()
    
    query = {"status": "active"}
    if provider_id:
        query["provider_id"] = provider_id
    if device_type:
        query["device_type"] = device_type
    
    devices = await db.iot_devices.find(
        query,
        {"_id": 0, "imei": 0}  # Hide sensitive data
    ).limit(limit).to_list(limit)
    
    return {
        "total": len(devices),
        "devices": devices
    }


@router.get("/stats")
async def get_telecom_stats():
    """
    Get telecom integration statistics
    """
    db = dependencies.get_db()
    
    total_events = await db.ran_events.count_documents({})
    blocked_events = await db.ran_events.count_documents({"result.action": "blocked"})
    iot_devices = await db.iot_devices.count_documents({"status": "active"})
    
    # Events by type
    pipeline = [
        {"$group": {"_id": "$event.event_type", "count": {"$sum": 1}}}
    ]
    events_by_type = await db.ran_events.aggregate(pipeline).to_list(None)
    
    return {
        "total_events_processed": total_events,
        "threats_blocked": blocked_events,
        "iot_devices_protected": iot_devices,
        "events_by_type": {e['_id']: e['count'] for e in events_by_type if e['_id']},
        "block_rate": round((blocked_events / max(1, total_events)) * 100, 2),
        "providers_configured": len(SUPPORTED_PROVIDERS)
    }
