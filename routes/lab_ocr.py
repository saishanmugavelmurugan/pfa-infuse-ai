"""
AI-Powered Lab Report OCR and Analysis
Extracts data from uploaded PDF/images using Vision AI
"""

import os
import base64
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from pydantic import BaseModel
import fitz  # PyMuPDF for PDF processing
from PIL import Image
import io

from utils.auth import get_current_user
from dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lab-ocr", tags=["Lab Report OCR"])


class ExtractedLabResult(BaseModel):
    test_name: str
    value: str
    unit: str
    normal_range: str
    status: str  # normal, high, low, critical


class OCRExtractionResult(BaseModel):
    success: bool
    test_type: str
    test_date: Optional[str]
    patient_name: Optional[str]
    lab_name: Optional[str]
    results: List[ExtractedLabResult]
    raw_text: Optional[str]
    confidence: float
    ai_summary: str
    recommendations: List[str]


async def extract_text_from_pdf(file_content: bytes) -> List[str]:
    """Extract text and images from PDF"""
    texts = []
    images = []
    
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        for page in doc:
            # Extract text
            text = page.get_text()
            if text.strip():
                texts.append(text)
            
            # Extract images from PDF
            for img_index, img in enumerate(page.get_images()):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    images.append(base64.b64encode(image_bytes).decode('utf-8'))
                except Exception as e:
                    logger.warning(f"Failed to extract image from PDF: {e}")
        
        doc.close()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
    
    return texts, images


async def extract_with_ai(image_base64: str = None, text_content: str = None) -> Dict[str, Any]:
    """Use AI to extract structured lab data from image or text"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_API_KEY"),
            model="gemini-2.0-flash"
        )
        
        prompt = """You are a medical lab report analyzer. Extract ALL test results from this lab report.

Return a JSON object with this EXACT structure:
{
    "test_type": "CBC/Lipid Panel/Liver Function/Kidney Function/Thyroid/Diabetes/Other",
    "test_date": "YYYY-MM-DD or null",
    "patient_name": "name or null",
    "lab_name": "lab name or null",
    "results": [
        {
            "test_name": "Hemoglobin",
            "value": "14.5",
            "unit": "g/dL",
            "normal_range": "12-17",
            "status": "normal/high/low/critical"
        }
    ],
    "confidence": 0.95,
    "summary": "Brief summary of findings",
    "recommendations": ["recommendation 1", "recommendation 2"],
    "concerns": ["any concerning values"]
}

Extract EVERY test value you can find. Be thorough. For status:
- "normal" if value is within range
- "high" if above range
- "low" if below range  
- "critical" if dangerously out of range

IMPORTANT: Return ONLY valid JSON, no markdown, no extra text."""

        if image_base64:
            # Vision-based extraction
            response = await chat.send_message_async(
                messages=[
                    UserMessage(
                        text=prompt,
                        images=[f"data:image/jpeg;base64,{image_base64}"]
                    )
                ]
            )
        elif text_content:
            # Text-based extraction
            response = await chat.send_message_async(
                messages=[
                    UserMessage(text=f"{prompt}\n\nLab Report Text:\n{text_content}")
                ]
            )
        else:
            return None
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Clean up response if it has markdown
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        return json.loads(response_text)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"AI extraction error: {e}")
        return None


@router.post("/upload-and-extract")
async def upload_and_extract_lab_report(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Upload a lab report (PDF/image) and extract data using AI OCR
    Returns structured lab results with AI analysis
    """
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    content_type = file.content_type
    
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {content_type}. Allowed: PDF, JPG, PNG"
        )
    
    # Read file content
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    extracted_data = None
    raw_text = ""
    image_base64 = None
    
    try:
        if content_type == "application/pdf":
            # Extract text and images from PDF
            texts, images = await extract_text_from_pdf(file_content)
            raw_text = "\n".join(texts)
            
            # Try text-based extraction first
            if raw_text.strip():
                extracted_data = await extract_with_ai(text_content=raw_text)
            
            # If text extraction failed and we have images, try image-based
            if not extracted_data and images:
                extracted_data = await extract_with_ai(image_base64=images[0])
                
        else:
            # Image file - use vision AI directly
            image_base64 = base64.b64encode(file_content).decode('utf-8')
            extracted_data = await extract_with_ai(image_base64=image_base64)
        
        if not extracted_data:
            raise HTTPException(
                status_code=422,
                detail="Could not extract data from the uploaded file. Please ensure it's a clear lab report."
            )
        
        # Generate unique ID
        import uuid
        report_id = str(uuid.uuid4())
        
        # Store in database
        lab_record = {
            "id": report_id,
            "user_id": current_user["user_id"],
            "file_name": file.filename,
            "file_type": content_type,
            "file_size": file_size,
            "test_type": extracted_data.get("test_type", "Unknown"),
            "test_date": extracted_data.get("test_date"),
            "patient_name": extracted_data.get("patient_name"),
            "lab_name": extracted_data.get("lab_name"),
            "results": extracted_data.get("results", []),
            "raw_text": raw_text[:5000] if raw_text else None,  # Limit stored text
            "ai_summary": extracted_data.get("summary", ""),
            "recommendations": extracted_data.get("recommendations", []),
            "concerns": extracted_data.get("concerns", []),
            "confidence": extracted_data.get("confidence", 0.8),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "analyzed": True
        }
        
        await db.user_lab_reports.insert_one(lab_record)
        
        # Remove MongoDB _id before returning
        lab_record.pop("_id", None)
        
        return {
            "success": True,
            "message": "Lab report processed successfully",
            "report_id": report_id,
            "extraction": {
                "test_type": extracted_data.get("test_type"),
                "test_date": extracted_data.get("test_date"),
                "patient_name": extracted_data.get("patient_name"),
                "lab_name": extracted_data.get("lab_name"),
                "results_count": len(extracted_data.get("results", [])),
                "results": extracted_data.get("results", []),
                "confidence": extracted_data.get("confidence", 0.8)
            },
            "analysis": {
                "summary": extracted_data.get("summary", ""),
                "recommendations": extracted_data.get("recommendations", []),
                "concerns": extracted_data.get("concerns", [])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lab report processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process lab report: {str(e)}"
        )


@router.get("/reports")
async def get_user_lab_reports(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all lab reports for current user"""
    cursor = db.user_lab_reports.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "raw_text": 0}  # Exclude large fields
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    reports = await cursor.to_list(length=limit)
    total = await db.user_lab_reports.count_documents({"user_id": current_user["user_id"]})
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "reports": reports
    }


@router.get("/reports/{report_id}")
async def get_lab_report_detail(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get detailed lab report by ID"""
    report = await db.user_lab_reports.find_one(
        {"id": report_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report


@router.post("/reports/{report_id}/reanalyze")
async def reanalyze_lab_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Re-run AI analysis on an existing report"""
    report = await db.user_lab_reports.find_one(
        {"id": report_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get full analysis using existing results
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_API_KEY"),
            model="gemini-2.0-flash"
        )
        
        results_text = json.dumps(report.get("results", []), indent=2)
        
        prompt = f"""Analyze these lab test results and provide:
1. A comprehensive summary of the patient's health based on these values
2. Specific recommendations (both allopathic and ayurvedic perspectives)
3. Any concerning values that need attention
4. Lifestyle modifications suggested

Lab Results:
{results_text}

Provide response as JSON:
{{
    "summary": "comprehensive analysis",
    "allopathic_recommendations": ["rec1", "rec2"],
    "ayurvedic_recommendations": ["rec1", "rec2"],
    "concerns": ["concern1"],
    "lifestyle_tips": ["tip1", "tip2"],
    "follow_up_tests": ["test1"],
    "urgency": "routine/soon/urgent"
}}"""

        response = await chat.send_message_async(
            messages=[UserMessage(text=prompt)]
        )
        
        response_text = response.text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        analysis = json.loads(response_text.strip())
        
        # Update database
        await db.user_lab_reports.update_one(
            {"id": report_id},
            {"$set": {
                "ai_analysis": analysis,
                "reanalyzed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "report_id": report_id,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"Reanalysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.delete("/reports/{report_id}")
async def delete_lab_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a lab report"""
    result = await db.user_lab_reports.delete_one({
        "id": report_id,
        "user_id": current_user["user_id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {"success": True, "message": "Report deleted"}


@router.get("/trends/{metric}")
async def get_metric_trend(
    metric: str,
    days: int = 90,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get trend data for a specific metric across all reports"""
    from datetime import timedelta
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    cursor = db.user_lab_reports.find(
        {
            "user_id": current_user["user_id"],
            "created_at": {"$gte": start_date}
        },
        {"_id": 0, "test_date": 1, "results": 1, "created_at": 1}
    ).sort("created_at", 1)
    
    reports = await cursor.to_list(length=100)
    
    # Extract metric values
    trend_data = []
    for report in reports:
        date = report.get("test_date") or report.get("created_at", "")[:10]
        for result in report.get("results", []):
            if metric.lower() in result.get("test_name", "").lower():
                try:
                    value = float(result.get("value", "0").replace(",", ""))
                    trend_data.append({
                        "date": date,
                        "value": value,
                        "unit": result.get("unit", ""),
                        "status": result.get("status", "")
                    })
                except ValueError:
                    continue
    
    return {
        "metric": metric,
        "period_days": days,
        "data_points": len(trend_data),
        "trend": trend_data
    }
