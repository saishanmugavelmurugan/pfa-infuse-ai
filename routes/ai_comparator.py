"""
AI-Powered Health Scheme Comparator Service
Uses Emergent LLM Key for GPT-powered analysis and recommendations
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/ai-comparator", tags=["AI Health Scheme Comparator"])

# Database connection
async def get_db():
    import dependencies
    return dependencies.get_db()

# Pydantic Models
class ComparisonRequest(BaseModel):
    scheme_ids: List[str]
    user_context: Optional[str] = None  # e.g., "family of 4, chronic conditions"
    focus_areas: Optional[List[str]] = None  # e.g., ["cost", "coverage", "accessibility"]

class BestPracticesRequest(BaseModel):
    country_code: str
    scheme_type: Optional[str] = None  # government, private, hybrid
    focus_area: Optional[str] = None  # e.g., "chronic care", "maternal health"

class SchemeRecommendationRequest(BaseModel):
    user_profile: Dict[str, Any]  # age, income, family_size, health_conditions, country
    preferences: Optional[List[str]] = None  # low_cost, comprehensive, digital_first

# Import health schemes data
from routes.health_schemes import GLOBAL_HEALTH_SCHEMES

async def get_llm_response(prompt: str, system_message: str) -> str:
    """Get response from LLM using Emergent integration"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            return "AI analysis unavailable. Please configure EMERGENT_LLM_KEY."
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"health-scheme-{str(uuid4())[:8]}",
            system_message=system_message
        ).with_model("openai", "gpt-4o")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        return f"AI analysis error: {str(e)}"

@router.post("/compare")
async def ai_compare_schemes(request: ComparisonRequest):
    """
    AI-powered comparison of health schemes with detailed analysis
    """
    db = await get_db()
    
    # Gather scheme data
    schemes_data = []
    for scheme_id in request.scheme_ids:
        # Search in pre-populated schemes
        for country_schemes in GLOBAL_HEALTH_SCHEMES.values():
            for scheme in country_schemes:
                if scheme["id"] == scheme_id:
                    schemes_data.append(scheme)
                    break
    
    if len(schemes_data) < 2:
        raise HTTPException(status_code=400, detail="At least 2 valid schemes required")
    
    # Build prompt for AI
    schemes_text = "\n\n".join([
        f"**{s['name']} ({s['country_name']})**\n"
        f"Type: {s.get('scheme_type', 'N/A')}\n"
        f"Coverage: {s.get('coverage_type', 'N/A')}\n"
        f"Description: {s.get('description', 'N/A')}\n"
        f"Benefits: {', '.join(s.get('benefits', ['N/A']))}\n"
        f"Limitations: {', '.join(s.get('limitations', ['N/A']))}"
        for s in schemes_data
    ])
    
    focus = ", ".join(request.focus_areas) if request.focus_areas else "overall coverage, cost-effectiveness, accessibility"
    context = f"\nUser context: {request.user_context}" if request.user_context else ""
    
    prompt = f"""Compare the following health schemes focusing on {focus}:{context}

{schemes_text}

Provide:
1. Side-by-side comparison table (use markdown)
2. Key differences highlighted
3. Pros and cons of each
4. Recommendation based on different user profiles (young professional, family, elderly, chronic condition patients)
5. Best practices each scheme implements that others could adopt"""

    system_message = """You are an expert health policy analyst specializing in global healthcare systems. 
Provide detailed, accurate comparisons of health schemes with actionable insights. 
Be objective and highlight both strengths and weaknesses. Format your response in clear markdown."""

    ai_analysis = await get_llm_response(prompt, system_message)
    
    # Store comparison for analytics
    comparison_record = {
        "id": str(uuid4()),
        "schemes_compared": [s["id"] for s in schemes_data],
        "focus_areas": request.focus_areas,
        "user_context": request.user_context,
        "ai_analysis": ai_analysis,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.scheme_comparisons.insert_one({**comparison_record})
    
    return {
        "comparison_id": comparison_record["id"],
        "schemes": [{"id": s["id"], "name": s["name"], "country": s["country_name"]} for s in schemes_data],
        "ai_analysis": ai_analysis,
        "raw_data": schemes_data
    }

@router.post("/best-practices")
async def get_best_practices(request: BestPracticesRequest):
    """
    AI-generated best practices report for a specific region's health system
    """
    db = await get_db()
    
    # Get schemes for the country
    schemes = GLOBAL_HEALTH_SCHEMES.get(request.country_code.upper(), [])
    
    if not schemes:
        # Check for nearby/similar countries for comparison
        all_schemes = []
        for country_schemes in GLOBAL_HEALTH_SCHEMES.values():
            all_schemes.extend(country_schemes)
        schemes = all_schemes[:5]  # Use top 5 as examples
    
    schemes_text = "\n\n".join([
        f"**{s['name']} ({s['country_name']})**\n{s.get('description', 'N/A')}"
        for s in schemes
    ])
    
    focus = f" with focus on {request.focus_area}" if request.focus_area else ""
    scheme_type = f" for {request.scheme_type} schemes" if request.scheme_type else ""
    
    prompt = f"""Analyze health system best practices{scheme_type}{focus} based on these examples:

{schemes_text}

Provide:
1. Top 10 global best practices in healthcare scheme design
2. Innovative approaches from different countries
3. Common pitfalls to avoid
4. Technology integration best practices
5. Recommendations for emerging markets
6. Patient-centric design principles
7. Cost containment strategies that maintain quality
8. Digital health integration examples"""

    system_message = """You are a senior health policy consultant with experience advising governments 
on healthcare reform. Provide evidence-based best practices with real-world examples. 
Be specific and actionable. Format in clear sections with bullet points."""

    ai_analysis = await get_llm_response(prompt, system_message)
    
    # Store for analytics
    report_record = {
        "id": str(uuid4()),
        "country_code": request.country_code,
        "scheme_type": request.scheme_type,
        "focus_area": request.focus_area,
        "ai_analysis": ai_analysis,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.best_practices_reports.insert_one({**report_record})
    
    return {
        "report_id": report_record["id"],
        "country_code": request.country_code,
        "best_practices": ai_analysis,
        "reference_schemes": [{"id": s["id"], "name": s["name"]} for s in schemes]
    }

@router.post("/recommend")
async def recommend_scheme(request: SchemeRecommendationRequest):
    """
    AI-powered scheme recommendation based on user profile
    """
    db = await get_db()
    
    profile = request.user_profile
    country = profile.get("country", "").upper()
    
    # Get relevant schemes
    country_schemes = GLOBAL_HEALTH_SCHEMES.get(country, [])
    
    # Also get similar countries' schemes for comparison
    all_schemes = []
    for c_code, schemes in GLOBAL_HEALTH_SCHEMES.items():
        all_schemes.extend(schemes)
    
    available_schemes = country_schemes if country_schemes else all_schemes[:10]
    
    schemes_text = "\n".join([
        f"- {s['name']} ({s['country_name']}): {s.get('description', '')[:200]}..."
        for s in available_schemes
    ])
    
    preferences = ", ".join(request.preferences) if request.preferences else "comprehensive coverage"
    
    prompt = f"""Based on this user profile, recommend the most suitable health scheme:

**User Profile:**
- Age: {profile.get('age', 'Not specified')}
- Income Level: {profile.get('income_level', 'Not specified')}
- Family Size: {profile.get('family_size', 'Not specified')}
- Health Conditions: {profile.get('health_conditions', 'None specified')}
- Country: {profile.get('country', 'Not specified')}
- Preferences: {preferences}

**Available Schemes:**
{schemes_text}

Provide:
1. Top 3 recommended schemes with reasoning
2. Coverage analysis for this user's specific needs
3. Estimated out-of-pocket costs
4. Enrollment steps
5. Alternative options if primary choice isn't available
6. Tips to maximize benefits"""

    system_message = """You are a healthcare navigator helping individuals choose the best health coverage. 
Provide personalized recommendations based on their specific situation. Be practical and considerate of 
their financial and health circumstances. Include specific action steps."""

    ai_recommendation = await get_llm_response(prompt, system_message)
    
    # Store recommendation
    rec_record = {
        "id": str(uuid4()),
        "user_profile_hash": str(hash(str(profile))),  # Privacy: don't store actual profile
        "country": country,
        "preferences": request.preferences,
        "ai_recommendation": ai_recommendation,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.scheme_recommendations.insert_one({**rec_record})
    
    return {
        "recommendation_id": rec_record["id"],
        "recommendation": ai_recommendation,
        "available_schemes": [{"id": s["id"], "name": s["name"], "country": s["country_name"]} for s in available_schemes]
    }

@router.get("/analytics")
async def get_comparator_analytics():
    """Get usage analytics for the AI comparator (admin only)"""
    db = await get_db()
    
    # Count comparisons
    comparisons_count = await db.scheme_comparisons.count_documents({})
    
    # Count best practices reports
    reports_count = await db.best_practices_reports.count_documents({})
    
    # Count recommendations
    recommendations_count = await db.scheme_recommendations.count_documents({})
    
    # Get popular schemes compared
    pipeline = [
        {"$unwind": "$schemes_compared"},
        {"$group": {"_id": "$schemes_compared", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    popular_schemes = await db.scheme_comparisons.aggregate(pipeline).to_list(10)
    
    return {
        "total_comparisons": comparisons_count,
        "total_best_practices_reports": reports_count,
        "total_recommendations": recommendations_count,
        "popular_schemes_compared": popular_schemes,
        "ai_model": "gpt-4o",
        "provider": "openai"
    }

@router.get("/government-consultation/{country_code}")
async def get_government_consultation(country_code: str, focus: Optional[str] = None):
    """
    Generate a government consultation report with recommendations
    This is specifically for admin/internal use to prepare policy recommendations
    """
    db = await get_db()
    
    # Get country's current schemes
    country_schemes = GLOBAL_HEALTH_SCHEMES.get(country_code.upper(), [])
    
    # Get all schemes for comparison
    all_schemes = []
    for c_code, schemes in GLOBAL_HEALTH_SCHEMES.items():
        if c_code != country_code.upper():
            all_schemes.extend(schemes)
    
    current_schemes_text = "\n".join([
        f"**{s['name']}**: {s.get('description', 'N/A')}"
        for s in country_schemes
    ]) if country_schemes else "No current schemes documented"
    
    reference_schemes_text = "\n".join([
        f"- {s['name']} ({s['country_name']}): {s.get('coverage_type', 'N/A')} coverage"
        for s in all_schemes[:15]
    ])
    
    focus_text = f" focusing on {focus}" if focus else ""
    
    prompt = f"""Prepare a government consultation report for {country_code.upper()}{focus_text}:

**Current Health Schemes in {country_code.upper()}:**
{current_schemes_text}

**Reference Schemes from Other Countries:**
{reference_schemes_text}

Generate a comprehensive consultation report including:

1. **Executive Summary** - Key findings and recommendations (2-3 paragraphs)

2. **Current State Analysis**
   - Strengths of current system
   - Gaps and challenges
   - Population coverage statistics (estimate)

3. **International Benchmarking**
   - Top 5 relevant international models to consider
   - Lessons learned from each

4. **Recommended Reforms**
   - Short-term (0-1 year): Quick wins
   - Medium-term (1-3 years): Structural improvements
   - Long-term (3-5 years): Transformational changes

5. **Implementation Roadmap**
   - Phase 1 priorities
   - Resource requirements
   - Key stakeholders

6. **Risk Assessment**
   - Political risks
   - Financial risks
   - Operational risks
   - Mitigation strategies

7. **Cost-Benefit Analysis**
   - Estimated investment required
   - Expected outcomes
   - ROI timeline

8. **Technology Integration Recommendations**
   - Digital health platforms
   - Data interoperability
   - AI/ML applications

Please format this as a professional government consultation document."""

    system_message = """You are a senior healthcare policy advisor preparing a formal government 
consultation document. Write in a professional, objective tone suitable for government officials 
and policymakers. Include specific recommendations with justifications. Use formal document 
structure with clear headings and bullet points."""

    ai_report = await get_llm_response(prompt, system_message)
    
    # Store report
    report_record = {
        "id": str(uuid4()),
        "type": "government_consultation",
        "country_code": country_code.upper(),
        "focus": focus,
        "report": ai_report,
        "current_schemes": [s["id"] for s in country_schemes],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "system"
    }
    await db.government_consultations.insert_one({**report_record})
    
    return {
        "report_id": report_record["id"],
        "country_code": country_code.upper(),
        "consultation_report": ai_report,
        "current_schemes": country_schemes,
        "reference_count": len(all_schemes[:15])
    }
