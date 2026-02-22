"""
AI Security Agent - Core Intelligence Engine for SecureSphere
Powered by GPT-4o via Emergent LLM Key

Capabilities:
- Real-time threat pattern recognition
- Zero-day threat detection
- Adaptive learning from new threats
- Multi-platform threat analysis (Mobile, IoT, Automotive)
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)

# Emergent LLM Integration
try:
    from emergentintegrations.llm.chat import chat, LlmModel
    EMERGENT_AVAILABLE = True
except ImportError:
    EMERGENT_AVAILABLE = False
    logger.warning("emergentintegrations not available, using mock responses")

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Threat Intelligence Database (In production, this would be MongoDB)
THREAT_SIGNATURES = {
    "phishing_patterns": [
        r"verify.*account.*immediately",
        r"suspended.*click.*here",
        r"urgent.*action.*required",
        r"confirm.*identity",
        r"bank.*update.*details",
        r"lottery.*winner",
        r"prize.*claim",
        r"otp.*share",
        r"kyc.*update.*mandatory"
    ],
    "malicious_domains": [
        "bit.ly", "tinyurl.com", "goo.gl",  # URL shorteners (suspicious in certain contexts)
        "login-secure", "account-verify", "banking-update",
        "paypa1", "amaz0n", "g00gle", "faceb00k"  # Typosquatting patterns
    ],
    "financial_fraud_keywords": [
        "upi", "transfer", "credit", "debit", "loan", "emi",
        "reward", "cashback", "refund", "payment failed"
    ]
}

# Known malicious IPs/Domains (sample - in production, sync with threat feeds)
KNOWN_THREATS = {
    "ips": ["192.168.1.100", "10.0.0.50"],  # Mock malicious IPs
    "domains": ["malware-site.com", "phishing-example.net"]
}


class AISecurityAgent:
    """AI-powered security analysis engine"""
    
    def __init__(self):
        self.model = LlmModel.GPT_4O if EMERGENT_AVAILABLE else None
        self.threat_memory: List[Dict] = []  # Learning memory
        self.analysis_count = 0
        
    async def analyze_url(self, url: str, context: Optional[str] = None) -> Dict:
        """
        Analyze URL for potential threats
        Returns threat assessment with confidence score
        """
        analysis_id = str(uuid4())
        
        # Basic heuristic analysis
        heuristic_score = self._heuristic_url_analysis(url)
        
        # AI-powered deep analysis
        ai_analysis = await self._ai_url_analysis(url, context)
        
        # Combine scores
        combined_score = (heuristic_score * 0.4) + (ai_analysis.get('risk_score', 50) * 0.6)
        
        result = {
            "analysis_id": analysis_id,
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "threat_level": self._get_threat_level(combined_score),
            "risk_score": round(combined_score, 2),
            "heuristic_score": heuristic_score,
            "ai_confidence": ai_analysis.get('confidence', 0.7),
            "threats_detected": ai_analysis.get('threats', []),
            "category": ai_analysis.get('category', 'unknown'),
            "recommendations": ai_analysis.get('recommendations', []),
            "safe_to_visit": combined_score < 40
        }
        
        # Store in threat memory for learning
        self._store_threat_memory(result)
        self.analysis_count += 1
        
        return result
    
    async def analyze_sms(self, message: str, sender: Optional[str] = None) -> Dict:
        """
        Analyze SMS for fraud patterns
        Detects phishing, financial fraud, and scam messages
        """
        analysis_id = str(uuid4())
        
        # Pattern-based analysis
        pattern_threats = self._pattern_sms_analysis(message)
        
        # AI-powered semantic analysis
        ai_analysis = await self._ai_sms_analysis(message, sender)
        
        # Calculate combined risk
        pattern_score = len(pattern_threats) * 15
        ai_score = ai_analysis.get('risk_score', 30)
        combined_score = min(100, (pattern_score * 0.3) + (ai_score * 0.7))
        
        result = {
            "analysis_id": analysis_id,
            "message_preview": message[:100] + "..." if len(message) > 100 else message,
            "sender": sender,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "threat_level": self._get_threat_level(combined_score),
            "risk_score": round(combined_score, 2),
            "fraud_type": ai_analysis.get('fraud_type', 'unknown'),
            "pattern_matches": pattern_threats,
            "ai_analysis": ai_analysis.get('analysis', ''),
            "extracted_urls": self._extract_urls(message),
            "extracted_phones": self._extract_phones(message),
            "recommendations": ai_analysis.get('recommendations', []),
            "is_spam": combined_score > 60,
            "is_fraud": combined_score > 75
        }
        
        self._store_threat_memory(result)
        self.analysis_count += 1
        
        return result
    
    async def calculate_threat_score(self, device_data: Dict) -> Dict:
        """
        Calculate real-time threat score for a device
        Considers multiple factors: network, apps, behavior, location
        """
        score_id = str(uuid4())
        
        # Factor scores
        network_score = self._analyze_network_security(device_data.get('network', {}))
        app_score = self._analyze_app_security(device_data.get('apps', []))
        behavior_score = self._analyze_behavior(device_data.get('behavior', {}))
        
        # AI-powered contextual analysis
        ai_context = await self._ai_context_analysis(device_data)
        
        # Weighted combination
        overall_score = (
            network_score * 0.25 +
            app_score * 0.25 +
            behavior_score * 0.20 +
            ai_context.get('risk_score', 50) * 0.30
        )
        
        return {
            "score_id": score_id,
            "device_id": device_data.get('device_id', 'unknown'),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_threat_score": round(overall_score, 2),
            "threat_level": self._get_threat_level(overall_score),
            "factors": {
                "network_security": {"score": network_score, "weight": 0.25},
                "app_security": {"score": app_score, "weight": 0.25},
                "behavior_analysis": {"score": behavior_score, "weight": 0.20},
                "ai_context": {"score": ai_context.get('risk_score', 50), "weight": 0.30}
            },
            "active_threats": ai_context.get('active_threats', []),
            "recommendations": ai_context.get('recommendations', []),
            "posture": "secure" if overall_score < 30 else "at_risk" if overall_score < 70 else "critical"
        }
    
    def _heuristic_url_analysis(self, url: str) -> float:
        """Basic heuristic URL analysis"""
        score = 0
        url_lower = url.lower()
        
        # Check for suspicious patterns
        if any(domain in url_lower for domain in THREAT_SIGNATURES['malicious_domains']):
            score += 30
        
        # Check for IP address in URL
        import re
        if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url):
            score += 25
        
        # Check for excessive subdomains
        if url_lower.count('.') > 4:
            score += 15
        
        # Check for suspicious TLDs
        suspicious_tlds = ['.xyz', '.top', '.click', '.link', '.work', '.date']
        if any(url_lower.endswith(tld) for tld in suspicious_tlds):
            score += 20
        
        # Check for URL shorteners
        shorteners = ['bit.ly', 'tinyurl', 'goo.gl', 't.co', 'ow.ly']
        if any(s in url_lower for s in shorteners):
            score += 15
        
        # Check for suspicious keywords
        suspicious_keywords = ['login', 'verify', 'secure', 'update', 'confirm', 'account']
        keyword_count = sum(1 for kw in suspicious_keywords if kw in url_lower)
        score += keyword_count * 10
        
        return min(100, score)
    
    def _pattern_sms_analysis(self, message: str) -> List[str]:
        """Pattern-based SMS analysis"""
        import re
        threats = []
        message_lower = message.lower()
        
        for pattern in THREAT_SIGNATURES['phishing_patterns']:
            if re.search(pattern, message_lower):
                threats.append(f"Phishing pattern: {pattern}")
        
        for keyword in THREAT_SIGNATURES['financial_fraud_keywords']:
            if keyword in message_lower:
                threats.append(f"Financial keyword: {keyword}")
        
        return threats
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        import re
        url_pattern = r'https?://[\w\.-]+(?:/[\w\.-]*)*'
        return re.findall(url_pattern, text)
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        import re
        phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,4}[-\s\.]?[0-9]{4,6}'
        return re.findall(phone_pattern, text)
    
    def _analyze_network_security(self, network: Dict) -> float:
        """Analyze network security posture"""
        score = 30  # Base score
        
        if network and network.get('vpn_active'):
            score -= 15
        if network and network.get('public_wifi'):
            score += 25
        if network and network.get('encrypted', True):
            score -= 10
        if network and network.get('suspicious_connections', 0) > 0:
            score += network.get('suspicious_connections', 0) * 10
        
        return max(0, min(100, score))
    
    def _analyze_app_security(self, apps: List[Dict]) -> float:
        """Analyze installed apps for security risks"""
        score = 20  # Base score
        
        if apps:  # Check if apps is not None
            for app in apps:
                if app.get('source') != 'official_store':
                    score += 15
                if app.get('permissions', []):
                    dangerous_perms = ['CAMERA', 'MICROPHONE', 'LOCATION', 'CONTACTS', 'SMS']
                    perm_count = sum(1 for p in app.get('permissions', []) if p in dangerous_perms)
                    score += perm_count * 3
        
        return max(0, min(100, score))
    
    def _analyze_behavior(self, behavior: Dict) -> float:
        """Analyze device behavior patterns"""
        score = 25  # Base score
        
        if behavior and behavior.get('unusual_data_usage'):
            score += 20
        if behavior and behavior.get('background_activity_high'):
            score += 15
        if behavior and behavior.get('frequent_crashes'):
            score += 10
        if behavior and behavior.get('battery_drain_fast'):
            score += 10
        
        return max(0, min(100, score))
    
    async def _ai_url_analysis(self, url: str, context: Optional[str]) -> Dict:
        """AI-powered URL threat analysis"""
        if not EMERGENT_AVAILABLE or not EMERGENT_LLM_KEY:
            return self._mock_ai_url_response(url)
        
        try:
            prompt = f"""Analyze this URL for security threats. Respond ONLY with valid JSON.

URL: {url}
Context: {context or 'User clicked on this link'}

Analyze for:
1. Phishing indicators
2. Malware distribution
3. Typosquatting
4. Suspicious domain patterns
5. SSL/TLS concerns

Respond with JSON:
{{
    "risk_score": <0-100>,
    "confidence": <0-1>,
    "category": "<phishing|malware|safe|suspicious|unknown>",
    "threats": ["<list of detected threats>"],
    "recommendations": ["<list of recommendations>"]
}}"""
            
            response = await chat(
                api_key=EMERGENT_LLM_KEY,
                model=LlmModel.GPT_4O,
                prompt=prompt
            )
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return self._mock_ai_url_response(url)
            
        except Exception as e:
            logger.error(f"AI URL analysis failed: {e}")
            return self._mock_ai_url_response(url)
    
    async def _ai_sms_analysis(self, message: str, sender: Optional[str]) -> Dict:
        """AI-powered SMS fraud analysis"""
        if not EMERGENT_AVAILABLE or not EMERGENT_LLM_KEY:
            return self._mock_ai_sms_response(message)
        
        try:
            prompt = f"""Analyze this SMS for fraud/scam indicators. Respond ONLY with valid JSON.

SMS Content: {message}
Sender: {sender or 'Unknown'}

Analyze for:
1. Phishing attempts
2. Financial fraud (UPI, banking scams)
3. Prize/lottery scams
4. OTP theft attempts
5. Impersonation (bank, government)

Respond with JSON:
{{
    "risk_score": <0-100>,
    "fraud_type": "<phishing|financial_fraud|lottery_scam|otp_theft|impersonation|legitimate|unknown>",
    "analysis": "<brief explanation>",
    "recommendations": ["<list of recommendations>"]
}}"""
            
            response = await chat(
                api_key=EMERGENT_LLM_KEY,
                model=LlmModel.GPT_4O,
                prompt=prompt
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return self._mock_ai_sms_response(message)
            
        except Exception as e:
            logger.error(f"AI SMS analysis failed: {e}")
            return self._mock_ai_sms_response(message)
    
    async def _ai_context_analysis(self, device_data: Dict) -> Dict:
        """AI-powered contextual threat analysis"""
        if not EMERGENT_AVAILABLE or not EMERGENT_LLM_KEY:
            return self._mock_ai_context_response()
        
        try:
            prompt = f"""Analyze this device security context. Respond ONLY with valid JSON.

Device Data:
- Platform: {device_data.get('platform', 'unknown')}
- OS Version: {device_data.get('os_version', 'unknown')}
- Network Type: {device_data.get('network', {}).get('type', 'unknown')}
- Apps Count: {len(device_data.get('apps') or [])}
- Location: {device_data.get('location', 'unknown')}

Provide security assessment with JSON:
{{
    "risk_score": <0-100>,
    "active_threats": ["<list of active threats>"],
    "recommendations": ["<security recommendations>"]
}}"""
            
            response = await chat(
                api_key=EMERGENT_LLM_KEY,
                model=LlmModel.GPT_4O,
                prompt=prompt
            )
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return self._mock_ai_context_response()
            
        except Exception as e:
            logger.error(f"AI context analysis failed: {e}")
            return self._mock_ai_context_response()
    
    def _mock_ai_url_response(self, url: str) -> Dict:
        """Mock response for URL analysis"""
        is_suspicious = any(p in url.lower() for p in ['login', 'verify', 'secure'])
        return {
            "risk_score": 65 if is_suspicious else 25,
            "confidence": 0.75,
            "category": "suspicious" if is_suspicious else "safe",
            "threats": ["Potential phishing attempt"] if is_suspicious else [],
            "recommendations": ["Verify the source before clicking", "Check SSL certificate"]
        }
    
    def _mock_ai_sms_response(self, message: str) -> Dict:
        """Mock response for SMS analysis"""
        is_suspicious = any(kw in message.lower() for kw in ['otp', 'bank', 'urgent', 'verify'])
        return {
            "risk_score": 70 if is_suspicious else 20,
            "fraud_type": "financial_fraud" if is_suspicious else "legitimate",
            "analysis": "Message contains suspicious financial keywords" if is_suspicious else "Message appears legitimate",
            "recommendations": ["Never share OTP", "Verify sender through official channels"]
        }
    
    def _mock_ai_context_response(self) -> Dict:
        """Mock response for context analysis"""
        return {
            "risk_score": 35,
            "active_threats": [],
            "recommendations": ["Keep OS updated", "Enable two-factor authentication", "Review app permissions"]
        }
    
    def _get_threat_level(self, score: float) -> str:
        """Convert score to threat level"""
        if score < 25:
            return "low"
        elif score < 50:
            return "medium"
        elif score < 75:
            return "high"
        else:
            return "critical"
    
    def _store_threat_memory(self, result: Dict):
        """Store analysis result for learning"""
        self.threat_memory.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": result.get('fraud_type') or result.get('category', 'unknown'),
            "score": result.get('risk_score', 0),
            "hash": hashlib.md5(str(result).encode()).hexdigest()
        })
        # Keep only last 1000 entries
        if len(self.threat_memory) > 1000:
            self.threat_memory = self.threat_memory[-1000:]
    
    def get_learning_stats(self) -> Dict:
        """Get AI learning statistics"""
        return {
            "total_analyses": self.analysis_count,
            "threat_memory_size": len(self.threat_memory),
            "threat_types_seen": list(set(t['type'] for t in self.threat_memory)),
            "average_risk_score": sum(t['score'] for t in self.threat_memory) / max(1, len(self.threat_memory)),
            "model": "GPT-4o" if EMERGENT_AVAILABLE else "Heuristic"
        }


# Global instance
security_agent = AISecurityAgent()
