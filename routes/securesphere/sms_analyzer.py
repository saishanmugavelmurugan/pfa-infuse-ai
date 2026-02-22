"""
Fraudulent SMS Analyzer API
Part of SecureSphere Mobile Security Module

Detects:
- Phishing attempts
- Financial fraud (UPI, banking scams)
- Prize/lottery scams
- OTP theft attempts
- Impersonation attacks
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4

from services.securesphere.ai_security_agent import security_agent
import dependencies

router = APIRouter(prefix="/securesphere/sms", tags=["SecureSphere - SMS Analyzer"])


class SMSAnalyzeRequest(BaseModel):
    message: str
    sender: Optional[str] = None
    device_id: Optional[str] = None
    timestamp: Optional[str] = None


class BulkSMSAnalyzeRequest(BaseModel):
    messages: List[dict]  # [{"message": str, "sender": str}]
    device_id: Optional[str] = None


@router.post("/analyze")
async def analyze_sms(request: SMSAnalyzeRequest):
    """
    Analyze an SMS for fraud patterns
    Uses AI-powered semantic analysis combined with pattern matching
    """
    try:
        # Perform AI-powered analysis
        result = await security_agent.analyze_sms(request.message, request.sender)
        
        # Store analysis in database
        db = dependencies.get_db()
        analysis_record = {
            "id": result['analysis_id'],
            "message_hash": hash(request.message) % 10**8,
            "sender": request.sender,
            "device_id": request.device_id,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.sms_analyses.insert_one(analysis_record)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/bulk")
async def analyze_sms_bulk(request: BulkSMSAnalyzeRequest):
    """
    Analyze multiple SMS messages in bulk
    Useful for scanning inbox for threats
    """
    results = []
    threat_count = 0
    
    for msg in request.messages[:50]:  # Limit to 50 messages per request
        try:
            result = await security_agent.analyze_sms(
                msg.get('message', ''), 
                msg.get('sender')
            )
            results.append(result)
            if result.get('is_fraud') or result.get('is_spam'):
                threat_count += 1
        except Exception as e:
            results.append({
                "message_preview": msg.get('message', '')[:50],
                "error": str(e),
                "risk_score": -1
            })
    
    return {
        "total_analyzed": len(request.messages),
        "threats_found": threat_count,
        "results": results,
        "summary": {
            "spam_messages": sum(1 for r in results if r.get('is_spam')),
            "fraud_messages": sum(1 for r in results if r.get('is_fraud')),
            "safe_messages": sum(1 for r in results if r.get('risk_score', 100) < 40)
        }
    }


@router.get("/fraud-types")
async def get_fraud_types():
    """
    Get list of fraud types detected by the system
    Includes descriptions and examples
    """
    return {
        "fraud_types": [
            {
                "type": "phishing",
                "name": "Phishing Attack",
                "description": "Messages attempting to trick you into revealing personal information",
                "examples": ["Your account has been suspended. Click here to verify."],
                "severity": "high"
            },
            {
                "type": "financial_fraud",
                "name": "Financial Fraud",
                "description": "Scams targeting your bank account, UPI, or credit cards",
                "examples": ["Your UPI payment of Rs.5000 failed. Click to retry."],
                "severity": "critical"
            },
            {
                "type": "lottery_scam",
                "name": "Lottery/Prize Scam",
                "description": "Fake prize winning notifications asking for fees",
                "examples": ["Congratulations! You've won Rs.10 Lakhs. Pay Rs.500 to claim."],
                "severity": "high"
            },
            {
                "type": "otp_theft",
                "name": "OTP Theft",
                "description": "Attempts to steal your One-Time Passwords",
                "examples": ["This is your bank. Please share the OTP for verification."],
                "severity": "critical"
            },
            {
                "type": "impersonation",
                "name": "Impersonation",
                "description": "Messages pretending to be from banks, government, or known contacts",
                "examples": ["Dear customer, your PAN is blocked. Update KYC immediately."],
                "severity": "high"
            },
            {
                "type": "job_scam",
                "name": "Job Scam",
                "description": "Fake job offers requiring upfront payment",
                "examples": ["Work from home. Earn Rs.50000/month. Pay Rs.1000 registration."],
                "severity": "medium"
            },
            {
                "type": "romance_scam",
                "name": "Romance Scam",
                "description": "Fraudsters building fake relationships to extract money",
                "examples": ["I'm stuck abroad. Please send money for ticket."],
                "severity": "medium"
            }
        ]
    }


@router.get("/history")
async def get_sms_analysis_history(
    device_id: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    fraud_type: Optional[str] = None,
    include_safe: bool = False
):
    """
    Get SMS analysis history
    Filter by device_id, fraud_type, or exclude safe messages
    """
    db = dependencies.get_db()
    
    query = {}
    if device_id:
        query["device_id"] = device_id
    if fraud_type:
        query["result.fraud_type"] = fraud_type
    if not include_safe:
        query["result.risk_score"] = {"$gte": 40}
    
    analyses = await db.sms_analyses.find(
        query, 
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "total": len(analyses),
        "analyses": analyses
    }


@router.post("/report")
async def report_fraudulent_sms(
    message: str, 
    sender: Optional[str] = None,
    fraud_type: str = "unknown",
    reporter_id: Optional[str] = None
):
    """
    Report a fraudulent SMS
    Contributes to community threat intelligence
    """
    db = dependencies.get_db()
    
    report_id = str(uuid4())
    report = {
        "id": report_id,
        "message_hash": hash(message) % 10**8,
        "sender": sender,
        "fraud_type": fraud_type,
        "reporter_id": reporter_id,
        "status": "pending_review",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sms_reports.insert_one(report)
    
    return {
        "report_id": report_id,
        "message": "Thank you for reporting. This helps protect others from fraud.",
        "fraud_type": fraud_type
    }


@router.get("/sender/reputation/{sender}")
async def check_sender_reputation(sender: str):
    """
    Check reputation of an SMS sender
    Returns history of fraud reports and analysis results
    """
    db = dependencies.get_db()
    
    # Get reports for this sender
    reports = await db.sms_reports.count_documents({"sender": sender})
    
    # Get analyses for this sender
    analyses = await db.sms_analyses.find(
        {"sender": sender},
        {"_id": 0, "result.risk_score": 1, "result.fraud_type": 1}
    ).limit(100).to_list(100)
    
    if not analyses and reports == 0:
        return {
            "sender": sender,
            "reputation": "unknown",
            "message": "No data available for this sender"
        }
    
    avg_risk = sum(a.get('result', {}).get('risk_score', 50) for a in analyses) / max(1, len(analyses))
    
    return {
        "sender": sender,
        "reputation": "malicious" if avg_risk > 70 or reports > 5 else "suspicious" if avg_risk > 40 or reports > 0 else "clean",
        "average_risk_score": round(avg_risk, 2),
        "total_reports": reports,
        "total_analyses": len(analyses),
        "fraud_types_detected": list(set(a.get('result', {}).get('fraud_type') for a in analyses if a.get('result', {}).get('fraud_type')))
    }


@router.get("/stats")
async def get_sms_analyzer_stats():
    """
    Get SMS analyzer statistics
    """
    db = dependencies.get_db()
    
    total_analyses = await db.sms_analyses.count_documents({})
    fraud_detected = await db.sms_analyses.count_documents({"result.is_fraud": True})
    spam_detected = await db.sms_analyses.count_documents({"result.is_spam": True})
    
    # Get AI learning stats
    ai_stats = security_agent.get_learning_stats()
    
    return {
        "total_analyses": total_analyses,
        "fraud_detected": fraud_detected,
        "spam_detected": spam_detected,
        "detection_rate": round(((fraud_detected + spam_detected) / max(1, total_analyses)) * 100, 2),
        "ai_stats": ai_stats,
        "supported_languages": ["English", "Hindi", "Hinglish", "Tamil", "Telugu", "Marathi"]
    }
