"""AI Health Analysis API for HealthTrack Pro
Provides AI-powered health analysis including:
- Lab report analysis
- Health recommendations (Allopathic + Ayurvedic)
- Wearable data insights
- Risk assessment
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import os
import json

router = APIRouter(prefix="/ai", tags=["HealthTrack - AI Health Analysis"])

# Database dependency
async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'test_database')]

# Disclaimer for all AI responses
DISCLAIMER = """⚠️ IMPORTANT MEDICAL DISCLAIMER: This AI-generated analysis is for informational purposes only and should NOT be considered as medical advice. Always consult with a qualified healthcare professional before making any health-related decisions or starting any treatment. The recommendations provided are general in nature and may not be suitable for your specific condition."""

# Models
class LabReportAnalysisRequest(BaseModel):
    patient_id: str
    lab_test_id: Optional[str] = None
    test_type: str = Field(..., description="e.g., CBC, Lipid Panel, Liver Function, Kidney Function")
    results: Dict[str, Any] = Field(..., description="Lab test results as key-value pairs")
    reference_ranges: Optional[Dict[str, str]] = None

class HealthRecommendationRequest(BaseModel):
    patient_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    conditions: List[str] = Field(default=[], description="Existing health conditions")
    symptoms: List[str] = Field(default=[], description="Current symptoms")
    vitals: Optional[Dict[str, Any]] = None
    lifestyle: Optional[Dict[str, Any]] = None

class WearableAnalysisRequest(BaseModel):
    patient_id: str
    device_type: str = Field(default="smartwatch", description="smartwatch, fitness_band, etc.")
    data: Dict[str, Any] = Field(..., description="Wearable data including steps, heart_rate, sleep, etc.")
    period_days: int = Field(default=7, le=30)

class RiskAssessmentRequest(BaseModel):
    patient_id: str
    age: int
    gender: str
    bmi: Optional[float] = None
    smoking: bool = False
    diabetes: bool = False
    hypertension: bool = False
    family_history: List[str] = []
    cholesterol_total: Optional[int] = None
    hdl: Optional[int] = None
    systolic_bp: Optional[int] = None

class AIAnalysisResponse(BaseModel):
    analysis_id: str
    patient_id: str
    analysis_type: str
    summary: str
    findings: List[str]
    allopathic_recommendations: List[str]
    ayurvedic_recommendations: List[str]
    lifestyle_tips: List[str]
    warning_signs: List[str]
    follow_up_suggested: bool
    disclaimer: str
    created_at: str

async def get_ai_analysis(prompt: str) -> Optional[str]:
    """Get AI analysis using Emergent LLM"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            return None
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"health-analysis-{uuid4()}",
            system_message="""You are an expert medical AI assistant. Provide health analysis in JSON format with:
            {
                "summary": "Brief overview",
                "findings": ["list of key findings"],
                "allopathic_recommendations": ["modern medicine recommendations"],
                "ayurvedic_recommendations": ["traditional/natural recommendations"],
                "lifestyle_tips": ["lifestyle improvements"],
                "warning_signs": ["signs to watch for"],
                "follow_up_suggested": true/false
            }
            Be thorough but concise. Always recommend consulting a doctor."""
        ).with_model("openai", "gpt-4o-mini")
        
        response = await chat.send_message(UserMessage(text=prompt))
        return response
    except Exception as e:
        print(f"AI Analysis Error: {e}")
        return None

def parse_ai_response(response: Optional[str], default_summary: str) -> dict:
    """Parse AI response or return fallback"""
    if response:
        try:
            # Try to extract JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
    
    # Return fallback response
    return {
        "summary": default_summary,
        "findings": ["Analysis completed. Please review with your healthcare provider."],
        "allopathic_recommendations": ["Consult with your physician for personalized advice"],
        "ayurvedic_recommendations": ["Consider consulting an Ayurvedic practitioner"],
        "lifestyle_tips": ["Maintain a balanced diet", "Regular exercise recommended", "Ensure adequate sleep"],
        "warning_signs": ["Seek immediate medical attention for any severe symptoms"],
        "follow_up_suggested": True
    }

@router.post("/analyze-lab-report", response_model=AIAnalysisResponse)
async def analyze_lab_report(request: LabReportAnalysisRequest):
    """AI-powered lab report analysis with recommendations"""
    db = await get_db()
    
    # Build analysis prompt
    prompt = f"""Analyze these {request.test_type} lab test results for a patient:
    
    Results: {json.dumps(request.results, indent=2)}
    {f'Reference Ranges: {json.dumps(request.reference_ranges, indent=2)}' if request.reference_ranges else ''}
    
    Provide:
    1. Summary of findings
    2. Any abnormal values and their significance
    3. Both allopathic and ayurvedic recommendations
    4. Lifestyle modifications
    5. Warning signs to watch for
    """
    
    ai_response = await get_ai_analysis(prompt)
    parsed = parse_ai_response(ai_response, f"{request.test_type} analysis completed")
    
    analysis = {
        "analysis_id": str(uuid4()),
        "patient_id": request.patient_id,
        "analysis_type": "lab_report",
        "test_type": request.test_type,
        "results": request.results,
        **parsed,
        "disclaimer": DISCLAIMER,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Store analysis
    await db.ai_health_analyses.insert_one(analysis)
    analysis.pop("_id", None)
    
    return AIAnalysisResponse(**analysis)

@router.post("/health-recommendations", response_model=AIAnalysisResponse)
async def get_health_recommendations(request: HealthRecommendationRequest):
    """Get personalized health recommendations based on patient profile"""
    db = await get_db()
    
    # Build recommendation prompt
    prompt = f"""Provide health recommendations for a patient with:
    
    Age: {request.age or 'Not specified'}
    Gender: {request.gender or 'Not specified'}
    Existing Conditions: {', '.join(request.conditions) if request.conditions else 'None reported'}
    Current Symptoms: {', '.join(request.symptoms) if request.symptoms else 'None reported'}
    Vitals: {json.dumps(request.vitals) if request.vitals else 'Not provided'}
    Lifestyle: {json.dumps(request.lifestyle) if request.lifestyle else 'Not provided'}
    
    Provide comprehensive recommendations including:
    1. Modern medicine approaches
    2. Ayurvedic/traditional remedies
    3. Lifestyle modifications
    4. Warning signs to watch
    """
    
    ai_response = await get_ai_analysis(prompt)
    parsed = parse_ai_response(ai_response, "Health recommendations generated based on your profile")
    
    analysis = {
        "analysis_id": str(uuid4()),
        "patient_id": request.patient_id,
        "analysis_type": "health_recommendations",
        "request_data": request.dict(),
        **parsed,
        "disclaimer": DISCLAIMER,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ai_health_analyses.insert_one(analysis)
    analysis.pop("_id", None)
    
    return AIAnalysisResponse(**analysis)

@router.post("/analyze-wearable-data", response_model=AIAnalysisResponse)
async def analyze_wearable_data(request: WearableAnalysisRequest):
    """Analyze data from wearable devices (smartwatch, fitness bands)"""
    db = await get_db()
    
    prompt = f"""Analyze this {request.device_type} data from the past {request.period_days} days:
    
    Data: {json.dumps(request.data, indent=2)}
    
    Provide insights on:
    1. Activity levels and fitness
    2. Sleep quality
    3. Heart rate patterns
    4. Any concerning patterns
    5. Recommendations for improvement
    """
    
    ai_response = await get_ai_analysis(prompt)
    parsed = parse_ai_response(ai_response, f"{request.device_type} data analysis completed")
    
    analysis = {
        "analysis_id": str(uuid4()),
        "patient_id": request.patient_id,
        "analysis_type": "wearable_analysis",
        "device_type": request.device_type,
        "period_days": request.period_days,
        **parsed,
        "disclaimer": DISCLAIMER,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ai_health_analyses.insert_one(analysis)
    analysis.pop("_id", None)
    
    return AIAnalysisResponse(**analysis)

@router.post("/risk-assessment")
async def cardiovascular_risk_assessment(request: RiskAssessmentRequest):
    """Calculate cardiovascular risk score with AI insights"""
    db = await get_db()
    
    # Simple risk calculation (Framingham-inspired)
    risk_score = 0
    risk_factors = []
    
    # Age factor
    if request.age >= 65:
        risk_score += 3
        risk_factors.append("Age 65+")
    elif request.age >= 55:
        risk_score += 2
        risk_factors.append("Age 55-64")
    elif request.age >= 45:
        risk_score += 1
        risk_factors.append("Age 45-54")
    
    # Gender
    if request.gender.lower() == 'male':
        risk_score += 1
        risk_factors.append("Male gender")
    
    # BMI
    if request.bmi:
        if request.bmi >= 30:
            risk_score += 2
            risk_factors.append("Obesity (BMI >= 30)")
        elif request.bmi >= 25:
            risk_score += 1
            risk_factors.append("Overweight (BMI >= 25)")
    
    # Smoking
    if request.smoking:
        risk_score += 2
        risk_factors.append("Smoking")
    
    # Diabetes
    if request.diabetes:
        risk_score += 2
        risk_factors.append("Diabetes")
    
    # Hypertension
    if request.hypertension:
        risk_score += 2
        risk_factors.append("Hypertension")
    
    # Family history
    if request.family_history:
        risk_score += len(request.family_history)
        risk_factors.extend([f"Family history: {h}" for h in request.family_history])
    
    # Blood pressure
    if request.systolic_bp:
        if request.systolic_bp >= 160:
            risk_score += 2
            risk_factors.append("High systolic BP (>= 160)")
        elif request.systolic_bp >= 140:
            risk_score += 1
            risk_factors.append("Elevated systolic BP (>= 140)")
    
    # Cholesterol
    if request.cholesterol_total:
        if request.cholesterol_total >= 240:
            risk_score += 2
            risk_factors.append("High cholesterol (>= 240)")
        elif request.cholesterol_total >= 200:
            risk_score += 1
            risk_factors.append("Borderline high cholesterol (>= 200)")
    
    # HDL (protective factor)
    if request.hdl:
        if request.hdl >= 60:
            risk_score -= 1
            risk_factors.append("High HDL (protective)")
        elif request.hdl < 40:
            risk_score += 1
            risk_factors.append("Low HDL (< 40)")
    
    # Determine risk category
    if risk_score >= 8:
        risk_category = "High"
        ten_year_risk = "20%+"
    elif risk_score >= 5:
        risk_category = "Moderate"
        ten_year_risk = "10-20%"
    elif risk_score >= 3:
        risk_category = "Low-Moderate"
        ten_year_risk = "5-10%"
    else:
        risk_category = "Low"
        ten_year_risk = "<5%"
    
    result = {
        "assessment_id": str(uuid4()),
        "patient_id": request.patient_id,
        "risk_score": risk_score,
        "risk_category": risk_category,
        "ten_year_risk_estimate": ten_year_risk,
        "risk_factors": risk_factors,
        "recommendations": [
            "Regular cardiovascular screenings" if risk_score >= 5 else "Annual health checkups",
            "Heart-healthy diet (Mediterranean or DASH)" if risk_score >= 3 else "Maintain balanced diet",
            "150 minutes moderate exercise per week",
            "Quit smoking" if request.smoking else "Avoid smoking",
            "Blood pressure monitoring" if request.hypertension else "Regular BP checks",
            "Diabetes management" if request.diabetes else "Blood sugar monitoring"
        ],
        "disclaimer": DISCLAIMER,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ai_health_analyses.insert_one(result)
    result.pop("_id", None)
    
    return result

@router.get("/analyses/{patient_id}")
async def get_patient_analyses(
    patient_id: str,
    analysis_type: Optional[str] = None,
    limit: int = 20
):
    """Get AI analysis history for a patient"""
    db = await get_db()
    
    query = {"patient_id": patient_id}
    if analysis_type:
        query["analysis_type"] = analysis_type
    
    analyses = await db.ai_health_analyses.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "patient_id": patient_id,
        "total": len(analyses),
        "analyses": analyses
    }

@router.get("/analyses/detail/{analysis_id}")
async def get_analysis_detail(analysis_id: str):
    """Get a specific AI analysis by ID"""
    db = await get_db()
    
    analysis = await db.ai_health_analyses.find_one(
        {"analysis_id": analysis_id},
        {"_id": 0}
    )
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis
