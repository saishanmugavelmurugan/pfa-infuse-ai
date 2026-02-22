"""
AI Support Agent - Intelligent Customer Support for SecureSphere & HealthTrack Pro
Provides 24/7 automated support with context-aware responses

Capabilities:
- Multi-language support (English only for SecureSphere, all languages for HealthTrack Pro)
- Context-aware responses
- Escalation to human support
- FAQ automation
- Guided troubleshooting
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Emergent LLM Integration
try:
    from emergentintegrations.llm.chat import chat, LlmModel
    EMERGENT_AVAILABLE = True
except ImportError:
    EMERGENT_AVAILABLE = False

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')


# Knowledge Base for both products
KNOWLEDGE_BASE = {
    "securesphere": {
        "product_name": "SecureSphere",
        "description": "Telco-grade cybersecurity platform for mobile, IoT, and automotive security",
        "features": [
            "URL Scanner - Detect phishing and malicious links",
            "SMS Analyzer - Identify fraudulent messages",
            "Real-time Threat Scoring - Continuous security monitoring",
            "Device Registry - Secure device management",
            "Telecom Integration - CSP-level security",
            "Automotive Security - Connected vehicle protection"
        ],
        "tiers": {
            "consumer": "Personal mobile protection for Android and iOS",
            "enterprise": "Fleet management and MDM integration",
            "telecom": "Network-level security for telecom operators",
            "automotive": "Connected vehicle security for OEMs"
        },
        "faqs": [
            {
                "q": "How does URL scanning work?",
                "a": "Our AI-powered URL scanner analyzes links using multiple detection methods including heuristic analysis, AI pattern recognition, and real-time threat intelligence. When you scan a URL, we check it against known malicious patterns, suspicious domain characteristics, and emerging threats."
            },
            {
                "q": "Is my data secure?",
                "a": "Yes! SecureSphere uses enterprise-grade encryption for all data. We don't store the content of your messages or URLs - only anonymized threat patterns to improve our detection capabilities."
            },
            {
                "q": "What SMS fraud types can you detect?",
                "a": "We detect 7 types of SMS fraud: phishing attacks, financial fraud (banking/UPI scams), lottery/prize scams, OTP theft attempts, impersonation (fake bank/government messages), job scams, and romance scams."
            },
            {
                "q": "How does the AI learning work?",
                "a": "Our AI continuously learns from new threats using federated learning. When a new threat pattern is detected across multiple users, it's added to our threat intelligence database to protect everyone. Your privacy is maintained through anonymization."
            }
        ]
    },
    "healthtrack": {
        "product_name": "HealthTrack Pro",
        "description": "Comprehensive healthcare management platform with AI-powered health insights",
        "features": [
            "Patient Records Management",
            "Appointment Scheduling",
            "E-Prescriptions",
            "Lab Test Ordering & Results",
            "AI Health Analytics",
            "ABDM Integration (India)",
            "Wearable Device Sync",
            "Telemedicine Support"
        ],
        "faqs": [
            {
                "q": "How do I book an appointment?",
                "a": "Go to the Appointments tab in your dashboard, click 'Book Appointment', select your preferred doctor, choose an available time slot, and confirm. You'll receive a confirmation via email and SMS."
            },
            {
                "q": "What is ABHA ID?",
                "a": "ABHA (Ayushman Bharat Health Account) is a unique health ID under India's ABDM initiative. It helps in maintaining your health records digitally and accessing healthcare services seamlessly across providers."
            },
            {
                "q": "How do I connect my wearable device?",
                "a": "Go to the 'Devices' tab, click 'Add Device', select your device brand (Fitbit, Apple Watch, etc.), and follow the authorization steps. Your health data will sync automatically."
            },
            {
                "q": "Are my health records secure?",
                "a": "Yes! We use industry-standard encryption and comply with healthcare data regulations. Your data is stored securely and only accessible by you and authorized healthcare providers with your consent."
            }
        ]
    }
}

# Guided Troubleshooting Flows
TROUBLESHOOTING_FLOWS = {
    "url_not_scanning": {
        "title": "URL Scanner Not Working",
        "steps": [
            "Ensure you've entered a complete URL including http:// or https://",
            "Check your internet connection",
            "Try refreshing the page and scanning again",
            "If the URL is very long, try scanning the main domain first",
            "Clear your browser cache and try again"
        ]
    },
    "sms_analysis_slow": {
        "title": "SMS Analysis Taking Too Long",
        "steps": [
            "Long messages may take more time to analyze",
            "Check your internet connection",
            "For bulk analysis, process messages in smaller batches",
            "If using special characters, ensure they're properly encoded"
        ]
    },
    "appointment_booking_failed": {
        "title": "Unable to Book Appointment",
        "steps": [
            "Ensure you're logged in to your account",
            "Check if the selected time slot is still available",
            "Verify your profile information is complete",
            "Try selecting a different time slot",
            "Clear browser cache and try again"
        ]
    },
    "device_sync_failed": {
        "title": "Wearable Device Not Syncing",
        "steps": [
            "Ensure your device is connected to Bluetooth",
            "Check if the device app is updated to the latest version",
            "Re-authorize the connection from the Devices tab",
            "Ensure your device has an active internet connection",
            "Try disconnecting and reconnecting the device"
        ]
    }
}


class AISupportAgent:
    """
    Intelligent support agent for SecureSphere and HealthTrack Pro
    """
    
    def __init__(self):
        self.model = LlmModel.GPT_4O if EMERGENT_AVAILABLE else None
        self.conversation_history: Dict[str, List[Dict]] = {}  # session_id -> messages
        self.support_stats = {
            "total_queries": 0,
            "resolved_automatically": 0,
            "escalated_to_human": 0,
            "average_response_time_ms": 0
        }
    
    async def get_response(self, 
                          session_id: str,
                          message: str, 
                          product: str = "securesphere",
                          language: str = "en",
                          user_context: Optional[Dict] = None) -> Dict:
        """
        Get AI-powered support response
        
        Args:
            session_id: Unique session identifier for conversation continuity
            message: User's support message
            product: "securesphere" or "healthtrack"
            language: Language code (only "en" for SecureSphere)
            user_context: Optional context about the user
        """
        import time
        start_time = time.time()
        
        response_id = str(uuid4())
        
        # Initialize conversation history for new sessions
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        # Add user message to history
        self.conversation_history[session_id].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Check for FAQ match first
        faq_response = self._check_faq_match(message, product)
        if faq_response:
            response = {
                "response_id": response_id,
                "message": faq_response,
                "source": "faq",
                "confidence": 0.95,
                "suggestions": self._get_related_topics(product),
                "needs_escalation": False
            }
        else:
            # Check for troubleshooting flow
            troubleshoot = self._check_troubleshooting_match(message)
            if troubleshoot:
                response = {
                    "response_id": response_id,
                    "message": f"**{troubleshoot['title']}**\n\nPlease try these steps:\n" + 
                              "\n".join([f"{i+1}. {step}" for i, step in enumerate(troubleshoot['steps'])]),
                    "source": "troubleshooting",
                    "confidence": 0.9,
                    "suggestions": ["Still having issues?", "Contact human support"],
                    "needs_escalation": False
                }
            else:
                # Use AI for complex queries
                ai_response = await self._get_ai_response(message, product, language, user_context)
                response = {
                    "response_id": response_id,
                    "message": ai_response.get("message", "I'm here to help! Could you provide more details about your issue?"),
                    "source": "ai",
                    "confidence": ai_response.get("confidence", 0.8),
                    "suggestions": ai_response.get("suggestions", []),
                    "needs_escalation": ai_response.get("needs_escalation", False)
                }
        
        # Add response to history
        self.conversation_history[session_id].append({
            "role": "assistant",
            "content": response["message"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Update stats
        elapsed_ms = int((time.time() - start_time) * 1000)
        self.support_stats["total_queries"] += 1
        if not response.get("needs_escalation"):
            self.support_stats["resolved_automatically"] += 1
        else:
            self.support_stats["escalated_to_human"] += 1
        
        # Update average response time
        total = self.support_stats["total_queries"]
        old_avg = self.support_stats["average_response_time_ms"]
        self.support_stats["average_response_time_ms"] = int((old_avg * (total - 1) + elapsed_ms) / total)
        
        response["response_time_ms"] = elapsed_ms
        response["session_id"] = session_id
        response["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return response
    
    def _check_faq_match(self, message: str, product: str) -> Optional[str]:
        """Check if message matches any FAQ"""
        message_lower = message.lower()
        faqs = KNOWLEDGE_BASE.get(product, {}).get("faqs", [])
        
        for faq in faqs:
            # Simple keyword matching - in production, use semantic similarity
            question_words = set(faq["q"].lower().split())
            message_words = set(message_lower.split())
            
            # Calculate overlap
            overlap = len(question_words.intersection(message_words))
            if overlap >= 3 or any(keyword in message_lower for keyword in faq["q"].lower().split()[:3]):
                return faq["a"]
        
        return None
    
    def _check_troubleshooting_match(self, message: str) -> Optional[Dict]:
        """Check if message needs troubleshooting flow"""
        message_lower = message.lower()
        
        troubleshoot_keywords = {
            "url_not_scanning": ["url not working", "scan not working", "cannot scan", "url scanner issue"],
            "sms_analysis_slow": ["sms slow", "analysis slow", "taking long", "sms stuck"],
            "appointment_booking_failed": ["cannot book", "appointment failed", "booking error", "slot not available"],
            "device_sync_failed": ["device not syncing", "sync failed", "wearable not connecting", "fitbit not working"]
        }
        
        for flow_id, keywords in troubleshoot_keywords.items():
            if any(kw in message_lower for kw in keywords):
                return TROUBLESHOOTING_FLOWS.get(flow_id)
        
        return None
    
    async def _get_ai_response(self, message: str, product: str, language: str, user_context: Optional[Dict]) -> Dict:
        """Get AI-powered response for complex queries"""
        if not EMERGENT_AVAILABLE or not EMERGENT_LLM_KEY:
            return self._mock_ai_response(message, product)
        
        try:
            kb = KNOWLEDGE_BASE.get(product, {})
            language_instruction = "English only" if product == "securesphere" else "Respond in the user's language"
            context_str = json.dumps(user_context) if user_context else "None provided"
            
            system_prompt = f"""You are a helpful support agent for {kb.get('product_name', product)}.
Product Description: {kb.get('description', '')}

Features: {', '.join(kb.get('features', []))}

Guidelines:
1. Be helpful, friendly, and professional
2. If you don't know something, say so and offer to escalate to human support
3. Keep responses concise but informative
4. Suggest related topics or next steps when appropriate
5. Language: {language_instruction}

User Context: {context_str}"""
            
            response = await chat(
                api_key=EMERGENT_LLM_KEY,
                model=LlmModel.GPT_4O,
                prompt=f"{system_prompt}\n\nUser Query: {message}\n\nProvide a helpful response:"
            )
            
            # Check if escalation is needed
            needs_escalation = any(phrase in message.lower() for phrase in [
                "speak to human", "talk to agent", "escalate", "supervisor", "complaint", "refund"
            ])
            
            return {
                "message": response,
                "confidence": 0.85,
                "suggestions": self._get_related_topics(product),
                "needs_escalation": needs_escalation
            }
            
        except Exception as e:
            logger.error(f"AI support response error: {e}")
            return self._mock_ai_response(message, product)
    
    def _mock_ai_response(self, message: str, product: str) -> Dict:
        """Fallback mock response"""
        return {
            "message": f"Thank you for reaching out about {KNOWLEDGE_BASE.get(product, {}).get('product_name', product)}! I understand you have a question. Our team is here to help. Could you provide more details about your specific issue so I can assist you better?",
            "confidence": 0.7,
            "suggestions": self._get_related_topics(product),
            "needs_escalation": False
        }
    
    def _get_related_topics(self, product: str) -> List[str]:
        """Get related help topics"""
        if product == "securesphere":
            return [
                "How to scan a URL?",
                "What fraud types can you detect?",
                "How does AI learning work?",
                "Contact human support"
            ]
        else:
            return [
                "How to book an appointment?",
                "How to view lab results?",
                "How to connect wearable devices?",
                "Contact human support"
            ]
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session"""
        return self.conversation_history.get(session_id, [])
    
    def get_support_stats(self) -> Dict:
        """Get support statistics"""
        return {
            **self.support_stats,
            "auto_resolution_rate": round(
                (self.support_stats["resolved_automatically"] / max(1, self.support_stats["total_queries"])) * 100, 2
            )
        }
    
    async def escalate_to_human(self, session_id: str, reason: str) -> Dict:
        """Escalate conversation to human support"""
        ticket_id = str(uuid4())
        
        return {
            "ticket_id": ticket_id,
            "status": "escalated",
            "message": "Your conversation has been escalated to our human support team. A support agent will contact you shortly.",
            "estimated_response_time": "Within 2 hours",
            "conversation_history": self.get_conversation_history(session_id)
        }


# Global instance
ai_support_agent = AISupportAgent()
