"""
Alerts Service - Email, SMS, and WhatsApp notifications
Supports Resend for emails and Twilio for SMS/WhatsApp
"""
import os
import asyncio
import logging
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logger.warning("Resend not installed. Email alerts disabled.")

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. SMS/WhatsApp alerts disabled.")


class AlertConfig:
    """Configuration for alerts service"""
    
    @staticmethod
    def is_email_configured() -> bool:
        return bool(os.environ.get("RESEND_API_KEY"))
    
    @staticmethod
    def is_sms_configured() -> bool:
        return bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"))
    
    @staticmethod
    def is_whatsapp_configured() -> bool:
        return AlertConfig.is_sms_configured() and bool(os.environ.get("TWILIO_WHATSAPP_NUMBER"))


class EmailAlert(BaseModel):
    to: EmailStr
    subject: str
    html_content: str
    text_content: Optional[str] = None


class SMSAlert(BaseModel):
    to: str  # Phone number with country code
    message: str


class WhatsAppAlert(BaseModel):
    to: str  # Phone number with country code
    message: str


class AlertsService:
    """Unified alerts service for email, SMS, and WhatsApp"""
    
    def __init__(self):
        self._init_resend()
        self._init_twilio()
    
    def _init_resend(self):
        """Initialize Resend for emails"""
        self.resend_available = RESEND_AVAILABLE and AlertConfig.is_email_configured()
        if self.resend_available:
            resend.api_key = os.environ.get("RESEND_API_KEY")
            self.sender_email = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
            logger.info("✅ Resend email service initialized")
        else:
            logger.warning("⚠️ Email alerts not configured")
    
    def _init_twilio(self):
        """Initialize Twilio for SMS and WhatsApp"""
        self.twilio_available = TWILIO_AVAILABLE and AlertConfig.is_sms_configured()
        if self.twilio_available:
            self.twilio_client = TwilioClient(
                os.environ.get("TWILIO_ACCOUNT_SID"),
                os.environ.get("TWILIO_AUTH_TOKEN")
            )
            self.twilio_phone = os.environ.get("TWILIO_PHONE_NUMBER")
            self.twilio_whatsapp = os.environ.get("TWILIO_WHATSAPP_NUMBER")
            logger.info("✅ Twilio SMS/WhatsApp service initialized")
        else:
            self.twilio_client = None
            logger.warning("⚠️ SMS/WhatsApp alerts not configured")
    
    async def send_email(self, alert: EmailAlert) -> Dict:
        """Send an email alert"""
        if not self.resend_available:
            logger.warning(f"Email not sent (not configured): {alert.subject}")
            return {"status": "skipped", "reason": "Email service not configured"}
        
        try:
            params = {
                "from": self.sender_email,
                "to": [alert.to],
                "subject": alert.subject,
                "html": alert.html_content
            }
            
            if alert.text_content:
                params["text"] = alert.text_content
            
            # Run sync SDK in thread to keep non-blocking
            result = await asyncio.to_thread(resend.Emails.send, params)
            
            logger.info(f"✅ Email sent to {alert.to}: {alert.subject}")
            return {
                "status": "success",
                "email_id": result.get("id"),
                "to": alert.to
            }
        except Exception as e:
            logger.error(f"❌ Failed to send email: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def send_sms(self, alert: SMSAlert) -> Dict:
        """Send an SMS alert"""
        if not self.twilio_available or not self.twilio_phone:
            logger.warning(f"SMS not sent (not configured): {alert.to}")
            return {"status": "skipped", "reason": "SMS service not configured"}
        
        try:
            # Run in thread to keep non-blocking
            def send():
                return self.twilio_client.messages.create(
                    body=alert.message,
                    from_=self.twilio_phone,
                    to=alert.to
                )
            
            message = await asyncio.to_thread(send)
            
            logger.info(f"✅ SMS sent to {alert.to}")
            return {
                "status": "success",
                "message_sid": message.sid,
                "to": alert.to
            }
        except Exception as e:
            logger.error(f"❌ Failed to send SMS: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def send_whatsapp(self, alert: WhatsAppAlert) -> Dict:
        """Send a WhatsApp message"""
        if not self.twilio_available or not self.twilio_whatsapp:
            logger.warning(f"WhatsApp not sent (not configured): {alert.to}")
            return {"status": "skipped", "reason": "WhatsApp service not configured"}
        
        try:
            # Ensure proper WhatsApp format
            to_number = alert.to if alert.to.startswith("whatsapp:") else f"whatsapp:{alert.to}"
            from_number = self.twilio_whatsapp if self.twilio_whatsapp.startswith("whatsapp:") else f"whatsapp:{self.twilio_whatsapp}"
            
            def send():
                return self.twilio_client.messages.create(
                    body=alert.message,
                    from_=from_number,
                    to=to_number
                )
            
            message = await asyncio.to_thread(send)
            
            logger.info(f"✅ WhatsApp sent to {alert.to}")
            return {
                "status": "success",
                "message_sid": message.sid,
                "to": alert.to
            }
        except Exception as e:
            logger.error(f"❌ Failed to send WhatsApp: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def get_status(self) -> Dict:
        """Get status of all alert channels"""
        return {
            "email": {
                "available": self.resend_available,
                "configured": AlertConfig.is_email_configured()
            },
            "sms": {
                "available": self.twilio_available,
                "configured": AlertConfig.is_sms_configured()
            },
            "whatsapp": {
                "available": self.twilio_available and bool(self.twilio_whatsapp),
                "configured": AlertConfig.is_whatsapp_configured()
            }
        }


# Email Templates
class EmailTemplates:
    """Pre-built email templates"""
    
    @staticmethod
    def password_reset(reset_link: str, user_name: str = "User") -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f97316, #ea580c); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #f97316; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Infuse-AI</h1>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>Hi {user_name},</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <p>This link will expire in 1 hour for security reasons.</p>
                    <p>If you didn't request this, you can safely ignore this email.</p>
                    <p>Best regards,<br>The Infuse-AI Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Infuse-AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def security_alert(alert_type: str, details: str, user_name: str = "User") -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #dc2626, #b91c1c); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #fef2f2; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #fecaca; }}
                .alert-box {{ background: white; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Security Alert</h1>
                </div>
                <div class="content">
                    <h2>{alert_type}</h2>
                    <p>Hi {user_name},</p>
                    <div class="alert-box">
                        <p><strong>Alert Details:</strong></p>
                        <p>{details}</p>
                    </div>
                    <p>If this was you, no action is needed. If not, please secure your account immediately.</p>
                    <p>Best regards,<br>The SecureSphere Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 SecureSphere by Infuse-AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def welcome_email(user_name: str, product: str = "Infuse-AI") -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f97316, #ea580c); padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: white; margin: 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .feature {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #e5e7eb; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to {product}! 🎉</h1>
                </div>
                <div class="content">
                    <h2>Hi {user_name},</h2>
                    <p>Thank you for joining {product}! We're excited to have you on board.</p>
                    <p>Here's what you can do:</p>
                    <div class="feature">✅ Access your personalized dashboard</div>
                    <div class="feature">✅ Explore all features</div>
                    <div class="feature">✅ Get real-time alerts and notifications</div>
                    <p>If you have any questions, our support team is here to help.</p>
                    <p>Best regards,<br>The {product} Team</p>
                </div>
                <div class="footer">
                    <p>© 2025 Infuse-AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """


# Singleton instance
alerts_service = AlertsService()
