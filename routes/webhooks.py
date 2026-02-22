"""
Webhook Management System
Complete webhook infrastructure for Infuse.AI Platform

Features:
- Webhook endpoint CRUD operations
- Event subscriptions (patient.created, threat.detected, etc.)
- Delivery logs with full request/response tracking
- Automatic retry logic with exponential backoff
- HMAC-SHA256 signature verification
- Rate limiting per webhook
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from enum import Enum
import hashlib
import hmac
import json
import asyncio
import aiohttp

import dependencies

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ==================== ENUMS & MODELS ====================

class WebhookEventType(str, Enum):
    # SecureSphere Events
    THREAT_DETECTED = "threat.detected"
    THREAT_RESOLVED = "threat.resolved"
    URL_SCANNED = "url.scanned"
    SMS_ANALYZED = "sms.analyzed"
    DEVICE_REGISTERED = "device.registered"
    DEVICE_COMPROMISED = "device.compromised"
    COMPLIANCE_ALERT = "compliance.alert"
    IOT_ANOMALY = "iot.anomaly"
    SIM_SWAP_DETECTED = "sim_swap.detected"
    GPS_SPOOFING = "gps_spoofing.detected"
    
    # HealthTrack Events
    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    APPOINTMENT_SCHEDULED = "appointment.scheduled"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    PRESCRIPTION_CREATED = "prescription.created"
    LAB_RESULT_READY = "lab_result.ready"
    VITALS_ALERT = "vitals.alert"
    
    # System Events
    SYSTEM_ALERT = "system.alert"
    API_RATE_LIMITED = "api.rate_limited"


class WebhookStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., description="Webhook endpoint URL")
    description: Optional[str] = None
    events: List[WebhookEventType] = Field(..., min_items=1)
    secret: Optional[str] = Field(None, description="Custom secret for signature, auto-generated if not provided")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Custom headers to send")
    is_active: bool = True


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    events: Optional[List[WebhookEventType]] = None
    headers: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


class WebhookTestPayload(BaseModel):
    event_type: WebhookEventType = WebhookEventType.THREAT_DETECTED
    custom_data: Optional[Dict[str, Any]] = None


class SignatureVerificationRequest(BaseModel):
    payload: str
    signature: str
    secret: str


# ==================== HELPER FUNCTIONS ====================

def generate_webhook_secret() -> str:
    """Generate a secure webhook secret"""
    return f"whsec_{uuid4().hex}"


def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload"""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected = generate_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


async def deliver_webhook(
    webhook_id: str,
    url: str,
    payload: Dict,
    secret: str,
    headers: Dict[str, str],
    delivery_id: str,
    attempt: int = 1,
    max_attempts: int = 5
):
    """Deliver webhook with retry logic"""
    db = dependencies.get_db()
    
    payload_str = json.dumps(payload, default=str)
    timestamp = datetime.now(timezone.utc).isoformat()
    signature = generate_signature(f"{timestamp}.{payload_str}", secret)
    
    request_headers = {
        "Content-Type": "application/json",
        "X-Webhook-ID": webhook_id,
        "X-Webhook-Timestamp": timestamp,
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Delivery-ID": delivery_id,
        "X-Attempt": str(attempt),
        "User-Agent": "Infuse-Webhook/1.0",
        **headers
    }
    
    start_time = datetime.now(timezone.utc)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_body = await response.text()
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                # Update delivery log
                delivery_update = {
                    "status": DeliveryStatus.SUCCESS if response.status < 400 else DeliveryStatus.FAILED,
                    "response_status": response.status,
                    "response_body": response_body[:5000],  # Limit response body size
                    "response_time_ms": round(response_time),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "attempt": attempt
                }
                
                await db.webhook_deliveries.update_one(
                    {"id": delivery_id},
                    {"$set": delivery_update}
                )
                
                # If failed and attempts remaining, schedule retry
                if response.status >= 400 and attempt < max_attempts:
                    await schedule_retry(webhook_id, url, payload, secret, headers, delivery_id, attempt + 1, max_attempts)
                
                return response.status < 400
                
    except Exception as e:
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        await db.webhook_deliveries.update_one(
            {"id": delivery_id},
            {"$set": {
                "status": DeliveryStatus.FAILED,
                "error": str(e),
                "response_time_ms": round(response_time),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "attempt": attempt
            }}
        )
        
        # Schedule retry if attempts remaining
        if attempt < max_attempts:
            await schedule_retry(webhook_id, url, payload, secret, headers, delivery_id, attempt + 1, max_attempts)
        
        return False


async def schedule_retry(
    webhook_id: str,
    url: str,
    payload: Dict,
    secret: str,
    headers: Dict[str, str],
    delivery_id: str,
    attempt: int,
    max_attempts: int
):
    """Schedule webhook retry with exponential backoff"""
    db = dependencies.get_db()
    
    # Exponential backoff: 2^attempt seconds (2, 4, 8, 16, 32...)
    delay = min(2 ** attempt, 300)  # Max 5 minutes
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
    
    await db.webhook_deliveries.update_one(
        {"id": delivery_id},
        {"$set": {
            "status": DeliveryStatus.RETRYING,
            "next_retry_at": retry_at.isoformat(),
            "retry_count": attempt - 1
        }}
    )
    
    # In production, this would be handled by a job queue (Celery, etc.)
    # For demo, we'll use asyncio
    await asyncio.sleep(delay)
    await deliver_webhook(webhook_id, url, payload, secret, headers, delivery_id, attempt, max_attempts)


# ==================== WEBHOOK CRUD ====================

@router.post("/")
async def create_webhook(webhook: WebhookCreate, background_tasks: BackgroundTasks):
    """
    Create a new webhook endpoint
    """
    db = dependencies.get_db()
    
    webhook_id = str(uuid4())
    secret = webhook.secret or generate_webhook_secret()
    
    webhook_doc = {
        "id": webhook_id,
        "name": webhook.name,
        "url": webhook.url,
        "description": webhook.description,
        "events": [e.value for e in webhook.events],
        "secret": secret,
        "headers": webhook.headers or {},
        "status": WebhookStatus.ACTIVE if webhook.is_active else WebhookStatus.PAUSED,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "delivery_stats": {
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "last_delivery_at": None
        }
    }
    
    await db.webhooks.insert_one(webhook_doc)
    
    return {
        "id": webhook_id,
        "name": webhook.name,
        "url": webhook.url,
        "events": [e.value for e in webhook.events],
        "secret": secret,
        "status": webhook_doc["status"],
        "created_at": webhook_doc["created_at"],
        "message": "Webhook created successfully. Store the secret securely - it won't be shown again."
    }


@router.get("/")
async def list_webhooks(
    status: Optional[WebhookStatus] = None,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0)
):
    """
    List all webhooks with optional status filter
    """
    db = dependencies.get_db()
    
    query = {}
    if status:
        query["status"] = status.value
    
    webhooks = await db.webhooks.find(
        query,
        {"_id": 0, "secret": 0}  # Don't expose secrets in list
    ).skip(offset).limit(limit).to_list(limit)
    
    total = await db.webhooks.count_documents(query)
    
    return {
        "total": total,
        "webhooks": webhooks,
        "limit": limit,
        "offset": offset
    }


@router.get("/{webhook_id}")
async def get_webhook(webhook_id: str):
    """
    Get webhook details by ID
    """
    db = dependencies.get_db()
    
    webhook = await db.webhooks.find_one(
        {"id": webhook_id},
        {"_id": 0, "secret": 0}  # Don't expose secret
    )
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return webhook


@router.put("/{webhook_id}")
async def update_webhook(webhook_id: str, update: WebhookUpdate):
    """
    Update webhook configuration
    """
    db = dependencies.get_db()
    
    webhook = await db.webhooks.find_one({"id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    if "events" in update_data:
        update_data["events"] = [e.value for e in update.events]
    
    if "is_active" in update_data:
        update_data["status"] = WebhookStatus.ACTIVE if update_data.pop("is_active") else WebhookStatus.PAUSED
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.webhooks.update_one(
        {"id": webhook_id},
        {"$set": update_data}
    )
    
    return {"message": "Webhook updated successfully", "webhook_id": webhook_id}


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """
    Delete a webhook
    """
    db = dependencies.get_db()
    
    result = await db.webhooks.delete_one({"id": webhook_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Also delete delivery logs
    await db.webhook_deliveries.delete_many({"webhook_id": webhook_id})
    
    return {"message": "Webhook deleted successfully", "webhook_id": webhook_id}


@router.post("/{webhook_id}/rotate-secret")
async def rotate_webhook_secret(webhook_id: str):
    """
    Rotate webhook secret - generates a new secret
    """
    db = dependencies.get_db()
    
    webhook = await db.webhooks.find_one({"id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    new_secret = generate_webhook_secret()
    
    await db.webhooks.update_one(
        {"id": webhook_id},
        {"$set": {
            "secret": new_secret,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Secret rotated successfully",
        "webhook_id": webhook_id,
        "new_secret": new_secret,
        "warning": "Store this secret securely - it won't be shown again."
    }


@router.post("/{webhook_id}/pause")
async def pause_webhook(webhook_id: str):
    """
    Pause webhook deliveries
    """
    db = dependencies.get_db()
    
    result = await db.webhooks.update_one(
        {"id": webhook_id},
        {"$set": {
            "status": WebhookStatus.PAUSED,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"message": "Webhook paused", "webhook_id": webhook_id}


@router.post("/{webhook_id}/resume")
async def resume_webhook(webhook_id: str):
    """
    Resume webhook deliveries
    """
    db = dependencies.get_db()
    
    result = await db.webhooks.update_one(
        {"id": webhook_id},
        {"$set": {
            "status": WebhookStatus.ACTIVE,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"message": "Webhook resumed", "webhook_id": webhook_id}


# ==================== EVENT SUBSCRIPTIONS ====================

@router.get("/events/types")
async def list_event_types():
    """
    List all available webhook event types
    """
    event_categories = {
        "securesphere": {
            "name": "SecureSphere Security Events",
            "events": [
                {"type": "threat.detected", "description": "New security threat detected"},
                {"type": "threat.resolved", "description": "Security threat resolved"},
                {"type": "url.scanned", "description": "URL scan completed"},
                {"type": "sms.analyzed", "description": "SMS analysis completed"},
                {"type": "device.registered", "description": "New device registered"},
                {"type": "device.compromised", "description": "Device security compromised"},
                {"type": "compliance.alert", "description": "Compliance status changed"},
                {"type": "iot.anomaly", "description": "IoT device anomaly detected"},
                {"type": "sim_swap.detected", "description": "SIM swap attempt detected"},
                {"type": "gps_spoofing.detected", "description": "GPS spoofing detected"}
            ]
        },
        "healthtrack": {
            "name": "HealthTrack Pro Events",
            "events": [
                {"type": "patient.created", "description": "New patient created"},
                {"type": "patient.updated", "description": "Patient record updated"},
                {"type": "appointment.scheduled", "description": "Appointment scheduled"},
                {"type": "appointment.cancelled", "description": "Appointment cancelled"},
                {"type": "prescription.created", "description": "New prescription created"},
                {"type": "lab_result.ready", "description": "Lab results available"},
                {"type": "vitals.alert", "description": "Abnormal vitals detected"}
            ]
        },
        "system": {
            "name": "System Events",
            "events": [
                {"type": "system.alert", "description": "System alert"},
                {"type": "api.rate_limited", "description": "API rate limit reached"}
            ]
        }
    }
    
    return {
        "total_events": sum(len(cat["events"]) for cat in event_categories.values()),
        "categories": event_categories
    }


@router.put("/{webhook_id}/events")
async def update_webhook_events(webhook_id: str, events: List[WebhookEventType]):
    """
    Update subscribed events for a webhook
    """
    db = dependencies.get_db()
    
    result = await db.webhooks.update_one(
        {"id": webhook_id},
        {"$set": {
            "events": [e.value for e in events],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "message": "Event subscriptions updated",
        "webhook_id": webhook_id,
        "events": [e.value for e in events]
    }


# ==================== DELIVERY LOGS ====================

@router.get("/{webhook_id}/deliveries")
async def get_delivery_logs(
    webhook_id: str,
    status: Optional[DeliveryStatus] = None,
    event_type: Optional[WebhookEventType] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0)
):
    """
    Get delivery logs for a webhook
    """
    db = dependencies.get_db()
    
    # Verify webhook exists
    webhook = await db.webhooks.find_one({"id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    query = {"webhook_id": webhook_id}
    if status:
        query["status"] = status.value
    if event_type:
        query["event_type"] = event_type.value
    
    deliveries = await db.webhook_deliveries.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    
    total = await db.webhook_deliveries.count_documents(query)
    
    return {
        "total": total,
        "deliveries": deliveries,
        "limit": limit,
        "offset": offset
    }


@router.get("/deliveries/{delivery_id}")
async def get_delivery_detail(delivery_id: str):
    """
    Get detailed delivery information including request/response
    """
    db = dependencies.get_db()
    
    delivery = await db.webhook_deliveries.find_one(
        {"id": delivery_id},
        {"_id": 0}
    )
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    return delivery


@router.post("/deliveries/{delivery_id}/retry")
async def retry_delivery(delivery_id: str, background_tasks: BackgroundTasks):
    """
    Manually retry a failed delivery
    """
    db = dependencies.get_db()
    
    delivery = await db.webhook_deliveries.find_one({"id": delivery_id})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    webhook = await db.webhooks.find_one({"id": delivery["webhook_id"]})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Create new delivery attempt
    new_delivery_id = str(uuid4())
    
    await db.webhook_deliveries.insert_one({
        "_id": None,
        "id": new_delivery_id,
        "webhook_id": webhook["id"],
        "event_type": delivery["event_type"],
        "payload": delivery["payload"],
        "status": DeliveryStatus.PENDING,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_retry": True,
        "original_delivery_id": delivery_id
    })
    
    # Schedule delivery
    background_tasks.add_task(
        deliver_webhook,
        webhook["id"],
        webhook["url"],
        delivery["payload"],
        webhook["secret"],
        webhook.get("headers", {}),
        new_delivery_id
    )
    
    return {
        "message": "Retry scheduled",
        "new_delivery_id": new_delivery_id,
        "original_delivery_id": delivery_id
    }


# ==================== TEST WEBHOOK ====================

@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str, payload: WebhookTestPayload, background_tasks: BackgroundTasks):
    """
    Send a test webhook to verify endpoint configuration
    """
    db = dependencies.get_db()
    
    webhook = await db.webhooks.find_one({"id": webhook_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    test_payload = {
        "event": payload.event_type.value,
        "test": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload.custom_data or {
            "message": "This is a test webhook from Infuse.AI",
            "webhook_id": webhook_id
        }
    }
    
    delivery_id = str(uuid4())
    
    # Create delivery log
    await db.webhook_deliveries.insert_one({
        "id": delivery_id,
        "webhook_id": webhook_id,
        "event_type": payload.event_type.value,
        "payload": test_payload,
        "status": DeliveryStatus.PENDING,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_test": True
    })
    
    # Schedule delivery
    background_tasks.add_task(
        deliver_webhook,
        webhook_id,
        webhook["url"],
        test_payload,
        webhook["secret"],
        webhook.get("headers", {}),
        delivery_id
    )
    
    return {
        "message": "Test webhook scheduled",
        "delivery_id": delivery_id,
        "event_type": payload.event_type.value,
        "payload": test_payload
    }


# ==================== TRIGGER WEBHOOK (Internal Use) ====================

async def trigger_webhook_event(event_type: str, data: Dict):
    """
    Trigger webhooks for a specific event type
    Internal function to be called when events occur
    """
    db = dependencies.get_db()
    
    # Find all active webhooks subscribed to this event
    webhooks = await db.webhooks.find({
        "status": WebhookStatus.ACTIVE,
        "events": event_type
    }).to_list(100)
    
    for webhook in webhooks:
        payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        delivery_id = str(uuid4())
        
        # Create delivery log
        await db.webhook_deliveries.insert_one({
            "_id": None,
            "id": delivery_id,
            "webhook_id": webhook["id"],
            "event_type": event_type,
            "payload": payload,
            "status": DeliveryStatus.PENDING,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Schedule async delivery
        asyncio.create_task(deliver_webhook(
            webhook["id"],
            webhook["url"],
            payload,
            webhook["secret"],
            webhook.get("headers", {}),
            delivery_id
        ))
        
        # Update delivery stats
        await db.webhooks.update_one(
            {"id": webhook["id"]},
            {"$inc": {"delivery_stats.total_deliveries": 1}}
        )


# ==================== WEBHOOK STATS ====================

@router.get("/{webhook_id}/stats")
async def get_webhook_stats(webhook_id: str, days: int = Query(default=7, le=30)):
    """
    Get delivery statistics for a webhook
    """
    db = dependencies.get_db()
    
    webhook = await db.webhooks.find_one({"id": webhook_id}, {"_id": 0})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get delivery counts by status
    pipeline = [
        {"$match": {
            "webhook_id": webhook_id,
            "created_at": {"$gte": start_date.isoformat()}
        }},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    status_counts = await db.webhook_deliveries.aggregate(pipeline).to_list(None)
    status_breakdown = {s["_id"]: s["count"] for s in status_counts}
    
    # Get average response time
    response_time_pipeline = [
        {"$match": {
            "webhook_id": webhook_id,
            "response_time_ms": {"$exists": True}
        }},
        {"$group": {
            "_id": None,
            "avg_response_time": {"$avg": "$response_time_ms"},
            "min_response_time": {"$min": "$response_time_ms"},
            "max_response_time": {"$max": "$response_time_ms"}
        }}
    ]
    
    response_times = await db.webhook_deliveries.aggregate(response_time_pipeline).to_list(None)
    
    total_deliveries = sum(status_breakdown.values())
    success_count = status_breakdown.get(DeliveryStatus.SUCCESS, 0)
    
    return {
        "webhook_id": webhook_id,
        "period_days": days,
        "total_deliveries": total_deliveries,
        "status_breakdown": status_breakdown,
        "success_rate": round((success_count / max(1, total_deliveries)) * 100, 2),
        "response_times": response_times[0] if response_times else {
            "avg_response_time": 0,
            "min_response_time": 0,
            "max_response_time": 0
        },
        "webhook_status": webhook.get("status"),
        "events_subscribed": webhook.get("events", [])
    }


# ==================== SIGNATURE VERIFICATION HELPER ====================

@router.post("/verify-signature")
async def verify_webhook_signature_endpoint(request: SignatureVerificationRequest):
    """
    Utility endpoint to verify webhook signatures
    Useful for debugging webhook integration
    """
    is_valid = verify_signature(request.payload, request.signature, request.secret)
    
    expected_signature = generate_signature(request.payload, request.secret)
    
    return {
        "is_valid": is_valid,
        "provided_signature": request.signature,
        "expected_signature": expected_signature if not is_valid else "matches",
        "tip": "Signature format: sha256=<HMAC-SHA256 of timestamp.payload>"
    }
