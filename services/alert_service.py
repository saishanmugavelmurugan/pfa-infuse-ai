"""
Multi-Channel Alert Service
Supports: In-App, Email, SMS, Webhook notifications
Currently mocked - ready for real integration
"""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

class AlertService:
    """
    Multi-channel alert dispatcher
    Channels: in_app, email, sms, webhook
    """
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.alert_configs: Dict[str, Dict] = {}  # user_id -> config
        self.delivery_queue: List[Dict] = []
        
    async def configure_alerts(
        self,
        user_id: str,
        segment: str,
        channels: List[str],
        severity_threshold: str = "medium",
        webhook_url: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Configure alert preferences for a user"""
        config = {
            "user_id": user_id,
            "segment": segment,
            "channels": channels,
            "severity_threshold": severity_threshold,
            "webhook_url": webhook_url,
            "email": email,
            "phone": phone,
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.alert_configs[user_id] = config
        
        return {
            "success": True,
            "message": "Alert configuration saved",
            "config": config
        }
    
    async def send_alert(
        self,
        user_id: str,
        threat_event: Dict[str, Any],
        connection_id: str
    ) -> Dict[str, Any]:
        """
        Send alert based on user's configured channels
        """
        config = self.alert_configs.get(user_id)
        if not config or not config.get("enabled"):
            return {"success": False, "reason": "Alerts not configured or disabled"}
        
        # Check severity threshold
        if not self._meets_threshold(
            threat_event.get("severity", "low"),
            config.get("severity_threshold", "medium")
        ):
            return {"success": False, "reason": "Below severity threshold"}
        
        # Create alert record
        alert_id = f"alert_{uuid4().hex[:12]}"
        alert = {
            "id": alert_id,
            "user_id": user_id,
            "connection_id": connection_id,
            "threat_event_id": threat_event.get("id"),
            "severity": threat_event.get("severity"),
            "title": self._generate_alert_title(threat_event),
            "message": self._generate_alert_message(threat_event),
            "channels_sent": [],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Send to all configured channels
        results = []
        for channel in config.get("channels", []):
            result = await self._send_to_channel(
                channel=channel,
                alert=alert,
                config=config
            )
            results.append(result)
            if result.get("success"):
                alert["channels_sent"].append(channel)
        
        alert["status"] = "sent" if alert["channels_sent"] else "failed"
        self.alerts.append(alert)
        
        return {
            "success": len(alert["channels_sent"]) > 0,
            "alert_id": alert_id,
            "channels_sent": alert["channels_sent"],
            "results": results
        }
    
    async def _send_to_channel(
        self,
        channel: str,
        alert: Dict,
        config: Dict
    ) -> Dict[str, Any]:
        """Send alert to specific channel"""
        if channel == "in_app":
            return await self._send_in_app(alert, config)
        elif channel == "email":
            return await self._send_email(alert, config)
        elif channel == "sms":
            return await self._send_sms(alert, config)
        elif channel == "webhook":
            return await self._send_webhook(alert, config)
        else:
            return {"success": False, "channel": channel, "error": "Unknown channel"}
    
    async def _send_in_app(self, alert: Dict, config: Dict) -> Dict[str, Any]:
        """Send in-app notification (stored for retrieval)"""
        # Store notification for user
        notification = {
            "id": f"notif_{uuid4().hex[:8]}",
            "user_id": alert["user_id"],
            "alert_id": alert["id"],
            "title": alert["title"],
            "message": alert["message"],
            "severity": alert["severity"],
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.delivery_queue.append(notification)
        
        return {
            "success": True,
            "channel": "in_app",
            "notification_id": notification["id"]
        }
    
    async def _send_email(self, alert: Dict, config: Dict) -> Dict[str, Any]:
        """Send email notification (MOCKED)"""
        email = config.get("email")
        if not email:
            return {"success": False, "channel": "email", "error": "No email configured"}
        
        # MOCK: In production, integrate with SendGrid/SES
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "success": True,
            "channel": "email",
            "recipient": email,
            "message": f"[MOCKED] Email sent to {email}",
            "mock": True
        }
    
    async def _send_sms(self, alert: Dict, config: Dict) -> Dict[str, Any]:
        """Send SMS notification (MOCKED)"""
        phone = config.get("phone")
        if not phone:
            return {"success": False, "channel": "sms", "error": "No phone configured"}
        
        # MOCK: In production, integrate with Twilio
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "success": True,
            "channel": "sms",
            "recipient": phone,
            "message": f"[MOCKED] SMS sent to {phone}",
            "mock": True
        }
    
    async def _send_webhook(self, alert: Dict, config: Dict) -> Dict[str, Any]:
        """Send webhook notification (MOCKED)"""
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return {"success": False, "channel": "webhook", "error": "No webhook URL configured"}
        
        # MOCK: In production, make actual HTTP POST
        payload = {
            "alert_id": alert["id"],
            "severity": alert["severity"],
            "title": alert["title"],
            "message": alert["message"],
            "timestamp": alert["created_at"]
        }
        
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            "success": True,
            "channel": "webhook",
            "url": webhook_url,
            "payload": payload,
            "message": f"[MOCKED] Webhook POST to {webhook_url}",
            "mock": True
        }
    
    def _meets_threshold(self, severity: str, threshold: str) -> bool:
        """Check if severity meets the configured threshold"""
        severity_levels = {
            "minimal": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        
        return severity_levels.get(severity, 0) >= severity_levels.get(threshold, 0)
    
    def _generate_alert_title(self, threat_event: Dict) -> str:
        """Generate alert title based on threat"""
        severity = threat_event.get("severity", "unknown").upper()
        action = threat_event.get("recommended_action", "detect").upper()
        return f"🚨 [{severity}] Security Alert - Action: {action}"
    
    def _generate_alert_message(self, threat_event: Dict) -> str:
        """Generate alert message based on threat"""
        threats = threat_event.get("threats_found", [])
        score = threat_event.get("threat_score", 0)
        summary = threat_event.get("ai_summary", "Threat detected")
        
        message = f"Threat Score: {score}/100\n"
        message += f"Summary: {summary}\n"
        
        if threats:
            message += f"Threats Detected: {len(threats)}\n"
            for t in threats[:3]:  # Show first 3 threats
                message += f"  - {t.get('type', 'Unknown')}: {t.get('description', '')}\n"
        
        return message
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Dict]:
        """Get notifications for a user"""
        notifications = [
            n for n in self.delivery_queue
            if n["user_id"] == user_id and (not unread_only or not n["read"])
        ]
        return notifications[:limit]
    
    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Mark a notification as read"""
        for notification in self.delivery_queue:
            if notification["id"] == notification_id and notification["user_id"] == user_id:
                notification["read"] = True
                return {"success": True}
        return {"success": False, "error": "Notification not found"}
    
    async def get_alert_config(self, user_id: str) -> Optional[Dict]:
        """Get user's alert configuration"""
        return self.alert_configs.get(user_id)
    
    async def get_alert_history(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get alert history for a user"""
        user_alerts = [a for a in self.alerts if a["user_id"] == user_id]
        return user_alerts[:limit]


# Singleton instance
alert_service = AlertService()
