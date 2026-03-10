"""
Security Alerts Service - Email notifications for suspicious login activity
Sends alerts when a user logs in from a new location or device
"""
import os
import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid not installed. Security email alerts disabled.")


class SecurityAlertConfig:
    """Configuration for security alerts"""
    
    @staticmethod
    def is_configured() -> bool:
        api_key = os.environ.get("SENDGRID_API_KEY", "")
        # Check if API key is real (not mock)
        return bool(api_key) and api_key != "MOCK_SENDGRID_KEY"
    
    @staticmethod
    def get_sender_email() -> str:
        return os.environ.get("SENDER_EMAIL", "security@healthtrackpro.com")
    
    @staticmethod
    def get_support_email() -> str:
        return os.environ.get("SUPPORT_EMAIL", "support@healthtrackpro.com")


class SecurityEmailService:
    """Service for sending security-related email notifications"""
    
    def __init__(self):
        self.configured = SENDGRID_AVAILABLE and SecurityAlertConfig.is_configured()
        if self.configured:
            self.client = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
            self.sender = SecurityAlertConfig.get_sender_email()
            logger.info("✅ Security email alerts service initialized")
        else:
            self.client = None
            self.sender = None
            logger.info("ℹ️ Security email alerts running in mock mode (SendGrid not configured)")
    
    def _generate_new_login_email(
        self,
        user_name: str,
        device: str,
        location: str,
        ip_address: str,
        timestamp: str
    ) -> tuple:
        """Generate HTML and text content for new login alert"""
        
        # Format timestamp for display
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime("%B %d, %Y at %I:%M %p UTC")
        except:
            formatted_time = timestamp
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background-color: #f8f9fa;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        <!-- Header -->
        <tr>
            <td style="background: linear-gradient(135deg, #f97316 0%, #f59e0b 100%); padding: 30px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">🔐 HealthTrack Pro</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">Security Alert</p>
            </td>
        </tr>
        
        <!-- Content -->
        <tr>
            <td style="padding: 40px 30px;">
                <h2 style="color: #1f2937; margin: 0 0 20px 0; font-size: 20px;">New Sign-in Detected</h2>
                
                <p style="color: #4b5563; line-height: 1.6; margin: 0 0 20px 0;">
                    Hi {user_name},
                </p>
                
                <p style="color: #4b5563; line-height: 1.6; margin: 0 0 20px 0;">
                    We noticed a new sign-in to your HealthTrack Pro account from a new location or device. 
                    If this was you, no action is needed.
                </p>
                
                <!-- Login Details Box -->
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fef3c7; border-radius: 8px; margin: 20px 0;">
                    <tr>
                        <td style="padding: 20px;">
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                                        <span style="color: #92400e; font-weight: 600;">Device:</span>
                                        <span style="color: #78350f; float: right;">{device}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                                        <span style="color: #92400e; font-weight: 600;">Location:</span>
                                        <span style="color: #78350f; float: right;">{location}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                                        <span style="color: #92400e; font-weight: 600;">IP Address:</span>
                                        <span style="color: #78350f; float: right;">{ip_address}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 8px 0;">
                                        <span style="color: #92400e; font-weight: 600;">Time:</span>
                                        <span style="color: #78350f; float: right;">{formatted_time}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                
                <!-- Warning Box -->
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fee2e2; border-radius: 8px; margin: 20px 0;">
                    <tr>
                        <td style="padding: 20px;">
                            <p style="color: #991b1b; margin: 0; font-weight: 600;">
                                ⚠️ Wasn't you?
                            </p>
                            <p style="color: #7f1d1d; margin: 10px 0 0 0; line-height: 1.5;">
                                If you didn't sign in, your account may be compromised. 
                                Please change your password immediately and enable MFA (Multi-Factor Authentication) for additional security.
                            </p>
                        </td>
                    </tr>
                </table>
                
                <!-- Action Button -->
                <table width="100%" cellpadding="0" cellspacing="0" style="margin: 30px 0;">
                    <tr>
                        <td style="text-align: center;">
                            <a href="https://healthtrackpro.com/security-dashboard" 
                               style="background: linear-gradient(135deg, #f97316 0%, #f59e0b 100%); 
                                      color: #ffffff; 
                                      text-decoration: none; 
                                      padding: 14px 28px; 
                                      border-radius: 8px; 
                                      font-weight: 600;
                                      display: inline-block;">
                                Review Security Settings
                            </a>
                        </td>
                    </tr>
                </table>
                
                <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 30px 0 0 0;">
                    For your security, we recommend:
                </p>
                <ul style="color: #6b7280; font-size: 14px; line-height: 1.8; margin: 10px 0 0 0; padding-left: 20px;">
                    <li>Enable MFA if not already active</li>
                    <li>Review your active sessions regularly</li>
                    <li>Use a strong, unique password</li>
                </ul>
            </td>
        </tr>
        
        <!-- Footer -->
        <tr>
            <td style="background-color: #f3f4f6; padding: 20px 30px; text-align: center;">
                <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                    This is an automated security notification from HealthTrack Pro.
                </p>
                <p style="color: #9ca3af; font-size: 12px; margin: 10px 0 0 0;">
                    © 2026 Infuse-AI. All rights reserved.
                </p>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        text_content = f"""
HealthTrack Pro - Security Alert

New Sign-in Detected

Hi {user_name},

We noticed a new sign-in to your HealthTrack Pro account from a new location or device.

Login Details:
- Device: {device}
- Location: {location}
- IP Address: {ip_address}
- Time: {formatted_time}

If this was you, no action is needed.

Wasn't you?
If you didn't sign in, your account may be compromised. Please change your password immediately and enable MFA for additional security.

Review your security settings: https://healthtrackpro.com/security-dashboard

---
This is an automated security notification from HealthTrack Pro.
© 2026 Infuse-AI. All rights reserved.
"""
        
        return html_content, text_content
    
    async def send_new_login_alert(
        self,
        user_email: str,
        user_name: str,
        device: str,
        location: str,
        ip_address: str,
        timestamp: str
    ) -> Dict:
        """Send an email alert for a new login from unknown location/device"""
        
        html_content, text_content = self._generate_new_login_email(
            user_name=user_name,
            device=device,
            location=location,
            ip_address=ip_address,
            timestamp=timestamp
        )
        
        if not self.configured:
            # Log the alert in mock mode
            logger.info(f"📧 [MOCK] Security alert would be sent to {user_email}: New login from {location} ({device})")
            return {
                "status": "mock",
                "reason": "Email service not configured (using mock)",
                "to": user_email,
                "subject": "New Sign-in to Your HealthTrack Pro Account"
            }
        
        try:
            message = Mail(
                from_email=Email(self.sender, "HealthTrack Pro Security"),
                to_emails=To(user_email),
                subject="🔐 New Sign-in to Your HealthTrack Pro Account",
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", text_content)
            )
            
            # Send asynchronously
            response = await asyncio.to_thread(self.client.send, message)
            
            logger.info(f"✅ Security alert sent to {user_email}: New login from {location}")
            return {
                "status": "success",
                "to": user_email,
                "status_code": response.status_code
            }
        except Exception as e:
            logger.error(f"❌ Failed to send security alert to {user_email}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "to": user_email
            }


# Singleton instance
_security_email_service = None

def get_security_email_service() -> SecurityEmailService:
    """Get the singleton security email service instance"""
    global _security_email_service
    if _security_email_service is None:
        _security_email_service = SecurityEmailService()
    return _security_email_service


async def check_and_alert_new_login(
    db,
    user_id: str,
    user_email: str,
    user_name: str,
    device: str,
    location: str,
    ip_address: str,
    timestamp: str
) -> Dict:
    """
    Check if this is a new location/device and send alert if so.
    Returns the result of the check and any email sent.
    """
    logger.info(f"🔍 Checking login for new location/device: {user_email} from {location} ({device})")
    
    # Get known locations/devices for this user
    known_logins = await db.known_login_locations.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    # Create fingerprint for this login (location + device type)
    # We use a simplified fingerprint to avoid false positives
    location_key = location.lower().strip() if location else "unknown"
    device_key = device.lower().strip() if device else "unknown"
    
    # Check if this combination is known
    is_new_location = True
    is_new_device = True
    
    for known in known_logins:
        if known.get("location", "").lower().strip() == location_key:
            is_new_location = False
        if known.get("device", "").lower().strip() == device_key:
            is_new_device = False
    
    # If neither is new, no alert needed
    if not is_new_location and not is_new_device:
        logger.info(f"✓ Known location and device for {user_email} - no alert needed")
        return {"alert_sent": False, "reason": "Known location and device"}
    
    logger.info(f"⚠️ New login detected for {user_email}: new_location={is_new_location}, new_device={is_new_device}")
    
    # Store this as a known location/device for future reference
    await db.known_login_locations.insert_one({
        "user_id": user_id,
        "location": location,
        "device": device,
        "ip_prefix": ip_address.rsplit('.', 1)[0] if '.' in ip_address else ip_address,
        "first_seen": timestamp,
        "last_seen": timestamp
    })
    
    # Send alert
    service = get_security_email_service()
    result = await service.send_new_login_alert(
        user_email=user_email,
        user_name=user_name,
        device=device,
        location=location,
        ip_address=ip_address,
        timestamp=timestamp
    )
    
    return {
        "alert_sent": True,
        "is_new_location": is_new_location,
        "is_new_device": is_new_device,
        "email_result": result
    }
