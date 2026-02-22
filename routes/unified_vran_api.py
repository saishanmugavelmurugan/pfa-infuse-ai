"""
Unified vRAN API - Integrated Telco-Grade vRAN System
Provides a single interface for all vRAN operations with integrated components

This API unifies:
- vran_connector (Mobile/APN connections)
- threat_engine (AI threat analysis)
- telecom_adapter (CSP integration)
- gsm_fraud (SIM swap, OTP, Caller ID)
- ai_security_agent (AI analysis)
- ai_learning_agent (Continuous learning)
- enforcement_engine (Automated enforcement)
"""
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

from services.unified_vran_service import unified_vran_service, SelfProtectionPolicy

router = APIRouter(prefix="/api/unified-vran", tags=["Unified vRAN - Telco Grade"])


# ==================== Request Models ====================

class UnifiedConnectionRequest(BaseModel):
    identifier: str = Field(..., description="Mobile number, APN, IP, MAC, VIN, etc.")
    segment: str = Field(..., description="telco, mobile, enterprise, automotive, white_goods, cctv")
    connection_type: str = Field(default="mobile_number", description="mobile_number or apn")
    user_id: str = Field(default="default")
    metadata: Optional[Dict[str, Any]] = None

class BulkAnalysisRequest(BaseModel):
    identifiers: List[Dict[str, str]]
    segment: str
    user_id: str = "default"


# ==================== Self-Protection Status ====================

@router.get("/self-protection/status")
async def get_self_protection_status():
    """
    Get vRAN self-protection status
    NOTE: Self-protection is MANDATORY and cannot be disabled
    """
    return SelfProtectionPolicy.get_status()

@router.post("/self-protection/attempt-disable")
async def attempt_disable_self_protection():
    """
    Attempt to disable self-protection
    This will ALWAYS fail - self-protection is mandatory
    """
    return {
        "success": False,
        "error": "Self-protection cannot be disabled",
        "status": "mandatory",
        "message": "The vRAN self-protection policy is hardened and cannot be disabled. This is a security requirement for telco-grade operation."
    }


# ==================== Unified Connect & Analyze ====================

@router.post("/connect-analyze")
async def unified_connect_and_analyze(request: UnifiedConnectionRequest):
    """
    Unified connect and analyze endpoint
    
    Flow:
    1. Establish vRAN connection
    2. Run integrated threat analysis (multiple engines)
    3. Apply self-protection enforcement if needed
    4. Trigger AI learning
    5. Send alerts if threats detected
    
    Returns comprehensive results from all integrated components
    """
    try:
        result = await unified_vran_service.connect_and_analyze(
            identifier=request.identifier,
            segment=request.segment,
            connection_type=request.connection_type,
            user_id=request.user_id,
            metadata=request.metadata
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-batch")
async def analyze_batch(request: BulkAnalysisRequest):
    """
    Bulk analysis for multiple identifiers
    Uses integrated analysis pipeline
    """
    results = []
    
    for item in request.identifiers[:100]:  # Limit to 100
        try:
            result = await unified_vran_service.connect_and_analyze(
                identifier=item.get("identifier", ""),
                segment=request.segment,
                connection_type=item.get("connection_type", "mobile_number"),
                user_id=request.user_id,
                metadata=item.get("metadata")
            )
            results.append(result)
        except Exception as e:
            results.append({
                "success": False,
                "identifier": item.get("identifier"),
                "error": str(e)
            })
    
    return {
        "total": len(results),
        "successful": len([r for r in results if r.get("success")]),
        "results": results
    }


# ==================== Comprehensive Statistics ====================

@router.get("/stats/comprehensive")
async def get_comprehensive_stats():
    """
    Get comprehensive statistics from all integrated components
    """
    return unified_vran_service.get_comprehensive_stats()

@router.get("/stats/by-segment/{segment}")
async def get_segment_stats(segment: str):
    """
    Get statistics for a specific segment
    """
    all_stats = unified_vran_service.get_comprehensive_stats()
    segment_config = all_stats.get("segment_configs", {}).get(segment)
    
    if not segment_config:
        raise HTTPException(status_code=404, detail=f"Segment '{segment}' not found")
    
    # Count sessions for this segment
    segment_sessions = [
        s for s in unified_vran_service.sessions.values()
        if s.get("segment") == segment
    ]
    
    return {
        "segment": segment,
        "config": segment_config,
        "active_sessions": len(segment_sessions),
        "identifiers_supported": segment_config.get("identifiers", []),
        "actions_available": segment_config.get("actions", []),
        "features_enabled": segment_config.get("features", [])
    }


# ==================== Session Management ====================

@router.get("/sessions")
async def list_unified_sessions(
    segment: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """
    List unified vRAN sessions
    """
    sessions = list(unified_vran_service.sessions.values())
    
    if segment:
        sessions = [s for s in sessions if s.get("segment") == segment]
    
    return {
        "total": len(sessions),
        "sessions": sessions[:limit]
    }

@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str):
    """
    Get details of a specific unified session
    """
    session = unified_vran_service.sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session

@router.delete("/sessions/{session_id}")
async def terminate_session(session_id: str):
    """
    Terminate a unified vRAN session
    """
    if session_id not in unified_vran_service.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Also disconnect from vran_connector
    await unified_vran_service.vran_connector.disconnect(session_id)
    
    del unified_vran_service.sessions[session_id]
    
    return {"success": True, "message": f"Session {session_id} terminated"}


# ==================== Integration Status ====================

@router.get("/integration-status")
async def get_integration_status():
    """
    Get status of all integrated components
    """
    return {
        "unified_service": "active",
        "components": {
            "vran_connector": {
                "status": "active",
                "active_sessions": len(unified_vran_service.vran_connector.active_sessions)
            },
            "threat_engine": {
                "status": "active",
                "patterns": len(unified_vran_service.threat_engine.THREAT_PATTERNS)
            },
            "ai_security_agent": {
                "status": "active",
                "analyses_performed": unified_vran_service.security_agent.analysis_count
            },
            "ai_learning_agent": {
                "status": "active",
                "learning_status": unified_vran_service.learning_agent.get_learning_status()
            },
            "enforcement_engine": {
                "status": "active",
                "metrics": unified_vran_service.enforcement_engine.get_metrics()
            },
            "alert_service": {
                "status": "active (mocked)"
            }
        },
        "self_protection": SelfProtectionPolicy.get_status(),
        "segments_supported": list(unified_vran_service.segment_configs.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ==================== Segment Configuration ====================

@router.get("/segments")
async def list_segments():
    """
    List all supported segments with their configurations
    """
    return {
        "segments": [
            {
                "id": seg_id,
                "identifiers": config["identifiers"],
                "actions": config["actions"],
                "features": config["features"]
            }
            for seg_id, config in unified_vran_service.segment_configs.items()
        ],
        "total": len(unified_vran_service.segment_configs)
    }

@router.get("/segments/{segment}/identifiers")
async def get_segment_identifiers(segment: str):
    """
    Get supported identifiers for a segment
    """
    config = unified_vran_service.segment_configs.get(segment)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Segment '{segment}' not found")
    
    identifier_examples = {
        "telco": {
            "msisdn": "+919876543210",
            "imsi": "405011234567890",
            "apn": "internet.telco.com"
        },
        "mobile": {
            "phone_number": "+919876543210",
            "imei": "123456789012345",
            "device_id": "device_abc123"
        },
        "enterprise": {
            "ip_address": "192.168.1.0/24",
            "domain": "company.example.com",
            "apn": "enterprise.apn.com"
        },
        "automotive": {
            "vin": "1HGBH41JXMN109186",
            "esim_iccid": "8991234567890123456",
            "apn": "telematics.auto.com"
        },
        "white_goods": {
            "device_id": "IOT_DEVICE_001",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "imei": "123456789012345"
        },
        "cctv": {
            "camera_id": "CAM_001",
            "ip_address": "192.168.1.100",
            "rtsp_url": "rtsp://camera.local/stream"
        }
    }
    
    return {
        "segment": segment,
        "identifiers": config["identifiers"],
        "examples": identifier_examples.get(segment, {})
    }
