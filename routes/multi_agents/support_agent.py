"""
Support Agent - Customer & Ops Support
Role: Front-line resolution and triage.
Capabilities: Instant query resolution via knowledge base, context-aware answers, smart escalation
Output: Resolved chats, ticket drafts, weekly "Top Issues" report
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import os
import uuid
import json

from dotenv import load_dotenv
load_dotenv()

# SendGrid for email
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

router = APIRouter(prefix="/agents/support", tags=["Support Agent"])

# MongoDB connection
from motor.motor_asyncio import AsyncIOMotorClient
mongo_client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mongo_client[os.environ.get("DB_NAME", "healthtrack_pro")]

# LLM Integration
#from emergentintegrations.llm.chat import LlmChat, UserMessage

# Knowledge Base (SOPs, FAQs, etc.)
KNOWLEDGE_BASE = {
    "appointment_booking": {
        "keywords": ["book", "appointment", "schedule", "consultation", "doctor"],
        "answer": "To book an appointment: 1) Go to 'Find Doctor' section, 2) Select your preferred doctor, 3) Choose available time slot, 4) Confirm booking. You'll receive a confirmation email.",
        "category": "appointments"
    },
    "cancel_appointment": {
        "keywords": ["cancel", "reschedule", "change appointment"],
        "answer": "To cancel/reschedule: Go to 'My Appointments' → Select the appointment → Click 'Cancel' or 'Reschedule'. Cancellations made 24+ hours before are fully refundable.",
        "category": "appointments"
    },
    "lab_report_upload": {
        "keywords": ["upload", "lab report", "test results", "diagnostic"],
        "answer": "To upload lab reports: 1) Go to 'Lab Reports' section, 2) Click 'Upload New Report', 3) Select your PDF/image file, 4) Our AI will analyze it within minutes.",
        "category": "lab_reports"
    },
    "payment_issue": {
        "keywords": ["payment", "refund", "charge", "billing", "transaction"],
        "answer": "For payment issues: 1) Check 'Payment History' for transaction details. 2) If charged incorrectly, click 'Report Issue'. Refunds are processed within 5-7 business days.",
        "category": "payments"
    },
    "wearable_sync": {
        "keywords": ["wearable", "sync", "apple health", "google fit", "samsung", "fitbit"],
        "answer": "To sync wearables: Go to Settings → Connected Devices → Select your device (Apple Health/Google Fit/Samsung Health) → Authorize access. Data syncs automatically every hour.",
        "category": "wearables"
    },
    "prescription_download": {
        "keywords": ["prescription", "download", "medicine", "medication"],
        "answer": "To download prescriptions: Go to 'Prescriptions' → Select the prescription → Click 'Download PDF'. Prescriptions include doctor's digital signature and are pharmacy-ready.",
        "category": "prescriptions"
    },
    "data_privacy": {
        "keywords": ["privacy", "data", "security", "otp", "access"],
        "answer": "Your data is protected with OTP-based access control. Doctors must request access and you approve via OTP. All data is encrypted (AES-256) and HIPAA/ABDM compliant.",
        "category": "security"
    },
    "account_issue": {
        "keywords": ["login", "password", "account", "locked", "forgot"],
        "answer": "For account issues: Use 'Forgot Password' on login page. If locked, wait 30 minutes or contact support. For persistent issues, verify your registered email/phone.",
        "category": "account"
    }
}

# Pydantic Models
class SupportQuery(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    message: str
    user_context: Optional[Dict[str, Any]] = None  # User session data

class SupportResponse(BaseModel):
    session_id: str
    message: str
    resolved: bool
    confidence: float
    category: str
    escalation_required: bool
    ticket_id: Optional[str] = None
    suggested_actions: List[str] = []

class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    priority: str = "medium"
    user_id: Optional[str] = None
    user_email: Optional[str] = None

class TicketResponse(BaseModel):
    ticket_id: str
    status: str
    message: str

class EscalationRequest(BaseModel):
    session_id: str
    reason: str
    priority: str = "high"

class KnowledgeBaseEntry(BaseModel):
    key: str
    keywords: List[str]
    answer: str
    category: str

class EmailReportRequest(BaseModel):
    recipient_email: str = "support.infuse.net.in"
    report_type: str = "weekly"
    custom_message: Optional[str] = None

class SessionEndRequest(BaseModel):
    session_id: str
    reason: str = "user_closed"  # user_closed, timeout, navigation

# In-memory active sessions tracking (for fast lookup)
ACTIVE_SESSIONS: Dict[str, Dict] = {}
SESSION_TIMEOUT_MINUTES = 10

# Email sending function
async def send_email_report(to_email: str, subject: str, html_content: str):
    """Send email report via SendGrid"""
    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
    
    if not SENDGRID_AVAILABLE or not sendgrid_key or sendgrid_key.startswith("MOCK"):
        # Return mocked response
        return {
            "success": True,
            "mocked": True,
            "message": f"Email would be sent to {to_email} (SendGrid not configured)"
        }
    
    try:
        message = Mail(
            from_email=Email("noreply@infuse.net.in", "HealthTrack Pro Support"),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        sg = SendGridAPIClient(sendgrid_key)
        response = sg.send(message)
        
        return {
            "success": response.status_code in [200, 201, 202],
            "mocked": False,
            "status_code": response.status_code
        }
    except Exception as e:
        print(f"SendGrid Error: {e}")
        return {
            "success": False,
            "mocked": False,
            "error": str(e)
        }

# Session Management Functions
async def cleanup_session(session_id: str, reason: str = "user_closed"):
    """Clean up a session - remove from active sessions and mark as closed in DB"""
    # Remove from in-memory tracking
    if session_id in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_id]
    
    # Mark session as closed in database
    await db.support_sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "status": "closed",
                "closed_at": datetime.now(timezone.utc),
                "close_reason": reason
            }
        },
        upsert=True
    )
    
    # Clear any cached LLM conversation context
    # The LlmChat library uses session_id for context - we mark it as ended
    await db.support_session_context.delete_many({"session_id": session_id})
    
    return True

async def create_new_session() -> str:
    """Create a fresh new session with unique ID"""
    session_id = str(uuid.uuid4())
    
    # Track in memory
    ACTIVE_SESSIONS[session_id] = {
        "created_at": datetime.now(timezone.utc),
        "last_activity": datetime.now(timezone.utc),
        "message_count": 0
    }
    
    # Store in database
    await db.support_sessions.insert_one({
        "session_id": session_id,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "last_activity": datetime.now(timezone.utc),
        "message_count": 0
    })
    
    return session_id

async def update_session_activity(session_id: str):
    """Update session last activity timestamp"""
    now = datetime.now(timezone.utc)
    
    if session_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[session_id]["last_activity"] = now
        ACTIVE_SESSIONS[session_id]["message_count"] += 1
    
    await db.support_sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {"last_activity": now},
            "$inc": {"message_count": 1}
        },
        upsert=True
    )

async def is_session_valid(session_id: str) -> bool:
    """Check if a session is still valid (not closed and not timed out)"""
    if not session_id:
        return False
    
    # Check in-memory first
    if session_id in ACTIVE_SESSIONS:
        session = ACTIVE_SESSIONS[session_id]
        elapsed = (datetime.now(timezone.utc) - session["last_activity"]).total_seconds()
        if elapsed > SESSION_TIMEOUT_MINUTES * 60:
            await cleanup_session(session_id, "timeout")
            return False
        return True
    
    # Check database
    session = await db.support_sessions.find_one({"session_id": session_id})
    if not session or session.get("status") == "closed":
        return False
    
    # Check timeout
    last_activity = session.get("last_activity")
    if last_activity:
        elapsed = (datetime.now(timezone.utc) - last_activity).total_seconds()
        if elapsed > SESSION_TIMEOUT_MINUTES * 60:
            await cleanup_session(session_id, "timeout")
            return False
    
    return True

async def garbage_collect_stale_sessions():
    """Clean up sessions older than 30 minutes"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    
    # Clean from memory
    stale_sessions = [
        sid for sid, data in ACTIVE_SESSIONS.items()
        if data["last_activity"] < cutoff
    ]
    for sid in stale_sessions:
        del ACTIVE_SESSIONS[sid]
    
    # Clean from database
    result = await db.support_sessions.update_many(
        {
            "status": "active",
            "last_activity": {"$lt": cutoff}
        },
        {
            "$set": {
                "status": "closed",
                "closed_at": datetime.now(timezone.utc),
                "close_reason": "garbage_collection"
            }
        }
    )
    
    return {"cleaned_memory": len(stale_sessions), "cleaned_db": result.modified_count}

# Helper Functions
def find_knowledge_match(query: str) -> tuple:
    """Find matching knowledge base entry"""
    query_lower = query.lower()
    best_match = None
    best_score = 0
    
    for key, entry in KNOWLEDGE_BASE.items():
        score = sum(1 for keyword in entry["keywords"] if keyword in query_lower)
        if score > best_score:
            best_score = score
            best_match = entry
    
    confidence = min(best_score / 3, 1.0) if best_score > 0 else 0
    return best_match, confidence

async def get_ai_response(session_id: str, message: str, context: str = "") -> str:
    """Get AI-powered response using GPT-5.2"""
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return "I apologize, but I'm having trouble connecting. Please try again or contact support directly."
        
        system_message = f"""You are a helpful support agent for HealthTrack Pro, a healthcare platform.
Your role is to assist users with their queries about appointments, lab reports, prescriptions, wearable integration, and account issues.

Platform Features:
- Appointment booking with Allopathic and Ayurvedic doctors
- AI-powered lab report analysis
- Wearable device integration (Apple Health, Google Fit, Samsung Health)
- Digital prescriptions
- OTP-based secure health record access

Guidelines:
1. Be helpful, professional, and empathetic
2. Provide clear, step-by-step instructions when applicable
3. If you cannot resolve the issue, suggest escalation
4. Never share sensitive medical advice - direct to doctors
5. Mention compliance (HIPAA, ABDM) when relevant

{f"Context about the user: {context}" if context else ""}
"""
        
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=message)
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        print(f"AI Response Error: {e}")
        return "I apologize, but I'm experiencing technical difficulties. Let me connect you with a human agent."

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

# API Endpoints
@router.post("/chat", response_model=SupportResponse)
async def support_chat(query: SupportQuery):
    """Main support chat endpoint"""
    # Check if existing session is valid, otherwise create new one
    if query.session_id and await is_session_valid(query.session_id):
        session_id = query.session_id
    else:
        # Create fresh session - no context from previous sessions
        session_id = await create_new_session()
    
    # Update session activity
    await update_session_activity(session_id)
    
    # Try knowledge base first
    kb_match, kb_confidence = find_knowledge_match(query.message)
    
    if kb_match and kb_confidence >= 0.6:
        # High confidence match from knowledge base
        response_message = kb_match["answer"]
        category = kb_match["category"]
        resolved = True
        escalation_required = False
        confidence = kb_confidence
    else:
        # Use AI for complex queries
        context = json.dumps(query.user_context) if query.user_context else ""
        ai_response = await get_ai_response(session_id, query.message, context)
        response_message = ai_response
        category = kb_match["category"] if kb_match else "general"
        resolved = kb_confidence >= 0.3
        escalation_required = kb_confidence < 0.3
        confidence = max(kb_confidence, 0.5) if not escalation_required else 0.3
    
    # Store conversation in database
    conversation = {
        "session_id": session_id,
        "user_id": query.user_id,
        "user_message": query.message,
        "agent_response": response_message,
        "category": category,
        "resolved": resolved,
        "confidence": confidence,
        "escalation_required": escalation_required,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.support_conversations.insert_one(conversation)
    
    # Update analytics
    await db.support_analytics.update_one(
        {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d")},
        {
            "$inc": {
                "total_queries": 1,
                f"categories.{category}": 1,
                "resolved_count": 1 if resolved else 0,
                "escalated_count": 1 if escalation_required else 0
            }
        },
        upsert=True
    )
    
    return SupportResponse(
        session_id=session_id,
        message=response_message,
        resolved=resolved,
        confidence=confidence,
        category=category,
        escalation_required=escalation_required,
        suggested_actions=["Book Appointment", "View Lab Reports", "Contact Doctor"] if not resolved else []
    )

# Session Management Endpoints
@router.post("/session/end")
async def end_session(request: SessionEndRequest):
    """End a support chat session - clears all context"""
    session_id = request.session_id
    reason = request.reason
    
    # Clean up the session
    await cleanup_session(session_id, reason)
    
    return {
        "status": "success",
        "message": "Session ended successfully",
        "session_id": session_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/session/new")
async def create_session():
    """Create a fresh new support session"""
    session_id = await create_new_session()
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": "Hi! How can I help you today?",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Check session status"""
    is_valid = await is_session_valid(session_id)
    
    session = await db.support_sessions.find_one(
        {"session_id": session_id},
        {"_id": 0}
    )
    
    return {
        "session_id": session_id,
        "is_valid": is_valid,
        "status": session.get("status") if session else "not_found",
        "message_count": session.get("message_count", 0) if session else 0,
        "last_activity": session.get("last_activity").isoformat() if session and session.get("last_activity") else None
    }

@router.post("/session/cleanup")
async def cleanup_stale_sessions():
    """Garbage collect stale sessions (admin endpoint)"""
    result = await garbage_collect_stale_sessions()
    
    return {
        "status": "success",
        "cleaned": result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/tickets/create", response_model=TicketResponse)
async def create_ticket(ticket: TicketCreate, background_tasks: BackgroundTasks):
    """Create support ticket (mocked Jira/Zendesk integration)"""
    ticket_id = f"HTPRO-{str(uuid.uuid4())[:8].upper()}"
    
    ticket_doc = {
        "ticket_id": ticket_id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "user_id": ticket.user_id,
        "user_email": ticket.user_email,
        "status": "open",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "integration": {
            "jira": {"synced": False, "mocked": True},
            "zendesk": {"synced": False, "mocked": True}
        }
    }
    await db.support_tickets.insert_one(ticket_doc)
    
    # TODO: Send email notification (background task)
    # background_tasks.add_task(send_ticket_notification, ticket_doc)
    
    return TicketResponse(
        ticket_id=ticket_id,
        status="created",
        message=f"Ticket {ticket_id} created successfully. You will receive updates at {ticket.user_email or 'your registered email'}."
    )

@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Get ticket details"""
    ticket = await db.support_tickets.find_one({"ticket_id": ticket_id}, {"_id": 0})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return serialize_doc(ticket)

@router.get("/tickets")
async def list_tickets(user_id: Optional[str] = None, status: Optional[str] = None):
    """List tickets with optional filters"""
    query = {}
    if user_id:
        query["user_id"] = user_id
    if status:
        query["status"] = status
    
    tickets = await db.support_tickets.find(query, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"tickets": [serialize_doc(t) for t in tickets]}

@router.post("/escalate")
async def escalate_to_human(escalation: EscalationRequest):
    """Escalate conversation to human agent"""
    escalation_doc = {
        "session_id": escalation.session_id,
        "reason": escalation.reason,
        "priority": escalation.priority,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "notifications": {
            "slack": {"sent": False, "mocked": True},
            "email": {"sent": False, "mocked": True},
            "whatsapp": {"sent": False, "mocked": True}
        }
    }
    await db.support_escalations.insert_one(escalation_doc)
    
    return {
        "status": "escalated",
        "message": "Your conversation has been escalated to a human agent. Expected response time: 15-30 minutes.",
        "escalation_id": str(escalation_doc["_id"]) if "_id" in escalation_doc else escalation.session_id
    }

@router.get("/analytics/summary")
async def get_support_analytics():
    """Get support analytics summary"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Get today's analytics
    today_stats = await db.support_analytics.find_one({"date": today}, {"_id": 0})
    
    # Get top issues this week
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_issues = await db.support_conversations.aggregate(pipeline).to_list(5)
    
    # Get resolution rate
    total = await db.support_conversations.count_documents({})
    resolved = await db.support_conversations.count_documents({"resolved": True})
    
    return {
        "today": today_stats or {"total_queries": 0, "resolved_count": 0, "escalated_count": 0},
        "top_issues": [{"category": i["_id"], "count": i["count"]} for i in top_issues],
        "resolution_rate": (resolved / total * 100) if total > 0 else 0,
        "total_conversations": total
    }

@router.get("/report/weekly")
async def generate_weekly_report():
    """Generate weekly top issues report"""
    # Get conversations from last 7 days
    from datetime import timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": week_ago}}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "resolved": {"$sum": {"$cond": ["$resolved", 1, 0]}},
            "escalated": {"$sum": {"$cond": ["$escalation_required", 1, 0]}}
        }},
        {"$sort": {"count": -1}}
    ]
    
    category_stats = await db.support_conversations.aggregate(pipeline).to_list(20)
    
    total_queries = sum(c["count"] for c in category_stats)
    total_resolved = sum(c["resolved"] for c in category_stats)
    
    return {
        "report_type": "weekly",
        "period": {
            "start": week_ago.isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_queries": total_queries,
            "resolved": total_resolved,
            "resolution_rate": (total_resolved / total_queries * 100) if total_queries > 0 else 0
        },
        "top_issues": category_stats,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/knowledge-base")
async def get_knowledge_base():
    """Get current knowledge base entries"""
    # Get from database if available, otherwise return default
    db_entries = await db.support_knowledge_base.find({}, {"_id": 0}).to_list(100)
    if db_entries:
        return {"entries": {e["key"]: e for e in db_entries}, "source": "database"}
    return {"entries": KNOWLEDGE_BASE, "source": "default"}

@router.post("/knowledge-base")
async def add_knowledge_entry(entry: KnowledgeBaseEntry):
    """Add or update a knowledge base entry"""
    kb_doc = {
        "key": entry.key,
        "keywords": entry.keywords,
        "answer": entry.answer,
        "category": entry.category,
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.support_knowledge_base.update_one(
        {"key": entry.key},
        {"$set": kb_doc},
        upsert=True
    )
    
    return {"status": "success", "message": f"Knowledge entry '{entry.key}' saved", "entry": kb_doc}

@router.delete("/knowledge-base/{key}")
async def delete_knowledge_entry(key: str):
    """Delete a knowledge base entry"""
    result = await db.support_knowledge_base.delete_one({"key": key})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Knowledge entry '{key}' not found")
    return {"status": "success", "message": f"Knowledge entry '{key}' deleted"}

@router.get("/knowledge-base/categories")
async def get_knowledge_categories():
    """Get all knowledge base categories"""
    categories = set()
    for entry in KNOWLEDGE_BASE.values():
        categories.add(entry["category"])
    
    db_entries = await db.support_knowledge_base.find({}, {"category": 1}).to_list(100)
    for entry in db_entries:
        categories.add(entry.get("category", "general"))
    
    return {"categories": sorted(list(categories))}

@router.post("/report/email")
async def send_weekly_report_email(request: EmailReportRequest, background_tasks: BackgroundTasks):
    """Generate and send weekly report via email"""
    from datetime import timedelta
    
    # Generate the report data
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": week_ago}}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "resolved": {"$sum": {"$cond": ["$resolved", 1, 0]}},
            "escalated": {"$sum": {"$cond": ["$escalation_required", 1, 0]}}
        }},
        {"$sort": {"count": -1}}
    ]
    
    category_stats = await db.support_conversations.aggregate(pipeline).to_list(20)
    
    total_queries = sum(c["count"] for c in category_stats)
    total_resolved = sum(c["resolved"] for c in category_stats)
    resolution_rate = (total_resolved / total_queries * 100) if total_queries > 0 else 0
    
    # Generate HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #FFDA7B, #FF9A3B, #E55A00); padding: 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 24px; }}
            .header p {{ color: rgba(255,255,255,0.9); margin: 10px 0 0 0; }}
            .content {{ padding: 30px; }}
            .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat {{ text-align: center; }}
            .stat-value {{ font-size: 32px; font-weight: bold; color: #E55A00; }}
            .stat-label {{ color: #666; font-size: 12px; }}
            .issues-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .issues-table th {{ background: #f5f5f5; padding: 12px; text-align: left; border-bottom: 2px solid #E55A00; }}
            .issues-table td {{ padding: 12px; border-bottom: 1px solid #eee; }}
            .footer {{ background: #1a1a2e; color: #888; padding: 20px; text-align: center; font-size: 12px; }}
            .footer a {{ color: #FF9A3B; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Weekly Support Report</h1>
                <p>HealthTrack Pro - AI Support Agent</p>
            </div>
            <div class="content">
                <h2>Summary</h2>
                <p><strong>Period:</strong> {week_ago.strftime('%b %d')} - {datetime.now(timezone.utc).strftime('%b %d, %Y')}</p>
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{total_queries}</div>
                        <div class="stat-label">Total Queries</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_resolved}</div>
                        <div class="stat-label">Resolved</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{resolution_rate:.1f}%</div>
                        <div class="stat-label">Resolution Rate</div>
                    </div>
                </div>
                
                <h2>Top Issues by Category</h2>
                <table class="issues-table">
                    <tr>
                        <th>Category</th>
                        <th>Queries</th>
                        <th>Resolved</th>
                        <th>Escalated</th>
                    </tr>
                    {"".join(f'''<tr>
                        <td style="text-transform: capitalize;">{cat.get("_id", "general")}</td>
                        <td>{cat.get("count", 0)}</td>
                        <td style="color: green;">{cat.get("resolved", 0)}</td>
                        <td style="color: orange;">{cat.get("escalated", 0)}</td>
                    </tr>''' for cat in category_stats[:10])}
                </table>
                
                {f"<p><strong>Note:</strong> {request.custom_message}</p>" if request.custom_message else ""}
                
                <p style="color: #888; font-size: 12px; margin-top: 20px;">
                    This report was automatically generated by the HealthTrack Pro AI Support Agent.
                </p>
            </div>
            <div class="footer">
                <p>Powered by <strong>Infuse.AI</strong></p>
                <p><a href="mailto:info@infuse.net.in">info@infuse.net.in</a> | <a href="https://www.infuse.net.in">www.infuse.net.in</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Send email
    email_result = await send_email_report(
        to_email=request.recipient_email,
        subject=f"HealthTrack Pro - Weekly Support Report ({week_ago.strftime('%b %d')} - {datetime.now(timezone.utc).strftime('%b %d')})",
        html_content=html_content
    )
    
    # Log the report
    report_log = {
        "type": request.report_type,
        "recipient": request.recipient_email,
        "sent_at": datetime.now(timezone.utc),
        "summary": {
            "total_queries": total_queries,
            "resolved": total_resolved,
            "resolution_rate": resolution_rate
        },
        "email_result": email_result
    }
    await db.support_report_logs.insert_one(report_log)
    
    return {
        "status": "success",
        "message": f"Report {'sent' if email_result.get('success') else 'generation completed'} to {request.recipient_email}",
        "email_status": email_result,
        "report_summary": {
            "total_queries": total_queries,
            "resolved": total_resolved,
            "resolution_rate": round(resolution_rate, 1),
            "top_categories": [{"category": c["_id"], "count": c["count"]} for c in category_stats[:5]]
        }
    }

@router.get("/report/history")
async def get_report_history(limit: int = 10):
    """Get history of sent reports"""
    reports = await db.support_report_logs.find(
        {}, 
        {"_id": 0}
    ).sort("sent_at", -1).limit(limit).to_list(limit)
    
    return {"reports": [serialize_doc(r) for r in reports]}
