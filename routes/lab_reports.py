from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import os
import base64
import asyncio
import dependencies

# Lazy import - only import when needed (saves 1.3s on startup)
# from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

router = APIRouter()

# LLM Key will be accessed when needed (not at import time)

# Models
class LabReportAnalysis(BaseModel):
    report_id: str
    user_id: str
    file_name: str
    file_type: str
    upload_date: datetime
    analysis: Dict
    detected_conditions: List[str]
    abnormal_values: List[Dict]
    severity: str  # "routine", "moderate", "urgent"
    simple_explanation: str
    recommendations: List[str]
    suggested_doctors: List[Dict]
    ayurveda_recommendations: Optional[Dict] = None

class ReportUploadResponse(BaseModel):
    report_id: str
    message: str
    file_name: str

@router.post("/upload-report")
async def upload_lab_report(file: UploadFile = File(...), user_id: str = "demo-user"):
    """
    Upload lab report (PDF or Image) for AI analysis.
    """
    # Validate file type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not supported. Allowed: PDF, JPG, PNG. Got: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    
    # Generate report ID
    from uuid import uuid4
    report_id = str(uuid4())
    
    # Store file metadata and content in MongoDB
    db = dependencies.get_database()
    
    # Convert file to base64 for storage
    file_base64 = base64.b64encode(content).decode('utf-8')
    
    report_doc = {
        "report_id": report_id,
        "user_id": user_id,
        "file_name": file.filename,
        "file_type": file.content_type,
        "file_data": file_base64,  # Store in DB for now (should use S3 in production)
        "upload_date": datetime.utcnow().isoformat(),
        "analysis_status": "pending",
        "analysis": None
    }
    
    await db.lab_reports.insert_one(report_doc)
    
    # Trigger background analysis
    asyncio.create_task(analyze_report_background(report_id, file_base64, file.content_type, user_id))
    
    return ReportUploadResponse(
        report_id=report_id,
        message="Report uploaded successfully. Analysis in progress...",
        file_name=file.filename
    )

async def analyze_report_background(report_id: str, file_base64: str, file_type: str, user_id: str):
    """
    Background task to analyze lab report using Gemini AI.
    """
    try:
        db = dependencies.get_database()
        
        # Lazy import AI library only when actually needed
        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType, ImageContent
        
        # Initialize Gemini chat (get key at runtime)
        emergent_llm_key = os.environ.get('EMERGENT_LLM_KEY', '')
        chat = LlmChat(
            api_key=emergent_llm_key,
            session_id=f"lab-report-{report_id}",
            system_message="You are a medical AI assistant specialized in analyzing lab reports and translating complex medical terminology into simple English for patients."
        ).with_model("gemini", "gemini-2.0-flash")
        
        # Create prompt for lab report analysis
        analysis_prompt = """Analyze this lab report and provide:
1. Detected medical conditions or concerns
2. List of abnormal values with normal ranges
3. Severity level (routine/moderate/urgent)
4. Simple explanation in plain English for a patient
5. Health recommendations
6. Suggested medical specialties to consult

Format your response as JSON with these keys:
- detected_conditions: array of condition names
- abnormal_values: array of {parameter, value, normal_range, status}
- severity: "routine", "moderate", or "urgent"
- simple_explanation: patient-friendly explanation
- recommendations: array of health recommendations
- suggested_specialties: array of medical specialties"""
        
        # Determine mime type
        mime_type = "image/jpeg" if "image" in file_type else "application/pdf"
        
        # Create message with file attachment
        # For images, use base64
        if "image" in file_type:
            file_content = ImageContent(image_base64=file_base64)
        else:
            # For PDF, save temporarily and use file path
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(base64.b64decode(file_base64))
                tmp_path = tmp.name
            
            file_content = FileContentWithMimeType(
                file_path=tmp_path,
                mime_type="application/pdf"
            )
        
        user_message = UserMessage(
            text=analysis_prompt,
            file_contents=[file_content]
        )
        
        # Get AI analysis
        response = await chat.send_message(user_message)
        
        # Parse AI response
        import json
        # Extract JSON from response (might be wrapped in markdown)
        response_text = response.strip()
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        try:
            analysis = json.loads(response_text)
        except:
            # If JSON parsing fails, create structured response from text
            analysis = {
                "detected_conditions": [],
                "abnormal_values": [],
                "severity": "routine",
                "simple_explanation": response_text,
                "recommendations": ["Consult with your doctor for detailed interpretation"],
                "suggested_specialties": ["General Physician"]
            }
        
        # Get doctor recommendations based on specialties
        suggested_doctors = await get_doctor_recommendations(
            specialties=analysis.get("suggested_specialties", []),
            severity=analysis.get("severity", "routine")
        )
        
        # Get Ayurveda recommendations
        ayurveda_recommendations = await get_ayurveda_recommendations(
            conditions=analysis.get("detected_conditions", [])
        )
        
        # Update report in database
        await db.lab_reports.update_one(
            {"report_id": report_id},
            {"$set": {
                "analysis_status": "completed",
                "analysis": analysis,
                "detected_conditions": analysis.get("detected_conditions", []),
                "abnormal_values": analysis.get("abnormal_values", []),
                "severity": analysis.get("severity", "routine"),
                "simple_explanation": analysis.get("simple_explanation", ""),
                "recommendations": analysis.get("recommendations", []),
                "suggested_doctors": suggested_doctors,
                "ayurveda_recommendations": ayurveda_recommendations,
                "analysis_date": datetime.utcnow().isoformat()
            }}
        )
        
        # Clean up temp file if PDF
        if "pdf" in file_type:
            import os
            try:
                os.unlink(tmp_path)
            except:
                pass
                
    except Exception as e:
        # Update report with error
        db = dependencies.get_database()
        await db.lab_reports.update_one(
            {"report_id": report_id},
            {"$set": {
                "analysis_status": "failed",
                "error": str(e)
            }}
        )

@router.get("/report/{report_id}")
async def get_report_analysis(report_id: str):
    """
    Get lab report analysis by ID.
    """
    db = dependencies.get_database()
    
    report = await db.lab_reports.find_one({"report_id": report_id}, {"_id": 0, "file_data": 0})
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report

@router.get("/user-reports/{user_id}")
async def get_user_reports(user_id: str):
    """
    Get all lab reports for a user.
    """
    db = dependencies.get_database()
    
    reports = await db.lab_reports.find(
        {"user_id": user_id}, 
        {"_id": 0, "file_data": 0}
    ).to_list(100)
    
    return {"reports": reports, "count": len(reports)}

@router.get("")
async def list_all_lab_reports(limit: int = 50):
    """
    Get all lab reports (admin view).
    """
    db = dependencies.get_db()
    
    reports = await db.lab_reports.find(
        {}, 
        {"_id": 0, "file_data": 0}
    ).to_list(limit)
    
    return {"reports": reports, "count": len(reports)}

@router.post("/upload")
async def upload_lab_report_simple(file: UploadFile = File(...), user_id: str = "demo-user"):
    """
    Alternative upload endpoint for lab reports.
    Alias for /upload-report for API compatibility.
    """
    return await upload_lab_report(file, user_id)

async def get_doctor_recommendations(specialties: List[str], severity: str) -> List[Dict]:
    """
    Get doctor recommendations based on detected conditions and severity.
    Uses mock database for now.
    """
    from .mock_doctors import get_doctors_by_specialty
    
    all_doctors = []
    for specialty in specialties:
        doctors = get_doctors_by_specialty(specialty, limit=3)
        all_doctors.extend(doctors)
    
    # Sort by rating and urgency
    all_doctors.sort(key=lambda x: (-x['rating'], -x['consultation_fee']))
    
    # Return top 5 unique doctors
    seen = set()
    unique_doctors = []
    for doctor in all_doctors:
        if doctor['id'] not in seen:
            seen.add(doctor['id'])
            unique_doctors.append(doctor)
            if len(unique_doctors) >= 5:
                break
    
    return unique_doctors

async def get_ayurveda_recommendations(conditions: List[str]) -> Dict:
    """
    Get Ayurveda doctor recommendations and holistic treatments.
    """
    from .mock_doctors import get_ayurveda_doctors
    
    ayurveda_doctors = get_ayurveda_doctors(limit=3)
    
    # Simple Ayurveda recommendations based on common conditions
    recommendations = {
        "doctors": ayurveda_doctors,
        "holistic_approach": [
            "Consult an Ayurvedic practitioner for personalized dosha analysis",
            "Consider Panchakarma therapy for detoxification",
            "Maintain balanced diet according to your body constitution",
            "Practice yoga and meditation for overall wellness"
        ],
        "herbal_remedies": [
            "Ashwagandha for stress and immunity",
            "Turmeric for inflammation",
            "Triphala for digestive health",
            "Brahmi for cognitive function"
        ],
        "lifestyle_tips": [
            "Follow daily routine (Dinacharya)",
            "Eat according to seasons (Ritucharya)",
            "Practice oil pulling (Gandusha)",
            "Get adequate sleep and rest"
        ]
    }
    
    return recommendations
