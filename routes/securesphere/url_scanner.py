"""
URL Scanner & Phishing Detection API
Part of SecureSphere Mobile Security Module
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4
import re

from services.securesphere.ai_security_agent import security_agent
import dependencies

router = APIRouter(prefix="/securesphere/url", tags=["SecureSphere - URL Scanner"])


class URLScanRequest(BaseModel):
    url: str
    context: Optional[str] = None
    device_id: Optional[str] = None
    source: Optional[str] = "manual"  # manual, sms, email, browser


class BulkURLScanRequest(BaseModel):
    urls: List[str]
    device_id: Optional[str] = None


@router.post("/scan")
async def scan_url(request: URLScanRequest):
    """
    Scan a URL for phishing, malware, and other threats
    Uses AI-powered analysis combined with heuristic detection
    """
    try:
        # Perform AI-powered analysis
        result = await security_agent.analyze_url(request.url, request.context)
        
        # Store scan in database
        db = dependencies.get_db()
        scan_record = {
            "id": result['analysis_id'],
            "url": request.url,
            "device_id": request.device_id,
            "source": request.source,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.url_scans.insert_one(scan_record)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/bulk")
async def scan_urls_bulk(request: BulkURLScanRequest):
    """
    Scan multiple URLs in bulk
    Useful for analyzing all links in an email or webpage
    """
    results = []
    for url in request.urls[:10]:  # Limit to 10 URLs per request
        try:
            result = await security_agent.analyze_url(url)
            results.append(result)
        except Exception as e:
            results.append({
                "url": url,
                "error": str(e),
                "risk_score": -1
            })
    
    # Calculate aggregate risk
    valid_scores = [r['risk_score'] for r in results if r.get('risk_score', -1) >= 0]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    max_score = max(valid_scores) if valid_scores else 0
    
    return {
        "total_scanned": len(request.urls),
        "results": results,
        "aggregate": {
            "average_risk_score": round(avg_score, 2),
            "max_risk_score": max_score,
            "safe_urls": sum(1 for r in results if r.get('safe_to_visit', False)),
            "risky_urls": sum(1 for r in results if r.get('risk_score', 0) > 50)
        }
    }


@router.get("/check/{url_hash}")
async def check_url_reputation(url_hash: str):
    """
    Quick reputation check using URL hash
    Returns cached result if available
    """
    db = dependencies.get_db()
    
    # Check cache
    cached = await db.url_reputation_cache.find_one({"url_hash": url_hash})
    
    if cached:
        return {
            "cached": True,
            "reputation": cached.get('reputation', 'unknown'),
            "risk_score": cached.get('risk_score', 50),
            "last_checked": cached.get('last_checked'),
            "reports_count": cached.get('reports_count', 0)
        }
    
    return {
        "cached": False,
        "reputation": "unknown",
        "message": "URL not found in database. Use /scan endpoint for full analysis."
    }


@router.get("/history")
async def get_scan_history(
    device_id: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    threat_level: Optional[str] = None
):
    """
    Get URL scan history
    Filter by device_id or threat_level
    """
    db = dependencies.get_db()
    
    query = {}
    if device_id:
        query["device_id"] = device_id
    if threat_level:
        query["result.threat_level"] = threat_level
    
    scans = await db.url_scans.find(
        query, 
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "total": len(scans),
        "scans": scans
    }


@router.post("/report")
async def report_malicious_url(url: str, reason: str, reporter_id: Optional[str] = None):
    """
    Report a URL as malicious
    Contributes to community threat intelligence
    """
    db = dependencies.get_db()
    
    report_id = str(uuid4())
    report = {
        "id": report_id,
        "url": url,
        "url_hash": re.sub(r'[^a-zA-Z0-9]', '', url)[:32],
        "reason": reason,
        "reporter_id": reporter_id,
        "status": "pending_review",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.url_reports.insert_one(report)
    
    # Update reputation cache
    await db.url_reputation_cache.update_one(
        {"url": url},
        {
            "$inc": {"reports_count": 1},
            "$set": {"last_reported": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return {
        "report_id": report_id,
        "message": "Thank you for reporting. Our team will review this URL.",
        "url": url
    }


@router.get("/stats")
async def get_url_scanner_stats():
    """
    Get URL scanner statistics and AI learning status
    """
    db = dependencies.get_db()
    
    total_scans = await db.url_scans.count_documents({})
    malicious_detected = await db.url_scans.count_documents({"result.threat_level": {"$in": ["high", "critical"]}})
    
    # Get AI learning stats
    ai_stats = security_agent.get_learning_stats()
    
    return {
        "total_scans": total_scans,
        "malicious_detected": malicious_detected,
        "detection_rate": round((malicious_detected / max(1, total_scans)) * 100, 2),
        "ai_stats": ai_stats,
        "supported_threat_types": [
            "phishing", "malware", "typosquatting", 
            "suspicious_redirect", "cryptocurrency_scam"
        ]
    }
