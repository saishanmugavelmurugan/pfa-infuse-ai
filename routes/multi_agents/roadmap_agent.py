"""
Enhancement & Roadmap Agent - Product Strategy
Role: Strategic planner for product development.
Capabilities: Analyze support themes + usage data to propose features, estimate effort, maintain roadmaps
Output: Quarterly roadmap decks, prioritized backlog, PRD drafts
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/agents/roadmap", tags=["Roadmap Agent"])

# MongoDB connection
from motor.motor_asyncio import AsyncIOMotorClient
mongo_client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mongo_client[os.environ.get("DB_NAME", "healthtrack_pro")]

# LLM Integration
#from emergentintegrations.llm.chat import LlmChat, UserMessage

# T-Shirt Sizing Guide
TSHIRT_SIZES = {
    "XS": {"days": "1-2", "points": 1, "description": "Trivial change, config update"},
    "S": {"days": "3-5", "points": 2, "description": "Simple feature, minor enhancement"},
    "M": {"days": "1-2 weeks", "points": 5, "description": "Medium feature, API + UI changes"},
    "L": {"days": "2-4 weeks", "points": 8, "description": "Large feature, multiple services"},
    "XL": {"days": "1-2 months", "points": 13, "description": "Epic feature, architectural changes"}
}

# Roadmap Horizons
ROADMAP_HORIZONS = {
    "3_year": {
        "name": "Growth Horizon",
        "focus": "Market expansion, feature parity, user acquisition",
        "timeframe": "2025-2027"
    },
    "5_year": {
        "name": "Ecosystem Horizon",
        "focus": "Platform ecosystem, partnerships, regional expansion",
        "timeframe": "2025-2029"
    },
    "10_year": {
        "name": "Disruption Horizon",
        "focus": "Industry disruption, AI-first healthcare, global reach",
        "timeframe": "2025-2034"
    }
}

# Initial Roadmap Items (seeded)
INITIAL_ROADMAP = [
    # 3-Year Growth Items
    {
        "id": "ROAD-001",
        "title": "Native Mobile App (iOS + Android)",
        "description": "Full-featured mobile app with native health integrations",
        "horizon": "3_year",
        "quarter": "Q1 2025",
        "size": "XL",
        "priority": "P0",
        "status": "in_progress",
        "category": "mobile"
    },
    {
        "id": "ROAD-002",
        "title": "Real-time Video Consultations",
        "description": "Twilio-powered video calling with screen share",
        "horizon": "3_year",
        "quarter": "Q2 2025",
        "size": "L",
        "priority": "P0",
        "status": "planned",
        "category": "telemedicine"
    },
    {
        "id": "ROAD-003",
        "title": "Multi-language Support (15 Indian languages)",
        "description": "Full localization for regional accessibility",
        "horizon": "3_year",
        "quarter": "Q2 2025",
        "size": "L",
        "priority": "P1",
        "status": "in_progress",
        "category": "accessibility"
    },
    {
        "id": "ROAD-004",
        "title": "AI Chatbot for Symptom Checker",
        "description": "GPT-powered preliminary symptom assessment",
        "horizon": "3_year",
        "quarter": "Q3 2025",
        "size": "M",
        "priority": "P1",
        "status": "planned",
        "category": "ai"
    },
    # 5-Year Ecosystem Items
    {
        "id": "ROAD-005",
        "title": "Insurance Provider Integration",
        "description": "Direct claim submission and pre-auth",
        "horizon": "5_year",
        "quarter": "Q1 2026",
        "size": "XL",
        "priority": "P1",
        "status": "backlog",
        "category": "ecosystem"
    },
    {
        "id": "ROAD-006",
        "title": "Pharmacy Network Integration",
        "description": "Direct medicine ordering and delivery",
        "horizon": "5_year",
        "quarter": "Q2 2026",
        "size": "L",
        "priority": "P2",
        "status": "backlog",
        "category": "ecosystem"
    },
    {
        "id": "ROAD-007",
        "title": "Hospital EHR Integration",
        "description": "HL7 FHIR-compliant health record exchange",
        "horizon": "5_year",
        "quarter": "Q3 2026",
        "size": "XL",
        "priority": "P1",
        "status": "backlog",
        "category": "interoperability"
    },
    {
        "id": "ROAD-008",
        "title": "B2B Enterprise Platform",
        "description": "White-label solution for corporates",
        "horizon": "5_year",
        "quarter": "Q4 2026",
        "size": "XL",
        "priority": "P2",
        "status": "backlog",
        "category": "enterprise"
    },
    # 10-Year Disruption Items
    {
        "id": "ROAD-009",
        "title": "AI-First Diagnosis Assistant",
        "description": "ML model for preliminary diagnosis suggestions",
        "horizon": "10_year",
        "quarter": "2028",
        "size": "XL",
        "priority": "P2",
        "status": "vision",
        "category": "ai"
    },
    {
        "id": "ROAD-010",
        "title": "Global Expansion (50+ Countries)",
        "description": "Multi-region deployment with local compliance",
        "horizon": "10_year",
        "quarter": "2029-2034",
        "size": "XL",
        "priority": "P2",
        "status": "vision",
        "category": "expansion"
    },
    {
        "id": "ROAD-011",
        "title": "Decentralized Health Records",
        "description": "Blockchain-based patient-controlled records",
        "horizon": "10_year",
        "quarter": "2030+",
        "size": "XL",
        "priority": "P3",
        "status": "vision",
        "category": "innovation"
    }
]

# Pydantic Models
class FeatureProposal(BaseModel):
    title: str
    description: str
    justification: str
    estimated_size: str
    priority: str
    source: str  # support_themes, usage_data, user_feedback, strategic
    horizon: str = "3_year"

class RoadmapItem(BaseModel):
    id: Optional[str] = None
    title: str
    description: str
    horizon: str
    quarter: str
    size: str
    priority: str
    status: str = "backlog"
    category: str

class PRDRequest(BaseModel):
    feature_title: str
    feature_description: str
    target_users: str
    success_metrics: Optional[str] = None

class BacklogItem(BaseModel):
    title: str
    description: str
    size: str
    priority: str
    source: str
    votes: int = 0

# Helper Functions
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

async def analyze_support_themes() -> List[Dict]:
    """Analyze support conversations for feature opportunities"""
    # Get recent support conversations
    recent = datetime.now(timezone.utc) - timedelta(days=30)
    
    pipeline = [
        {"$match": {"timestamp": {"$gte": recent}}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "unresolved": {"$sum": {"$cond": [{"$eq": ["$resolved", False]}, 1, 0]}}
        }},
        {"$sort": {"count": -1}}
    ]
    
    themes = await db.support_conversations.aggregate(pipeline).to_list(10)
    
    # Map themes to feature opportunities
    theme_opportunities = {
        "appointments": {
            "feature": "Smart Appointment Scheduling",
            "description": "AI-powered scheduling based on symptoms and doctor availability"
        },
        "lab_reports": {
            "feature": "Advanced Lab Trend Analysis",
            "description": "Long-term health trend visualization from lab reports"
        },
        "wearables": {
            "feature": "Expanded Wearable Support",
            "description": "Integration with more wearable devices and deeper metrics"
        },
        "payments": {
            "feature": "Flexible Payment Options",
            "description": "EMI, insurance integration, and multiple payment methods"
        },
        "prescriptions": {
            "feature": "Medicine Reminder System",
            "description": "Push notifications for medication schedules"
        }
    }
    
    opportunities = []
    for theme in themes:
        if theme["_id"] in theme_opportunities:
            opp = theme_opportunities[theme["_id"]]
            opportunities.append({
                "category": theme["_id"],
                "query_count": theme["count"],
                "unresolved_rate": (theme["unresolved"] / theme["count"] * 100) if theme["count"] > 0 else 0,
                "suggested_feature": opp["feature"],
                "description": opp["description"],
                "priority_score": theme["count"] * (1 + theme["unresolved"] / max(theme["count"], 1))
            })
    
    return sorted(opportunities, key=lambda x: x["priority_score"], reverse=True)

async def generate_prd(title: str, description: str, target_users: str, success_metrics: str) -> str:
    """Generate PRD draft using AI"""
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return "Unable to generate PRD - AI service unavailable"
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"prd-{uuid.uuid4()}",
            system_message="""You are a senior product manager at a healthcare technology company.
Generate professional Product Requirement Documents (PRDs) following best practices.
Include: Executive Summary, Problem Statement, Goals, User Stories, Technical Requirements,
Success Metrics, Timeline, and Risks."""
        ).with_model("openai", "gpt-5.2")
        
        prompt = f"""Generate a detailed PRD for the following feature:

**Feature Title:** {title}

**Description:** {description}

**Target Users:** {target_users}

**Success Metrics:** {success_metrics or "To be defined based on feature goals"}

Please create a comprehensive PRD in markdown format."""
        
        response = await chat.send_message(UserMessage(text=prompt))
        return response
    except Exception as e:
        print(f"PRD Generation Error: {e}")
        return f"Error generating PRD: {str(e)}"

# API Endpoints
@router.get("/roadmap")
async def get_roadmap(horizon: Optional[str] = None):
    """Get product roadmap"""
    # Check if roadmap exists in DB, otherwise seed it
    count = await db.roadmap_items.count_documents({})
    if count == 0:
        # Seed initial roadmap
        for item in INITIAL_ROADMAP:
            item["created_at"] = datetime.now(timezone.utc)
            await db.roadmap_items.insert_one(item)
    
    query = {}
    if horizon:
        query["horizon"] = horizon
    
    items = await db.roadmap_items.find(query, {"_id": 0}).to_list(100)
    
    # Group by horizon
    grouped = {
        "3_year": {"info": ROADMAP_HORIZONS["3_year"], "items": []},
        "5_year": {"info": ROADMAP_HORIZONS["5_year"], "items": []},
        "10_year": {"info": ROADMAP_HORIZONS["10_year"], "items": []}
    }
    
    for item in items:
        if item["horizon"] in grouped:
            grouped[item["horizon"]]["items"].append(item)
    
    return {
        "roadmap": grouped,
        "total_items": len(items),
        "sizing_guide": TSHIRT_SIZES
    }

@router.post("/roadmap/items")
async def add_roadmap_item(item: RoadmapItem):
    """Add new roadmap item"""
    item_dict = item.dict()
    item_dict["id"] = item.id or f"ROAD-{str(uuid.uuid4())[:8].upper()}"
    item_dict["created_at"] = datetime.now(timezone.utc)
    
    await db.roadmap_items.insert_one(item_dict)
    
    return {"status": "created", "item": item_dict}

@router.put("/roadmap/items/{item_id}")
async def update_roadmap_item(item_id: str, updates: Dict[str, Any]):
    """Update roadmap item"""
    updates["updated_at"] = datetime.now(timezone.utc)
    
    result = await db.roadmap_items.update_one(
        {"id": item_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    
    return {"status": "updated", "item_id": item_id}

@router.delete("/roadmap/items/{item_id}")
async def delete_roadmap_item(item_id: str):
    """Delete roadmap item"""
    result = await db.roadmap_items.delete_one({"id": item_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    
    return {"status": "deleted", "item_id": item_id}

@router.get("/backlog")
async def get_backlog(priority: Optional[str] = None, size: Optional[str] = None):
    """Get prioritized backlog"""
    query = {}
    if priority:
        query["priority"] = priority
    if size:
        query["size"] = size
    
    items = await db.backlog_items.find(query, {"_id": 0}).sort([
        ("priority", 1),
        ("votes", -1)
    ]).to_list(100)
    
    return {
        "backlog": items,
        "total": len(items),
        "by_priority": {
            "P0": len([i for i in items if i.get("priority") == "P0"]),
            "P1": len([i for i in items if i.get("priority") == "P1"]),
            "P2": len([i for i in items if i.get("priority") == "P2"]),
            "P3": len([i for i in items if i.get("priority") == "P3"])
        }
    }

@router.post("/backlog/items")
async def add_backlog_item(item: BacklogItem):
    """Add item to backlog"""
    item_dict = item.dict()
    item_dict["id"] = f"BACK-{str(uuid.uuid4())[:8].upper()}"
    item_dict["created_at"] = datetime.now(timezone.utc)
    
    await db.backlog_items.insert_one(item_dict)
    
    return {"status": "created", "item": item_dict}

@router.post("/backlog/items/{item_id}/vote")
async def vote_backlog_item(item_id: str):
    """Vote for a backlog item"""
    result = await db.backlog_items.update_one(
        {"id": item_id},
        {"$inc": {"votes": 1}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Backlog item not found")
    
    return {"status": "voted", "item_id": item_id}

@router.get("/analysis/support-themes")
async def get_support_theme_analysis():
    """Analyze support themes for feature opportunities"""
    opportunities = await analyze_support_themes()
    
    return {
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "period": "Last 30 days",
        "opportunities": opportunities,
        "recommendation": opportunities[0] if opportunities else None
    }

@router.post("/analysis/propose-feature")
async def propose_feature(proposal: FeatureProposal):
    """Submit a feature proposal"""
    proposal_dict = proposal.dict()
    proposal_dict["id"] = f"PROP-{str(uuid.uuid4())[:8].upper()}"
    proposal_dict["status"] = "pending_review"
    proposal_dict["created_at"] = datetime.now(timezone.utc)
    proposal_dict["effort_estimate"] = TSHIRT_SIZES.get(proposal.estimated_size, {})
    
    await db.feature_proposals.insert_one(proposal_dict)
    
    return {
        "status": "submitted",
        "proposal_id": proposal_dict["id"],
        "message": "Feature proposal submitted for review",
        "effort_estimate": proposal_dict["effort_estimate"]
    }

@router.get("/proposals")
async def get_proposals(status: Optional[str] = None):
    """Get feature proposals"""
    query = {}
    if status:
        query["status"] = status
    
    proposals = await db.feature_proposals.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return {"proposals": proposals, "total": len(proposals)}

@router.post("/prd/generate")
async def generate_prd_endpoint(request: PRDRequest):
    """Generate PRD draft for a feature"""
    prd_content = await generate_prd(
        request.feature_title,
        request.feature_description,
        request.target_users,
        request.success_metrics or ""
    )
    
    # Store generated PRD
    prd_doc = {
        "id": f"PRD-{str(uuid.uuid4())[:8].upper()}",
        "feature_title": request.feature_title,
        "content": prd_content,
        "status": "draft",
        "created_at": datetime.now(timezone.utc)
    }
    await db.prds.insert_one(prd_doc)
    
    return {
        "prd_id": prd_doc["id"],
        "status": "generated",
        "content": prd_content
    }

@router.get("/prds")
async def list_prds():
    """List all PRDs"""
    prds = await db.prds.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"prds": prds, "total": len(prds)}

@router.get("/prds/{prd_id}")
async def get_prd(prd_id: str):
    """Get specific PRD"""
    prd = await db.prds.find_one({"id": prd_id}, {"_id": 0})
    if not prd:
        raise HTTPException(status_code=404, detail="PRD not found")
    return prd

@router.get("/quarterly-deck")
async def get_quarterly_deck():
    """Generate quarterly roadmap deck data"""
    current_quarter = f"Q{((datetime.now().month - 1) // 3) + 1} {datetime.now().year}"
    
    # Get items for current and next quarter
    items = await db.roadmap_items.find({}, {"_id": 0}).to_list(100)
    
    # Filter by status
    in_progress = [i for i in items if i.get("status") == "in_progress"]
    planned = [i for i in items if i.get("status") == "planned"]
    completed = [i for i in items if i.get("status") == "completed"]
    
    # Get support theme analysis
    themes = await analyze_support_themes()
    
    return {
        "deck_title": f"HealthTrack Pro - {current_quarter} Roadmap",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {
            "executive_summary": {
                "total_items": len(items),
                "in_progress": len(in_progress),
                "planned": len(planned),
                "completed": len(completed)
            },
            "current_quarter": {
                "focus": "Mobile App Launch & Video Consultations",
                "key_deliverables": in_progress[:5]
            },
            "next_quarter": {
                "focus": "Language Expansion & AI Features",
                "planned_items": planned[:5]
            },
            "user_insights": {
                "top_themes": themes[:3],
                "recommendation": "Focus on appointment scheduling improvements based on support data"
            },
            "horizons": ROADMAP_HORIZONS
        }
    }

@router.get("/sizing-guide")
async def get_sizing_guide():
    """Get t-shirt sizing reference"""
    return {
        "sizes": TSHIRT_SIZES,
        "guidelines": {
            "XS": "Bug fixes, copy changes, config updates",
            "S": "Small features, minor UI changes, simple API endpoints",
            "M": "Medium features, requires design + dev coordination",
            "L": "Large features, multiple sprints, cross-team coordination",
            "XL": "Epic features, may span multiple quarters"
        }
    }

@router.get("/dashboard/summary")
async def get_roadmap_dashboard():
    """Get roadmap agent dashboard summary"""
    items = await db.roadmap_items.find({}, {"_id": 0}).to_list(100)
    proposals = await db.feature_proposals.find({}, {"_id": 0}).to_list(100)
    themes = await analyze_support_themes()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "roadmap": {
            "total_items": len(items),
            "by_horizon": {
                "3_year": len([i for i in items if i.get("horizon") == "3_year"]),
                "5_year": len([i for i in items if i.get("horizon") == "5_year"]),
                "10_year": len([i for i in items if i.get("horizon") == "10_year"])
            },
            "by_status": {
                "in_progress": len([i for i in items if i.get("status") == "in_progress"]),
                "planned": len([i for i in items if i.get("status") == "planned"]),
                "backlog": len([i for i in items if i.get("status") == "backlog"]),
                "completed": len([i for i in items if i.get("status") == "completed"])
            }
        },
        "proposals": {
            "total": len(proposals),
            "pending": len([p for p in proposals if p.get("status") == "pending_review"]),
            "approved": len([p for p in proposals if p.get("status") == "approved"])
        },
        "insights": {
            "top_support_theme": themes[0]["category"] if themes else None,
            "suggested_focus": themes[0]["suggested_feature"] if themes else "No data available"
        }
    }
