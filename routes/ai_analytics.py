from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import asyncio
from uuid import uuid4

router = APIRouter(prefix="/healthtrack/ai-analytics", tags=["HealthTrack - AI Analytics"])

# Database dependency - defined locally to avoid circular imports
async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'test_database')]

class LabTestAnalysisRequest(BaseModel):
    lab_test_id: str
    patient_id: str

class WearableDataRequest(BaseModel):
    patient_id: str
    device_type: str = "apple_watch"
    days: int = 7

class AIAnalysisResponse(BaseModel):
    analysis_id: str
    patient_id: str
    analysis_type: str
    summary: str
    allopathic_recommendations: List[str]
    ayurvedic_recommendations: List[str]
    lifestyle_tips: List[str]
    warning_signs: List[str]
    disclaimer: str
    created_at: str

DISCLAIMER = """⚠️ IMPORTANT MEDICAL DISCLAIMER: This AI-generated analysis is for informational purposes only and should NOT be considered as medical advice. Always consult with a qualified healthcare professional before making any health-related decisions or starting any treatment. The recommendations provided are general in nature and may not be suitable for your specific condition."""

async def get_ai_analysis(prompt: str) -> str:
    """Get AI analysis using Emergent LLM"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            raise Exception("EMERGENT_LLM_KEY not configured")
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"health-analysis-{uuid4()}",
            system_message="""You are an expert medical AI assistant specializing in health analytics. 
            You provide comprehensive health analysis including both modern medicine (allopathic) and traditional 
            Ayurvedic perspectives. Always be thorough but concise. Format your response as JSON with the following structure:
            {
                "summary": "Brief overview of the health data",
                "allopathic_recommendations": ["list of modern medicine recommendations"],
                "ayurvedic_recommendations": ["list of ayurvedic/natural recommendations"],
                "lifestyle_tips": ["list of lifestyle improvement tips"],
                "warning_signs": ["list of warning signs to watch for"]
            }
            Always remind patients to consult their doctor."""
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        print(f"AI Analysis Error: {e}")
        # Return fallback analysis
        return None

def parse_ai_response(response: str) -> dict:
    """Parse AI response into structured format"""
    import json
    try:
        # Try to extract JSON from the response
        if response:
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
    except:
        pass
    
    # Return default structure if parsing fails
    return {
        "summary": "Analysis completed. Please review the detailed results below.",
        "allopathic_recommendations": ["Consult with your physician for personalized advice"],
        "ayurvedic_recommendations": ["Consider incorporating balanced diet and yoga"],
        "lifestyle_tips": ["Maintain regular sleep schedule", "Stay hydrated"],
        "warning_signs": ["Consult doctor if symptoms worsen"]
    }

@router.post("/analyze-lab-report")
async def analyze_lab_report(request: LabTestAnalysisRequest):
    """AI-powered analysis of lab test results with allopathic and ayurvedic recommendations"""
    
    # Get database connection
    db = await get_db()
    
    # Get lab test data
    lab_test = await db.healthtrack_lab_tests.find_one(
        {"id": request.lab_test_id},
        {"_id": 0}
    )
    
    if not lab_test:
        raise HTTPException(status_code=404, detail="Lab test not found")
    
    # Get patient info
    patient = await db.healthtrack_patients.find_one(
        {"id": request.patient_id},
        {"_id": 0}
    )
    
    patient_info = ""
    if patient:
        patient_info = f"""Patient: {patient.get('first_name', '')} {patient.get('last_name', '')}
        Age: {patient.get('date_of_birth', 'Unknown')}
        Gender: {patient.get('gender', 'Unknown')}
        Medical History: {patient.get('medical_history', {})}"""
    
    # Build analysis prompt
    prompt = f"""Analyze the following lab test results and provide comprehensive health recommendations:
    
    {patient_info}
    
    Lab Test: {lab_test.get('test_name', 'Unknown Test')}
    Test Date: {lab_test.get('order_date', 'Unknown')}
    Status: {lab_test.get('status', 'Unknown')}
    
    Results:
    {lab_test.get('results', {})}
    
    Please provide:
    1. A brief summary of the results
    2. Allopathic (modern medicine) recommendations
    3. Ayurvedic/natural health recommendations
    4. Lifestyle tips for improvement
    5. Warning signs to watch for
    
    Format your response as JSON."""
    
    # Get AI analysis
    ai_response = await get_ai_analysis(prompt)
    analysis_data = parse_ai_response(ai_response) if ai_response else parse_ai_response(None)
    
    # Create analysis record
    analysis = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "lab_test_id": request.lab_test_id,
        "analysis_type": "lab_report",
        "summary": analysis_data.get("summary", "Analysis completed"),
        "allopathic_recommendations": analysis_data.get("allopathic_recommendations", []),
        "ayurvedic_recommendations": analysis_data.get("ayurvedic_recommendations", []),
        "lifestyle_tips": analysis_data.get("lifestyle_tips", []),
        "warning_signs": analysis_data.get("warning_signs", []),
        "disclaimer": DISCLAIMER,
        "raw_ai_response": ai_response,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Save analysis
    await db.healthtrack_ai_analyses.insert_one(analysis)
    del analysis["raw_ai_response"]  # Don't return raw response
    
    return analysis

@router.post("/analyze-wearable-data")
async def analyze_wearable_data(request: WearableDataRequest):
    """AI-powered analysis of wearable device health data"""
    
    # Get database connection
    db = await get_db()
    
    # Get wearable data
    wearable_data = await db.healthtrack_wearable_data.find(
        {"patient_id": request.patient_id, "device_type": request.device_type},
        {"_id": 0}
    ).sort("recorded_at", -1).limit(request.days * 24).to_list(1000)  # Hourly data
    
    if not wearable_data:
        raise HTTPException(status_code=404, detail="No wearable data found for this patient")
    
    # Get patient info
    patient = await db.healthtrack_patients.find_one(
        {"id": request.patient_id},
        {"_id": 0}
    )
    
    # Aggregate data for analysis
    heart_rates = [d.get("heart_rate", 0) for d in wearable_data if d.get("heart_rate")]
    steps = [d.get("steps", 0) for d in wearable_data if d.get("steps")]
    sleep_hours = [d.get("sleep_hours", 0) for d in wearable_data if d.get("sleep_hours")]
    calories = [d.get("calories_burned", 0) for d in wearable_data if d.get("calories_burned")]
    
    avg_heart_rate = sum(heart_rates) / len(heart_rates) if heart_rates else 0
    total_steps = sum(steps)
    avg_sleep = sum(sleep_hours) / len(sleep_hours) if sleep_hours else 0
    total_calories = sum(calories)
    
    # Build analysis prompt
    prompt = f"""Analyze the following wearable health device data and provide comprehensive health recommendations:
    
    Patient: {patient.get('first_name', '')} {patient.get('last_name', '')} if patient else 'Unknown'
    Device: {request.device_type}
    Period: Last {request.days} days
    
    Health Metrics:
    - Average Heart Rate: {avg_heart_rate:.1f} bpm
    - Heart Rate Range: {min(heart_rates) if heart_rates else 0} - {max(heart_rates) if heart_rates else 0} bpm
    - Total Steps: {total_steps:,}
    - Average Daily Steps: {total_steps // request.days:,}
    - Average Sleep: {avg_sleep:.1f} hours/night
    - Total Calories Burned: {total_calories:,}
    
    Please provide:
    1. A summary of the health trends
    2. Allopathic recommendations for cardiovascular health
    3. Ayurvedic recommendations for holistic wellness
    4. Lifestyle tips for improvement
    5. Warning signs to watch for
    
    Format your response as JSON."""
    
    # Get AI analysis
    ai_response = await get_ai_analysis(prompt)
    analysis_data = parse_ai_response(ai_response) if ai_response else parse_ai_response(None)
    
    # Create analysis record
    analysis = {
        "id": str(uuid4()),
        "patient_id": request.patient_id,
        "analysis_type": "wearable_data",
        "device_type": request.device_type,
        "metrics": {
            "avg_heart_rate": round(avg_heart_rate, 1),
            "heart_rate_range": [min(heart_rates) if heart_rates else 0, max(heart_rates) if heart_rates else 0],
            "total_steps": total_steps,
            "avg_daily_steps": total_steps // request.days if request.days > 0 else 0,
            "avg_sleep_hours": round(avg_sleep, 1),
            "total_calories": total_calories
        },
        "summary": analysis_data.get("summary", "Analysis completed"),
        "allopathic_recommendations": analysis_data.get("allopathic_recommendations", []),
        "ayurvedic_recommendations": analysis_data.get("ayurvedic_recommendations", []),
        "lifestyle_tips": analysis_data.get("lifestyle_tips", []),
        "warning_signs": analysis_data.get("warning_signs", []),
        "disclaimer": DISCLAIMER,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Save analysis
    await db.healthtrack_ai_analyses.insert_one({**analysis, "raw_ai_response": ai_response})
    
    return analysis

@router.get("/patient/{patient_id}/analyses")
async def get_patient_analyses(patient_id: str):
    """Get all AI analyses for a patient"""
    # Get database connection
    db = await get_db()
    
    analyses = await db.healthtrack_ai_analyses.find(
        {"patient_id": patient_id},
        {"_id": 0, "raw_ai_response": 0}
    ).sort("created_at", -1).to_list(50)
    
    return {"analyses": analyses, "total": len(analyses)}

@router.get("/comprehensive/{patient_id}")
async def get_comprehensive_health_analysis(patient_id: str):
    """Get comprehensive health analysis combining all data sources"""
    
    # Get database connection
    db = await get_db()
    
    # Get patient
    patient = await db.healthtrack_patients.find_one(
        {"id": patient_id},
        {"_id": 0}
    )
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get recent vitals
    medical_records = await db.healthtrack_medical_records.find(
        {"patient_id": patient_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    # Get lab tests
    lab_tests = await db.healthtrack_lab_tests.find(
        {"patient_id": patient_id},
        {"_id": 0}
    ).sort("order_date", -1).limit(5).to_list(5)
    
    # Get wearable data summary
    wearable_data = await db.healthtrack_wearable_data.find(
        {"patient_id": patient_id},
        {"_id": 0}
    ).sort("recorded_at", -1).limit(168).to_list(168)  # 7 days hourly
    
    # Build comprehensive prompt
    vitals_summary = ""
    if medical_records:
        latest = medical_records[0]
        vitals = latest.get('vitals', {})
        vitals_summary = f"""Latest Vitals:
        - Blood Pressure: {vitals.get('blood_pressure_systolic', 'N/A')}/{vitals.get('blood_pressure_diastolic', 'N/A')} mmHg
        - Heart Rate: {vitals.get('heart_rate', 'N/A')} bpm
        - Blood Sugar: {vitals.get('blood_sugar', 'N/A')} mg/dL
        - Temperature: {vitals.get('temperature', 'N/A')}°F"""
    
    lab_summary = ""
    if lab_tests:
        lab_summary = "Recent Lab Tests:\n"
        for test in lab_tests[:3]:
            lab_summary += f"- {test.get('test_name', 'Unknown')}: {test.get('status', 'Unknown')}\n"
            if test.get('results'):
                for key, value in test.get('results', {}).items():
                    lab_summary += f"  {key}: {value}\n"
    
    wearable_summary = ""
    if wearable_data:
        heart_rates = [d.get("heart_rate", 0) for d in wearable_data if d.get("heart_rate")]
        steps = [d.get("steps", 0) for d in wearable_data if d.get("steps")]
        if heart_rates:
            wearable_summary = f"""Wearable Device Data (7 days):
            - Average Heart Rate: {sum(heart_rates)/len(heart_rates):.1f} bpm
            - Total Steps: {sum(steps):,}
            - Average Daily Steps: {sum(steps)//7:,}"""
    
    prompt = f"""Provide a comprehensive health analysis for this patient:
    
    Patient: {patient.get('first_name', '')} {patient.get('last_name', '')}
    DOB: {patient.get('date_of_birth', 'Unknown')}
    Gender: {patient.get('gender', 'Unknown')}
    
    Medical History:
    - Chronic Conditions: {patient.get('medical_history', {}).get('chronic_conditions', [])}
    - Allergies: {patient.get('medical_history', {}).get('allergies', [])}
    - Current Medications: {patient.get('medical_history', {}).get('current_medications', [])}
    
    {vitals_summary}
    
    {lab_summary}
    
    {wearable_summary}
    
    Provide a holistic health assessment with:
    1. Overall health summary
    2. Allopathic (modern medicine) recommendations
    3. Ayurvedic health recommendations based on likely dosha imbalances
    4. Lifestyle and dietary tips
    5. Warning signs requiring immediate medical attention
    
    Format as JSON."""
    
    # Get AI analysis
    ai_response = await get_ai_analysis(prompt)
    analysis_data = parse_ai_response(ai_response) if ai_response else parse_ai_response(None)
    
    return {
        "patient_id": patient_id,
        "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}",
        "analysis_type": "comprehensive",
        "summary": analysis_data.get("summary", "Comprehensive analysis completed"),
        "allopathic_recommendations": analysis_data.get("allopathic_recommendations", []),
        "ayurvedic_recommendations": analysis_data.get("ayurvedic_recommendations", []),
        "lifestyle_tips": analysis_data.get("lifestyle_tips", []),
        "warning_signs": analysis_data.get("warning_signs", []),
        "disclaimer": DISCLAIMER,
        "data_sources": {
            "vitals": len(medical_records) > 0,
            "lab_tests": len(lab_tests),
            "wearable_data_points": len(wearable_data)
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
