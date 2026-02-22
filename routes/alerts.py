"""
Alerts API - Send email, SMS, and WhatsApp notifications
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from services.alerts_service import alerts_service, EmailAlert, SMSAlert, WhatsAppAlert, EmailTemplates

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    html_content: str
    text_content: Optional[str] = None


class SendSMSRequest(BaseModel):
    to: str  # Phone with country code e.g., +1234567890
    message: str


class SendWhatsAppRequest(BaseModel):
    to: str  # Phone with country code
    message: str


class TestAlertRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


@router.get("/status")
async def get_alerts_status():
    """Get status of all alert channels"""
    return alerts_service.get_status()


@router.post("/email")
async def send_email(request: SendEmailRequest):
    """Send an email"""
    alert = EmailAlert(
        to=request.to,
        subject=request.subject,
        html_content=request.html_content,
        text_content=request.text_content
    )
    result = await alerts_service.send_email(alert)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/sms")
async def send_sms(request: SendSMSRequest):
    """Send an SMS"""
    alert = SMSAlert(to=request.to, message=request.message)
    result = await alerts_service.send_sms(alert)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/whatsapp")
async def send_whatsapp(request: SendWhatsAppRequest):
    """Send a WhatsApp message"""
    alert = WhatsAppAlert(to=request.to, message=request.message)
    result = await alerts_service.send_whatsapp(alert)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/test")
async def test_alerts(request: TestAlertRequest):
    """Test alert channels"""
    results = {}
    
    if request.email:
        email_alert = EmailAlert(
            to=request.email,
            subject="Test Alert from Infuse-AI",
            html_content=EmailTemplates.welcome_email("Test User", "Infuse-AI")
        )
        results["email"] = await alerts_service.send_email(email_alert)
    
    if request.phone:
        sms_alert = SMSAlert(
            to=request.phone,
            message="🔔 Test alert from Infuse-AI. Your notification system is working!"
        )
        results["sms"] = await alerts_service.send_sms(sms_alert)
        
        whatsapp_alert = WhatsAppAlert(
            to=request.phone,
            message="🔔 Test alert from Infuse-AI. Your WhatsApp notifications are working!"
        )
        results["whatsapp"] = await alerts_service.send_whatsapp(whatsapp_alert)
    
    return {
        "status": "completed",
        "results": results
    }
