from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os
import json

router = APIRouter(prefix="/healthtrack/ai-agents", tags=["HealthTrack - AI Agents"])

# Database dependency
async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'healthtrack_pro')]

# =====================================================
# HEALTH INSIGHTS AI AGENT
# =====================================================

class HealthInsightsRequest(BaseModel):
    patient_id: str
    analysis_type: str = "comprehensive"  # comprehensive, vitals, lab, wearable
    include_recommendations: bool = True

class HealthInsightsResponse(BaseModel):
    insight_id: str
    patient_id: str
    analysis_type: str
    critical_findings: List[str]
    risk_factors: List[Dict[str, Any]]
    trends: Dict[str, Any]
    allopathic_recommendations: List[str]
    ayurvedic_recommendations: List[str]
    lifestyle_recommendations: List[str]
    follow_up_actions: List[str]
    confidence_score: float
    disclaimer: str
    created_at: str

async def get_health_insights_from_ai(patient_data: dict, analysis_type: str) -> dict:
    """Get AI-powered health insights using Emergent LLM"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            raise Exception("EMERGENT_LLM_KEY not configured")
        
        system_message = """You are an advanced AI Health Insights Agent. Your role is to:
1. Analyze patient health data comprehensively
2. Identify critical findings and risk factors
3. Detect health trends and patterns
4. Provide both allopathic (modern medicine) and ayurvedic recommendations
5. Suggest lifestyle improvements
6. Recommend follow-up actions

Always provide evidence-based insights and be cautious about health advice.
Format your response as valid JSON with the following structure:
{
    "critical_findings": ["list of critical health findings"],
    "risk_factors": [{"factor": "name", "severity": "high/medium/low", "description": "details"}],
    "trends": {"improving": [], "declining": [], "stable": []},
    "allopathic_recommendations": ["modern medicine recommendations"],
    "ayurvedic_recommendations": ["ayurvedic/natural recommendations"],
    "lifestyle_recommendations": ["lifestyle improvement suggestions"],
    "follow_up_actions": ["recommended follow-up actions"],
    "confidence_score": 0.85
}"""
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"health-insights-{uuid4()}",
            system_message=system_message
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze the following patient health data and provide comprehensive insights:

Patient Information:
{json.dumps(patient_data, indent=2, default=str)}

Analysis Type: {analysis_type}

Provide detailed health insights in JSON format."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse JSON from response
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        
        return None
    except Exception as e:
        print(f"Health Insights AI Error: {e}")
        return None

@router.post("/health-insights", response_model=HealthInsightsResponse)
async def generate_health_insights(request: HealthInsightsRequest, background_tasks: BackgroundTasks):
    """Generate AI-powered health insights for a patient"""
    db = await get_db()
    
    # Gather patient data
    patient = await db.healthtrack_patients.find_one({"id": request.patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get additional data based on analysis type
    patient_data = {"patient_info": patient}
    
    if request.analysis_type in ["comprehensive", "vitals"]:
        records = await db.healthtrack_medical_records.find(
            {"patient_id": request.patient_id}, {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(10)
        patient_data["medical_records"] = records
    
    if request.analysis_type in ["comprehensive", "lab"]:
        lab_tests = await db.healthtrack_lab_tests.find(
            {"patient_id": request.patient_id}, {"_id": 0}
        ).sort("order_date", -1).limit(10).to_list(10)
        patient_data["lab_tests"] = lab_tests
    
    if request.analysis_type in ["comprehensive", "wearable"]:
        wearable_data = await db.healthtrack_wearable_data.find(
            {"patient_id": request.patient_id}, {"_id": 0}
        ).sort("recorded_at", -1).limit(168).to_list(168)  # 7 days
        
        # Aggregate wearable data
        if wearable_data:
            heart_rates = [d.get("heart_rate", 0) for d in wearable_data if d.get("heart_rate")]
            steps = [d.get("steps", 0) for d in wearable_data if d.get("steps")]
            patient_data["wearable_summary"] = {
                "avg_heart_rate": sum(heart_rates) / len(heart_rates) if heart_rates else 0,
                "total_steps": sum(steps),
                "data_points": len(wearable_data)
            }
    
    # Get AI insights
    ai_insights = await get_health_insights_from_ai(patient_data, request.analysis_type)
    
    # Build response
    insight = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "analysis_type": request.analysis_type,
        "critical_findings": ai_insights.get("critical_findings", []) if ai_insights else ["Analysis completed - consult your physician"],
        "risk_factors": ai_insights.get("risk_factors", []) if ai_insights else [],
        "trends": ai_insights.get("trends", {"improving": [], "declining": [], "stable": []}) if ai_insights else {},
        "allopathic_recommendations": ai_insights.get("allopathic_recommendations", []) if ai_insights else [],
        "ayurvedic_recommendations": ai_insights.get("ayurvedic_recommendations", []) if ai_insights else [],
        "lifestyle_recommendations": ai_insights.get("lifestyle_recommendations", []) if ai_insights else [],
        "follow_up_actions": ai_insights.get("follow_up_actions", []) if ai_insights else [],
        "confidence_score": ai_insights.get("confidence_score", 0.7) if ai_insights else 0.5,
        "disclaimer": "⚠️ This AI-generated analysis is for informational purposes only. Always consult with a qualified healthcare professional before making health decisions.",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Save to database
    await db.healthtrack_ai_insights.insert_one({**insight, "raw_patient_data": patient_data})
    
    return HealthInsightsResponse(**insight)

@router.get("/health-insights/patient/{patient_id}")
async def get_patient_insights(patient_id: str, limit: int = 10):
    """Get historical health insights for a patient"""
    db = await get_db()
    
    insights = await db.healthtrack_ai_insights.find(
        {"patient_id": patient_id},
        {"_id": 0, "raw_patient_data": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"patient_id": patient_id, "insights": insights, "total": len(insights)}

@router.get("/health-insights/critical-alerts")
async def get_critical_alerts(organization_id: Optional[str] = None):
    """Get all critical health alerts across patients"""
    db = await get_db()
    
    # Get recent insights with critical findings
    pipeline = [
        {"$match": {"critical_findings": {"$ne": []}}},
        {"$sort": {"created_at": -1}},
        {"$limit": 50},
        {"$project": {"_id": 0, "raw_patient_data": 0}}
    ]
    
    alerts = await db.healthtrack_ai_insights.aggregate(pipeline).to_list(50)
    
    return {"critical_alerts": alerts, "total": len(alerts)}

# =====================================================
# REVENUE & ANALYTICS AI AGENT
# =====================================================

class RevenueAnalyticsRequest(BaseModel):
    organization_id: Optional[str] = None
    time_period: str = "30d"  # 7d, 30d, 90d, 1y
    analysis_focus: str = "comprehensive"  # comprehensive, usage, revenue, growth

class RevenueInsight(BaseModel):
    category: str
    insight: str
    impact: str
    recommendation: str
    priority: str

async def get_revenue_analytics_from_ai(analytics_data: dict) -> dict:
    """Get AI-powered revenue and usage analytics"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            raise Exception("EMERGENT_LLM_KEY not configured")
        
        system_message = """You are an AI Revenue & Analytics Agent for a healthcare platform. Your role is to:
1. Analyze platform usage patterns and user behavior
2. Identify revenue optimization opportunities
3. Suggest new revenue models and monetization strategies
4. Detect growth opportunities and market trends
5. Provide actionable business recommendations

Format your response as valid JSON with this structure:
{
    "usage_insights": [{"metric": "name", "trend": "up/down/stable", "insight": "details"}],
    "revenue_opportunities": [{"opportunity": "name", "potential_value": "high/medium/low", "implementation": "how to implement"}],
    "new_revenue_models": [{"model": "name", "description": "details", "target_segment": "who", "estimated_revenue": "potential"}],
    "growth_recommendations": [{"area": "name", "recommendation": "details", "priority": "high/medium/low"}],
    "risk_factors": [{"risk": "name", "mitigation": "how to address"}],
    "kpi_summary": {"key_metrics": [], "health_score": 0.85}
}"""
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"revenue-analytics-{uuid4()}",
            system_message=system_message
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze the following platform usage and business data to provide revenue and growth insights:

{json.dumps(analytics_data, indent=2, default=str)}

Provide comprehensive business analytics in JSON format."""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass
        
        return None
    except Exception as e:
        print(f"Revenue Analytics AI Error: {e}")
        return None

@router.post("/revenue-analytics")
async def generate_revenue_analytics(request: RevenueAnalyticsRequest):
    """Generate AI-powered revenue and usage analytics"""
    db = await get_db()
    
    # Calculate time range
    days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    days = days_map.get(request.time_period, 30)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Gather analytics data
    analytics_data = {
        "time_period": request.time_period,
        "analysis_focus": request.analysis_focus
    }
    
    # User statistics
    total_users = await db.users.count_documents({})
    recent_users = await db.users.count_documents({"created_at": {"$gte": cutoff.isoformat()}})
    analytics_data["user_stats"] = {
        "total_users": total_users,
        "new_users_period": recent_users,
        "growth_rate": (recent_users / max(total_users, 1)) * 100
    }
    
    # Patient statistics
    total_patients = await db.healthtrack_patients.count_documents({})
    analytics_data["patient_stats"] = {"total_patients": total_patients}
    
    # Appointment statistics
    total_appointments = await db.healthtrack_appointments.count_documents({})
    completed_appointments = await db.healthtrack_appointments.count_documents({"status": "completed"})
    analytics_data["appointment_stats"] = {
        "total": total_appointments,
        "completed": completed_appointments,
        "completion_rate": (completed_appointments / max(total_appointments, 1)) * 100
    }
    
    # Prescription statistics
    total_prescriptions = await db.healthtrack_prescriptions.count_documents({})
    analytics_data["prescription_stats"] = {"total": total_prescriptions}
    
    # Lab test statistics
    total_lab_tests = await db.healthtrack_lab_tests.count_documents({})
    analytics_data["lab_test_stats"] = {"total": total_lab_tests}
    
    # AI insights usage
    ai_insights_count = await db.healthtrack_ai_insights.count_documents({})
    analytics_data["ai_usage"] = {"total_ai_insights": ai_insights_count}
    
    # Wearable device adoption
    wearable_devices = await db.healthtrack_wearable_devices.count_documents({})
    analytics_data["wearable_adoption"] = {"connected_devices": wearable_devices}
    
    # Get AI analytics
    ai_analytics = await get_revenue_analytics_from_ai(analytics_data)
    
    # Build response
    result = {
        "id": str(uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "time_period": request.time_period,
        "raw_metrics": analytics_data,
        "usage_insights": ai_analytics.get("usage_insights", []) if ai_analytics else [],
        "revenue_opportunities": ai_analytics.get("revenue_opportunities", []) if ai_analytics else [],
        "new_revenue_models": ai_analytics.get("new_revenue_models", []) if ai_analytics else [],
        "growth_recommendations": ai_analytics.get("growth_recommendations", []) if ai_analytics else [],
        "risk_factors": ai_analytics.get("risk_factors", []) if ai_analytics else [],
        "kpi_summary": ai_analytics.get("kpi_summary", {}) if ai_analytics else {}
    }
    
    # Save to database
    await db.platform_analytics.insert_one(result)
    
    return result

@router.get("/revenue-analytics/dashboard")
async def get_analytics_dashboard():
    """Get quick analytics dashboard data"""
    db = await get_db()
    
    # Get latest analytics report
    latest = await db.platform_analytics.find_one(
        {},
        {"_id": 0},
        sort=[("generated_at", -1)]
    )
    
    # Get quick stats
    stats = {
        "total_users": await db.users.count_documents({}),
        "total_patients": await db.healthtrack_patients.count_documents({}),
        "total_appointments": await db.healthtrack_appointments.count_documents({}),
        "total_prescriptions": await db.healthtrack_prescriptions.count_documents({}),
        "ai_insights_generated": await db.healthtrack_ai_insights.count_documents({}),
        "wearable_devices": await db.healthtrack_wearable_devices.count_documents({})
    }
    
    return {
        "current_stats": stats,
        "latest_analysis": latest
    }

@router.get("/revenue-analytics/usage-report")
async def get_usage_report(days: int = 30):
    """Generate a usage report for the specified period"""
    db = await get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    report = {
        "report_id": str(uuid4()),
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "new_patients": await db.healthtrack_patients.count_documents(
                {"created_at": {"$gte": cutoff.isoformat()}}
            ),
            "appointments_scheduled": await db.healthtrack_appointments.count_documents(
                {"created_at": {"$gte": cutoff.isoformat()}}
            ),
            "prescriptions_written": await db.healthtrack_prescriptions.count_documents(
                {"created_at": {"$gte": cutoff.isoformat()}}
            ),
            "lab_tests_ordered": await db.healthtrack_lab_tests.count_documents(
                {"order_date": {"$gte": cutoff.isoformat()}}
            ),
            "ai_analyses_run": await db.healthtrack_ai_insights.count_documents(
                {"created_at": {"$gte": cutoff.isoformat()}}
            )
        }
    }
    
    return report
