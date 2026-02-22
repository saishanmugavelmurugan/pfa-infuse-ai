"""
AI Agents API - Learning Agent & Support Agent Endpoints
Part of SecureSphere & HealthTrack Pro
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
from uuid import uuid4

from services.securesphere.ai_learning_agent import ai_learning_agent
from services.securesphere.ai_support_agent import ai_support_agent
import dependencies

router = APIRouter(prefix="/securesphere/ai-agents", tags=["SecureSphere - AI Agents"])


class SupportQuery(BaseModel):
    session_id: Optional[str] = None
    message: str
    product: str = "securesphere"  # securesphere or healthtrack
    language: str = "en"
    user_context: Optional[Dict] = None


class FeedbackRequest(BaseModel):
    analysis_type: str  # url, sms, threat
    analysis_id: str
    feedback: str  # false_positive, false_negative, correct
    details: Optional[str] = None


# ==================== AI Learning Agent Endpoints ====================

@router.get("/learning/status")
async def get_learning_status():
    """
    Get AI Learning Agent status and statistics
    """
    return ai_learning_agent.get_learning_status()


@router.get("/learning/threat-report")
async def get_threat_intelligence_report():
    """
    Generate comprehensive threat intelligence report
    """
    return await ai_learning_agent.generate_threat_intelligence_report()


@router.post("/learning/feedback")
async def submit_analysis_feedback(feedback: FeedbackRequest):
    """
    Submit feedback for an analysis to improve AI learning
    """
    db = dependencies.get_db()
    
    feedback_id = str(uuid4())
    feedback_record = {
        "id": feedback_id,
        "analysis_type": feedback.analysis_type,
        "analysis_id": feedback.analysis_id,
        "feedback": feedback.feedback,
        "details": feedback.details,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ai_feedback.insert_one(feedback_record)
    
    # Process feedback for learning
    if feedback.feedback in ["false_positive", "false_negative"]:
        ai_learning_agent.learning_stats["false_positives_corrected"] += 1
    
    return {
        "feedback_id": feedback_id,
        "message": "Thank you for your feedback! This helps improve our AI detection.",
        "learning_impact": "Pattern adjustment queued"
    }


@router.get("/learning/patterns")
async def get_learned_patterns(
    pattern_type: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    Get learned threat patterns
    pattern_type: url, sms, network, automotive
    """
    patterns = {
        "url": list(ai_learning_agent.url_signatures.values())[:limit],
        "sms": list(ai_learning_agent.sms_templates.values())[:limit],
        "network": ai_learning_agent.network_anomalies[:limit],
        "automotive": list(ai_learning_agent.automotive_signatures.values())[:limit]
    }
    
    if pattern_type and pattern_type in patterns:
        return {
            "pattern_type": pattern_type,
            "count": len(patterns[pattern_type]),
            "patterns": patterns[pattern_type]
        }
    
    return {
        "total_patterns": sum(len(p) for p in patterns.values()),
        "by_type": {k: len(v) for k, v in patterns.items()}
    }


@router.get("/learning/sender-reputation/{sender}")
async def get_sender_reputation(sender: str):
    """
    Get learned reputation for an SMS sender
    """
    reputation = ai_learning_agent.sender_reputation.get(sender.lower())
    
    if not reputation:
        return {
            "sender": sender,
            "status": "unknown",
            "message": "No reputation data available for this sender"
        }
    
    return {
        "sender": sender,
        "reputation": reputation,
        "trust_level": "trusted" if reputation["trust_score"] > 70 else "neutral" if reputation["trust_score"] > 30 else "suspicious"
    }


# ==================== AI Support Agent Endpoints ====================

@router.post("/support/query")
async def query_support_agent(query: SupportQuery):
    """
    Send a query to the AI Support Agent
    """
    session_id = query.session_id or str(uuid4())
    
    response = await ai_support_agent.get_response(
        session_id=session_id,
        message=query.message,
        product=query.product,
        language=query.language,
        user_context=query.user_context
    )
    
    # Store in database for analytics
    db = dependencies.get_db()
    await db.support_queries.insert_one({
        "session_id": session_id,
        "query": query.message,
        "product": query.product,
        "response": response,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return response


@router.get("/support/history/{session_id}")
async def get_support_history(session_id: str):
    """
    Get conversation history for a support session
    """
    history = ai_support_agent.get_conversation_history(session_id)
    
    return {
        "session_id": session_id,
        "messages": history,
        "message_count": len(history)
    }


@router.post("/support/escalate/{session_id}")
async def escalate_to_human(session_id: str, reason: str = "User requested"):
    """
    Escalate support conversation to human agent
    """
    result = await ai_support_agent.escalate_to_human(session_id, reason)
    
    # Store escalation in database
    db = dependencies.get_db()
    await db.support_escalations.insert_one({
        "ticket_id": result["ticket_id"],
        "session_id": session_id,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return result


@router.get("/support/stats")
async def get_support_stats():
    """
    Get AI Support Agent statistics
    """
    return ai_support_agent.get_support_stats()


@router.get("/support/faq/{product}")
async def get_product_faq(product: str):
    """
    Get FAQ for a product
    product: securesphere or healthtrack
    """
    from services.securesphere.ai_support_agent import KNOWLEDGE_BASE
    
    kb = KNOWLEDGE_BASE.get(product)
    if not kb:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "product": product,
        "product_name": kb.get("product_name"),
        "faqs": kb.get("faqs", [])
    }


# ==================== Combined Analytics ====================

@router.get("/analytics")
async def get_ai_agents_analytics():
    """
    Get combined analytics for all AI agents
    """
    learning_status = ai_learning_agent.get_learning_status()
    support_stats = ai_support_agent.get_support_stats()
    
    return {
        "ai_learning_agent": {
            "status": learning_status["status"],
            "patterns_learned": learning_status["statistics"]["patterns_learned"],
            "samples_processed": learning_status["statistics"]["total_samples_processed"],
            "model_version": learning_status["model_version"]
        },
        "ai_support_agent": {
            "total_queries": support_stats["total_queries"],
            "auto_resolution_rate": support_stats["auto_resolution_rate"],
            "average_response_time_ms": support_stats["average_response_time_ms"]
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
