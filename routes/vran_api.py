"""
vRAN Integration API Routes
Complete threat detection system with all 4 segments
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import json
import csv
import io

# Import services
import sys
sys.path.append('/app/backend')
from services.vran_connector import vran_connector
from services.threat_engine import threat_engine
from services.bulk_processor import bulk_processor
from services.alert_service import alert_service

router = APIRouter(prefix="/api/vran", tags=["vRAN Integration"])

# ==================== Request/Response Models ====================

class MobileConnectionRequest(BaseModel):
    mobile_number: str = Field(..., description="Mobile number in E.164 format")
    segment: str = Field(..., description="telco, mobile, enterprise, automotive")
    user_id: str
    metadata: Optional[Dict[str, Any]] = None

class APNConnectionRequest(BaseModel):
    apn: str = Field(..., description="Access Point Name")
    segment: str
    user_id: str
    credentials: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

class ThreatAnalysisRequest(BaseModel):
    identifier: str
    segment: str
    connection_type: str = "mobile_number"
    additional_data: Optional[Dict[str, Any]] = None

class BulkUploadRequest(BaseModel):
    segment: str
    identifiers: List[Dict[str, Any]]
    priority: str = "normal"

class AlertConfigRequest(BaseModel):
    segment: str
    channels: List[str]  # in_app, email, sms, webhook
    severity_threshold: str = "medium"
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

# ==================== Connection Endpoints ====================

@router.post("/connect/mobile")
async def connect_via_mobile(request: MobileConnectionRequest):
    """
    Connect to vRAN using mobile number (MSISDN)
    Establishes monitoring session for threat detection
    """
    try:
        result = await vran_connector.connect_mobile_number(
            mobile_number=request.mobile_number,
            user_id=request.user_id,
            segment=request.segment,
            metadata=request.metadata
        )
        
        if result.get("success"):
            # Store connection in DB (would go to MongoDB)
            connection_record = {
                "id": str(uuid4()),
                "user_id": request.user_id,
                "segment": request.segment,
                "connection_type": "mobile_number",
                "identifier": request.mobile_number,
                "session_id": result.get("session_id"),
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return {
                "success": True,
                "connection": connection_record,
                "vran_info": result
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect/apn")
async def connect_via_apn(request: APNConnectionRequest):
    """
    Connect to vRAN using APN (Access Point Name)
    For enterprise and telco connections
    """
    try:
        result = await vran_connector.connect_apn(
            apn=request.apn,
            user_id=request.user_id,
            segment=request.segment,
            credentials=request.credentials,
            metadata=request.metadata
        )
        
        if result.get("success"):
            connection_record = {
                "id": str(uuid4()),
                "user_id": request.user_id,
                "segment": request.segment,
                "connection_type": "apn",
                "identifier": request.apn,
                "session_id": result.get("session_id"),
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return {
                "success": True,
                "connection": connection_record,
                "vran_info": result
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """Get vRAN session status"""
    result = await vran_connector.get_session_status(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Session not found")
    return result

@router.delete("/session/{session_id}")
async def disconnect_session(session_id: str):
    """Disconnect from vRAN session"""
    result = await vran_connector.disconnect(session_id)
    return result

# ==================== Threat Analysis Endpoints ====================

@router.post("/analyze")
async def analyze_threat(request: ThreatAnalysisRequest):
    """
    Analyze identifier for threats
    Returns: threat score, severity, recommended action
    """
    try:
        result = await threat_engine.analyze_identifier(
            identifier=request.identifier,
            segment=request.segment,
            connection_type=request.connection_type,
            additional_data=request.additional_data
        )
        
        # If threats found, trigger alerts
        if result.get("threat_detected"):
            await alert_service.send_alert(
                user_id=request.additional_data.get("user_id", "system") if request.additional_data else "system",
                threat_event=result,
                connection_id=request.identifier
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/batch")
async def analyze_batch(identifiers: List[ThreatAnalysisRequest]):
    """
    Analyze multiple identifiers in batch
    For real-time bulk scanning
    """
    results = []
    for req in identifiers[:100]:  # Limit to 100 per request
        try:
            result = await threat_engine.analyze_identifier(
                identifier=req.identifier,
                segment=req.segment,
                connection_type=req.connection_type,
                additional_data=req.additional_data
            )
            results.append(result)
        except Exception as e:
            results.append({
                "identifier": req.identifier,
                "error": str(e)
            })
    
    return {
        "total": len(results),
        "results": results
    }

# ==================== Bulk Processing Endpoints ====================

@router.post("/bulk/upload")
async def create_bulk_upload(request: BulkUploadRequest, user_id: str = "default"):
    """
    Create bulk upload job for processing millions of identifiers
    Returns job ID for tracking
    """
    try:
        result = await bulk_processor.create_bulk_job(
            user_id=user_id,
            segment=request.segment,
            identifiers=request.identifiers,
            priority=request.priority
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk/upload/file")
async def upload_bulk_file(
    file: UploadFile = File(...),
    segment: str = "mobile",
    user_id: str = "default"
):
    """
    Upload CSV/JSON file for bulk processing
    Supports large files with streaming
    """
    try:
        content = await file.read()
        identifiers = []
        
        if file.filename.endswith('.csv'):
            # Parse CSV
            reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            identifiers = list(reader)
        elif file.filename.endswith('.json'):
            # Parse JSON
            identifiers = json.loads(content.decode('utf-8'))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or JSON.")
        
        # Create bulk job
        result = await bulk_processor.create_bulk_job(
            user_id=user_id,
            segment=segment,
            identifiers=identifiers,
            priority="normal"
        )
        
        return {
            "success": True,
            "file_name": file.filename,
            "records_parsed": len(identifiers),
            "job": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bulk/job/{job_id}")
async def get_bulk_job_status(job_id: str):
    """Get bulk job status and progress"""
    result = await bulk_processor.get_job_status(job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/bulk/job/{job_id}/results")
async def get_bulk_job_results(job_id: str, page: int = 1, page_size: int = 100):
    """Get paginated results of a bulk job"""
    result = await bulk_processor.get_job_results(job_id, page, page_size)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/bulk/job/{job_id}/cancel")
async def cancel_bulk_job(job_id: str):
    """Cancel a running bulk job"""
    result = await bulk_processor.cancel_job(job_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/bulk/jobs")
async def list_bulk_jobs(user_id: str = "default", status: Optional[str] = None):
    """List all bulk jobs for a user"""
    jobs = await bulk_processor.get_all_jobs(user_id, status)
    return {"jobs": jobs}

# ==================== Alert Configuration Endpoints ====================

@router.post("/alerts/configure")
async def configure_alerts(request: AlertConfigRequest, user_id: str = "default"):
    """
    Configure alert preferences
    Channels: in_app, email, sms, webhook
    """
    result = await alert_service.configure_alerts(
        user_id=user_id,
        segment=request.segment,
        channels=request.channels,
        severity_threshold=request.severity_threshold,
        webhook_url=request.webhook_url,
        email=request.email,
        phone=request.phone
    )
    return result

@router.get("/alerts/config")
async def get_alert_config(user_id: str = "default"):
    """Get current alert configuration"""
    config = await alert_service.get_alert_config(user_id)
    if not config:
        return {"message": "No alert configuration found"}
    return {"config": config}

@router.get("/alerts/notifications")
async def get_notifications(user_id: str = "default", unread_only: bool = False):
    """Get user notifications"""
    notifications = await alert_service.get_user_notifications(user_id, unread_only)
    return {"notifications": notifications}

@router.post("/alerts/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user_id: str = "default"):
    """Mark notification as read"""
    result = await alert_service.mark_notification_read(notification_id, user_id)
    return result

@router.get("/alerts/history")
async def get_alert_history(user_id: str = "default", limit: int = 100):
    """Get alert history"""
    history = await alert_service.get_alert_history(user_id, limit)
    return {"alerts": history}

# ==================== AI Learning Endpoints ====================

@router.get("/ai/stats")
async def get_ai_learning_stats():
    """Get AI learning statistics"""
    stats = await threat_engine.get_learning_stats()
    return {"stats": stats}

@router.post("/ai/feedback/false-positive")
async def report_false_positive(identifier: str, threat_type: str):
    """Report a false positive to improve AI accuracy"""
    await threat_engine.report_false_positive(identifier, threat_type)
    return {"success": True, "message": "False positive reported. AI will learn from this."}

# ==================== Segment-Specific Endpoints ====================

# Telco Segment
@router.post("/telco/register")
async def register_telco_identifier(
    msisdn: Optional[str] = None,
    imsi: Optional[str] = None,
    apn: Optional[str] = None,
    network_code: Optional[str] = None,
    user_id: str = "default"
):
    """Register telco identifier for monitoring"""
    identifier = msisdn or imsi or apn
    if not identifier:
        raise HTTPException(status_code=400, detail="Provide msisdn, imsi, or apn")
    
    conn_type = "apn" if apn else "mobile_number"
    
    if conn_type == "apn":
        result = await vran_connector.connect_apn(apn, user_id, "telco")
    else:
        result = await vran_connector.connect_mobile_number(identifier, user_id, "telco")
    
    return {
        "segment": "telco",
        "identifier_type": conn_type,
        "connection": result
    }

# Mobile User Segment
@router.post("/mobile/register")
async def register_mobile_identifier(
    phone_number: Optional[str] = None,
    imei: Optional[str] = None,
    device_id: Optional[str] = None,
    user_id: str = "default"
):
    """Register mobile device for monitoring"""
    if not phone_number:
        return {"error": "phone_number parameter is required"}
    
    result = await vran_connector.connect_mobile_number(phone_number, user_id, "mobile")
    
    return {
        "segment": "mobile",
        "phone_number": phone_number,
        "imei": imei,
        "connection": result
    }

# Enterprise Segment
@router.post("/enterprise/register")
async def register_enterprise_identifier(
    ip_address: Optional[str] = None,
    domain: Optional[str] = None,
    apn: Optional[str] = None,
    user_id: str = "default"
):
    """Register enterprise endpoint for monitoring"""
    identifier = ip_address or domain or apn
    if not identifier:
        raise HTTPException(status_code=400, detail="Provide ip_address, domain, or apn")
    
    if apn:
        result = await vran_connector.connect_apn(apn, user_id, "enterprise")
    else:
        result = await vran_connector.connect_mobile_number(identifier, user_id, "enterprise")
    
    return {
        "segment": "enterprise",
        "identifier": identifier,
        "connection": result
    }

# Automotive Segment
@router.post("/automotive/register")
async def register_automotive_identifier(
    vin: Optional[str] = None,
    esim_iccid: Optional[str] = None,
    apn: Optional[str] = None,
    user_id: str = "default"
):
    """Register vehicle for monitoring"""
    if not vin and not apn:
        return {"error": "Provide vin or apn parameter"}
    
    identifier = apn or vin
    
    if apn:
        result = await vran_connector.connect_apn(apn, user_id, "automotive")
    else:
        result = await vran_connector.connect_mobile_number(vin, user_id, "automotive", {"vin": vin})
    
    return {
        "segment": "automotive",
        "vin": vin,
        "esim": esim_iccid,
        "connection": result
    }

# White Goods / IoT Segment
@router.post("/white-goods/register")
async def register_white_goods_identifier(
    device_id: Optional[str] = None,
    mac_address: Optional[str] = None,
    imei: Optional[str] = None,
    apn: Optional[str] = None,
    serial_number: Optional[str] = None,
    device_type: Optional[str] = None,
    manufacturer: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_id: str = "default"
):
    """Register IoT appliance / white goods for monitoring"""
    identifier = device_id or mac_address or imei or apn
    if not identifier:
        return {"error": "Provide device_id, mac_address, imei, or apn"}
    
    metadata = {
        "device_type": device_type,
        "manufacturer": manufacturer,
        "serial_number": serial_number,
        "ip_address": ip_address
    }
    
    if apn:
        result = await vran_connector.connect_apn(apn, user_id, "white_goods", metadata=metadata)
    else:
        result = await vran_connector.connect_mobile_number(identifier, user_id, "white_goods", metadata)
    
    return {
        "segment": "white_goods",
        "device_id": device_id,
        "mac_address": mac_address,
        "device_type": device_type,
        "connection": result
    }

# CCTV Segment
@router.post("/cctv/register")
async def register_cctv_identifier(
    camera_id: Optional[str] = None,
    camera_type: str = "private",  # public or private
    ip_address: Optional[str] = None,
    mac_address: Optional[str] = None,
    stream_url: Optional[str] = None,
    apn: Optional[str] = None,
    imei: Optional[str] = None,
    manufacturer: Optional[str] = None,
    location: Optional[str] = None,
    user_id: str = "default"
):
    """Register CCTV camera (public or private) for monitoring"""
    identifier = camera_id or ip_address or mac_address or apn
    if not identifier:
        return {"error": "Provide camera_id, ip_address, mac_address, or apn"}
    
    if camera_type not in ["public", "private"]:
        return {"error": "camera_type must be 'public' or 'private'"}
    
    metadata = {
        "camera_type": camera_type,
        "stream_url": stream_url,
        "manufacturer": manufacturer,
        "location": location,
        "ip_address": ip_address
    }
    
    if apn:
        result = await vran_connector.connect_apn(apn, user_id, "cctv", metadata=metadata)
    else:
        result = await vran_connector.connect_mobile_number(identifier, user_id, "cctv", metadata)
    
    return {
        "segment": "cctv",
        "camera_id": camera_id,
        "camera_type": camera_type,
        "location": location,
        "connection": result
    }

# CCTV Batch Registration (for multiple cameras)
@router.post("/cctv/register/batch")
async def register_cctv_batch(
    cameras: List[Dict[str, Any]],
    user_id: str = "default"
):
    """Register multiple CCTV cameras at once"""
    results = []
    for camera in cameras[:100]:  # Limit to 100 per batch
        try:
            identifier = camera.get("camera_id") or camera.get("ip_address") or camera.get("mac_address")
            if not identifier:
                results.append({"success": False, "error": "Missing identifier"})
                continue
            
            camera_type = camera.get("camera_type", "private")
            apn = camera.get("apn")
            
            if apn:
                result = await vran_connector.connect_apn(apn, user_id, "cctv", metadata=camera)
            else:
                result = await vran_connector.connect_mobile_number(identifier, user_id, "cctv", camera)
            
            results.append({
                "success": result.get("success", False),
                "camera_id": camera.get("camera_id"),
                "camera_type": camera_type,
                "session_id": result.get("session_id")
            })
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return {
        "total": len(results),
        "successful": len([r for r in results if r.get("success")]),
        "results": results
    }

# White Goods Batch Registration
@router.post("/white-goods/register/batch")
async def register_white_goods_batch(
    devices: List[Dict[str, Any]],
    user_id: str = "default"
):
    """Register multiple IoT devices at once"""
    results = []
    for device in devices[:100]:  # Limit to 100 per batch
        try:
            identifier = device.get("device_id") or device.get("mac_address") or device.get("imei")
            if not identifier:
                results.append({"success": False, "error": "Missing identifier"})
                continue
            
            apn = device.get("apn")
            
            if apn:
                result = await vran_connector.connect_apn(apn, user_id, "white_goods", metadata=device)
            else:
                result = await vran_connector.connect_mobile_number(identifier, user_id, "white_goods", device)
            
            results.append({
                "success": result.get("success", False),
                "device_id": device.get("device_id"),
                "device_type": device.get("device_type"),
                "session_id": result.get("session_id")
            })
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return {
        "total": len(results),
        "successful": len([r for r in results if r.get("success")]),
        "results": results
    }

# ==================== Dashboard Stats ====================

@router.get("/dashboard/stats")
async def get_dashboard_stats(user_id: str = "default"):
    """Get overall threat dashboard statistics"""
    ai_stats = await threat_engine.get_learning_stats()
    
    return {
        "total_active_sessions": len(vran_connector.active_sessions),
        "ai_stats": ai_stats,
        "threat_patterns_active": len(threat_engine.THREAT_PATTERNS),
        "external_feeds_connected": len(threat_engine.EXTERNAL_FEEDS),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
