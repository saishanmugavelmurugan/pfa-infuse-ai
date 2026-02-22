"""
AI-Powered Threat Detection Engine
Continuous learning system for Detect → Protect → Enforce
"""
import asyncio
import random
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

class ThreatIntelligenceEngine:
    """
    AI-powered threat detection with continuous learning
    Integrates internal DB + external feeds + ML patterns
    """
    
    # Known threat patterns (continuously updated by AI)
    THREAT_PATTERNS = {
        "sim_swap": {
            "pattern": r"SIM.*swap|IMSI.*change|unauthorized.*activation",
            "severity": "critical",
            "action": "enforce",
            "description": "SIM swap fraud attempt detected"
        },
        "smishing": {
            "pattern": r"(bit\.ly|tinyurl|goo\.gl).*(bank|otp|verify|urgent)",
            "severity": "high",
            "action": "protect",
            "description": "SMS phishing attempt"
        },
        "ss7_attack": {
            "pattern": r"location.*track|intercept.*sms|ss7.*exploit",
            "severity": "critical",
            "action": "enforce",
            "description": "SS7 protocol exploitation attempt"
        },
        "malicious_apn": {
            "pattern": r"(proxy|tunnel|vpn)\.malware\.|suspicious\.apn",
            "severity": "high",
            "action": "protect",
            "description": "Malicious APN configuration"
        },
        "imei_spoofing": {
            "pattern": r"imei.*spoof|device.*clone|fake.*imei",
            "severity": "high",
            "action": "enforce",
            "description": "IMEI spoofing detected"
        },
        "ddos_pattern": {
            "pattern": r"flood|ddos|syn.*attack|amplification",
            "severity": "critical",
            "action": "enforce",
            "description": "DDoS attack pattern"
        },
        "data_exfiltration": {
            "pattern": r"exfil|large.*upload|unusual.*traffic|data.*leak",
            "severity": "high",
            "action": "protect",
            "description": "Potential data exfiltration"
        },
        "vehicle_hack": {
            "pattern": r"can.*bus.*inject|obd.*exploit|telematics.*breach",
            "severity": "critical",
            "action": "enforce",
            "description": "Vehicle system compromise attempt"
        },
        # White Goods / IoT Threats
        "botnet_infection": {
            "pattern": r"mirai|botnet|zombie|c2.*server|command.*control",
            "severity": "critical",
            "action": "enforce",
            "description": "IoT botnet infection detected"
        },
        "iot_firmware_tamper": {
            "pattern": r"firmware.*tamper|rootkit|backdoor.*firmware|unauthorized.*update",
            "severity": "high",
            "action": "enforce",
            "description": "IoT firmware tampering attempt"
        },
        "smart_home_breach": {
            "pattern": r"smart.*home.*breach|iot.*exploit|appliance.*hack",
            "severity": "high",
            "action": "protect",
            "description": "Smart home device breach attempt"
        },
        # CCTV Threats
        "camera_hijack": {
            "pattern": r"stream.*hijack|camera.*takeover|rtsp.*exploit|onvif.*vuln",
            "severity": "critical",
            "action": "enforce",
            "description": "Camera stream hijacking attempt"
        },
        "unauthorized_access_cctv": {
            "pattern": r"unauthorized.*view|privacy.*breach|illegal.*access.*camera",
            "severity": "high",
            "action": "enforce",
            "description": "Unauthorized CCTV access attempt"
        },
        "cctv_credential_attack": {
            "pattern": r"default.*password|brute.*force.*camera|credential.*stuff",
            "severity": "high",
            "action": "protect",
            "description": "CCTV credential attack detected"
        },
        "dvr_nvr_exploit": {
            "pattern": r"dvr.*exploit|nvr.*vulnerability|recorder.*hack",
            "severity": "critical",
            "action": "enforce",
            "description": "DVR/NVR system exploitation attempt"
        }
    }
    
    # External threat feeds (simulated)
    EXTERNAL_FEEDS = [
        "abuse_ipdb",
        "virustotal",
        "threatfox",
        "phishtank",
        "gsma_fraud_db"
    ]
    
    def __init__(self):
        self.learning_buffer: List[Dict] = []
        self.learned_patterns: List[Dict] = []
        self.false_positives: List[str] = []
        self.threat_cache: Dict[str, Dict] = {}
        
    async def analyze_identifier(
        self,
        identifier: str,
        segment: str,
        connection_type: str,
        additional_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for threat analysis
        Returns: threat assessment with recommended action
        """
        start_time = datetime.now(timezone.utc)
        
        # Parallel analysis from multiple sources
        results = await asyncio.gather(
            self._check_internal_db(identifier, segment),
            self._check_external_feeds(identifier),
            self._ai_pattern_analysis(identifier, segment, additional_data),
            self._behavioral_analysis(identifier, segment)
        )
        
        internal_result, external_result, ai_result, behavioral_result = results
        
        # Aggregate threat scores
        threat_score = self._calculate_aggregate_score(
            internal_result, external_result, ai_result, behavioral_result
        )
        
        # Determine severity and action
        severity, action = self._determine_action(threat_score, segment)
        
        # Collect all threats found
        threats_found = []
        for result in [internal_result, external_result, ai_result, behavioral_result]:
            if result.get("threats"):
                threats_found.extend(result["threats"])
        
        # Generate AI summary
        ai_summary = await self._generate_ai_summary(
            identifier, segment, threat_score, threats_found
        )
        
        # Calculate analysis time
        analysis_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Store for learning
        await self._store_for_learning(identifier, segment, threat_score, threats_found)
        
        return {
            "identifier": identifier,
            "segment": segment,
            "threat_detected": threat_score > 30,
            "threat_score": round(threat_score, 2),
            "severity": severity,
            "recommended_action": action,
            "threats_found": threats_found,
            "ai_summary": ai_summary,
            "analysis_time_ms": analysis_time,
            "sources_checked": ["internal_db", "external_feeds", "ai_patterns", "behavioral"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _check_internal_db(
        self, 
        identifier: str, 
        segment: str
    ) -> Dict[str, Any]:
        """Check against internal threat database"""
        # Simulate DB lookup
        await asyncio.sleep(0.02)
        
        threats = []
        score = 0
        
        # Check against known patterns
        for pattern_name, pattern_data in self.THREAT_PATTERNS.items():
            if re.search(pattern_data["pattern"], identifier.lower()):
                threats.append({
                    "type": pattern_name,
                    "source": "internal_db",
                    "severity": pattern_data["severity"],
                    "description": pattern_data["description"]
                })
                score += self._severity_to_score(pattern_data["severity"])
        
        # Check cache for known bad actors
        if identifier in self.threat_cache:
            cached = self.threat_cache[identifier]
            threats.append({
                "type": "cached_threat",
                "source": "threat_cache",
                "severity": cached.get("severity", "medium"),
                "description": "Previously identified threat"
            })
            score += 40
        
        return {"score": min(score, 100), "threats": threats}
    
    async def _check_external_feeds(self, identifier: str) -> Dict[str, Any]:
        """Check against external threat intelligence feeds"""
        # Simulate external API calls
        await asyncio.sleep(0.05)
        
        threats = []
        score = 0
        
        # Simulate random threat detection from feeds
        for feed in self.EXTERNAL_FEEDS:
            # 5% chance of finding a threat per feed
            if random.random() < 0.05:
                severity = random.choice(["low", "medium", "high"])
                threats.append({
                    "type": f"external_{feed}",
                    "source": feed,
                    "severity": severity,
                    "description": f"Flagged by {feed}"
                })
                score += self._severity_to_score(severity)
        
        return {"score": min(score, 100), "threats": threats}
    
    async def _ai_pattern_analysis(
        self,
        identifier: str,
        segment: str,
        additional_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """AI/ML based pattern analysis"""
        await asyncio.sleep(0.03)
        
        threats = []
        score = 0
        
        # Segment-specific analysis
        if segment == "telco":
            score, threats = await self._analyze_telco_patterns(identifier, additional_data)
        elif segment == "mobile":
            score, threats = await self._analyze_mobile_patterns(identifier, additional_data)
        elif segment == "enterprise":
            score, threats = await self._analyze_enterprise_patterns(identifier, additional_data)
        elif segment == "automotive":
            score, threats = await self._analyze_automotive_patterns(identifier, additional_data)
        elif segment == "white_goods":
            score, threats = await self._analyze_white_goods_patterns(identifier, additional_data)
        elif segment == "cctv":
            score, threats = await self._analyze_cctv_patterns(identifier, additional_data)
        
        return {"score": score, "threats": threats}
    
    async def _analyze_telco_patterns(
        self, 
        identifier: str, 
        data: Optional[Dict]
    ) -> Tuple[float, List]:
        """Telco-specific threat patterns"""
        threats = []
        score = 0
        
        # Check for suspicious IMSI patterns
        if data and data.get("imsi"):
            imsi = data["imsi"]
            # Check for test/invalid IMSI
            if imsi.startswith("001") or imsi.startswith("999"):
                threats.append({
                    "type": "invalid_imsi",
                    "source": "ai_analysis",
                    "severity": "high",
                    "description": "Test or invalid IMSI detected"
                })
                score += 60
        
        # Check for rapid SIM changes
        if data and data.get("sim_change_count", 0) > 3:
            threats.append({
                "type": "rapid_sim_change",
                "source": "ai_analysis",
                "severity": "critical",
                "description": "Multiple SIM changes detected - possible fraud"
            })
            score += 80
        
        return score, threats
    
    async def _analyze_mobile_patterns(
        self, 
        identifier: str, 
        data: Optional[Dict]
    ) -> Tuple[float, List]:
        """Mobile user threat patterns"""
        threats = []
        score = 0
        
        # Check for rooted/jailbroken device indicators
        if data and data.get("device_status") == "rooted":
            threats.append({
                "type": "rooted_device",
                "source": "ai_analysis",
                "severity": "medium",
                "description": "Rooted/jailbroken device detected"
            })
            score += 30
        
        # Check for suspicious app patterns
        if data and data.get("suspicious_apps", 0) > 0:
            threats.append({
                "type": "malicious_apps",
                "source": "ai_analysis",
                "severity": "high",
                "description": f"{data['suspicious_apps']} potentially malicious apps detected"
            })
            score += 50
        
        return score, threats
    
    async def _analyze_enterprise_patterns(
        self, 
        identifier: str, 
        data: Optional[Dict]
    ) -> Tuple[float, List]:
        """Enterprise security patterns"""
        threats = []
        score = 0
        
        # Check for suspicious IP patterns
        if data and data.get("ip_address"):
            ip = data["ip_address"]
            # Check for known bad IP ranges (simplified)
            if ip.startswith("10.0.0.") or ip.startswith("192.168."):
                pass  # Internal IP, okay
            elif random.random() < 0.1:  # 10% chance of suspicious external IP
                threats.append({
                    "type": "suspicious_ip",
                    "source": "ai_analysis",
                    "severity": "medium",
                    "description": "IP associated with suspicious activity"
                })
                score += 40
        
        # Check for unusual access patterns
        if data and data.get("access_hour"):
            hour = data["access_hour"]
            if hour < 6 or hour > 22:  # Unusual hours
                threats.append({
                    "type": "unusual_access_time",
                    "source": "ai_analysis",
                    "severity": "low",
                    "description": "Access during unusual hours"
                })
                score += 15
        
        return score, threats
    
    async def _analyze_automotive_patterns(
        self, 
        identifier: str, 
        data: Optional[Dict]
    ) -> Tuple[float, List]:
        """Automotive/fleet security patterns"""
        threats = []
        score = 0
        
        # Check for VIN manipulation
        if data and data.get("vin"):
            vin = data["vin"]
            if len(vin) != 17:
                threats.append({
                    "type": "invalid_vin",
                    "source": "ai_analysis",
                    "severity": "high",
                    "description": "Invalid or manipulated VIN"
                })
                score += 70
        
        # Check for unusual telematics
        if data and data.get("speed", 0) > 200:
            threats.append({
                "type": "impossible_speed",
                "source": "ai_analysis",
                "severity": "medium",
                "description": "Impossible speed reading - possible spoofing"
            })
            score += 40
        
        return score, threats
    
    async def _analyze_white_goods_patterns(
        self, 
        identifier: str, 
        data: Optional[Dict]
    ) -> Tuple[float, List]:
        """White Goods / IoT Appliance security patterns"""
        threats = []
        score = 0
        
        # Check for default credentials indicator
        if data and data.get("password_changed") == False:
            threats.append({
                "type": "default_credentials",
                "source": "ai_analysis",
                "severity": "high",
                "description": "Device using default credentials - vulnerable to attack"
            })
            score += 60
        
        # Check for outdated firmware
        if data and data.get("firmware_outdated"):
            threats.append({
                "type": "outdated_firmware",
                "source": "ai_analysis",
                "severity": "medium",
                "description": "Outdated firmware with known vulnerabilities"
            })
            score += 40
        
        # Check for suspicious network traffic patterns
        if data and data.get("outbound_connections", 0) > 100:
            threats.append({
                "type": "suspicious_traffic",
                "source": "ai_analysis",
                "severity": "high",
                "description": "Unusually high outbound connections - possible botnet activity"
            })
            score += 70
        
        # Check for unknown manufacturer
        if data and data.get("manufacturer") == "unknown":
            threats.append({
                "type": "unknown_device",
                "source": "ai_analysis",
                "severity": "low",
                "description": "Unknown manufacturer - verify device authenticity"
            })
            score += 20
        
        # Check for insecure protocols
        if data and data.get("uses_http"):
            threats.append({
                "type": "insecure_protocol",
                "source": "ai_analysis",
                "severity": "medium",
                "description": "Device using unencrypted HTTP communication"
            })
            score += 30
        
        return score, threats
    
    async def _analyze_cctv_patterns(
        self, 
        identifier: str, 
        data: Optional[Dict]
    ) -> Tuple[float, List]:
        """CCTV / Surveillance Camera security patterns"""
        threats = []
        score = 0
        
        camera_type = data.get("camera_type", "private") if data else "private"
        
        # Check for exposed stream
        if data and data.get("stream_public"):
            severity = "critical" if camera_type == "private" else "high"
            threats.append({
                "type": "exposed_stream",
                "source": "ai_analysis",
                "severity": severity,
                "description": f"Camera stream publicly accessible - {camera_type} camera"
            })
            score += 80 if camera_type == "private" else 50
        
        # Check for default RTSP credentials
        if data and data.get("rtsp_default_creds"):
            threats.append({
                "type": "rtsp_default_credentials",
                "source": "ai_analysis",
                "severity": "critical",
                "description": "RTSP stream using default credentials"
            })
            score += 75
        
        # Check for firmware vulnerabilities
        if data and data.get("firmware_vulnerable"):
            threats.append({
                "type": "vulnerable_firmware",
                "source": "ai_analysis",
                "severity": "high",
                "description": "Camera firmware has known vulnerabilities"
            })
            score += 60
        
        # Check for unauthorized access attempts
        if data and data.get("failed_login_attempts", 0) > 10:
            threats.append({
                "type": "brute_force_attempt",
                "source": "ai_analysis",
                "severity": "high",
                "description": f"Multiple failed login attempts ({data['failed_login_attempts']}) - possible brute force attack"
            })
            score += 55
        
        # Check for privacy compliance (public cameras)
        if camera_type == "public" and data and not data.get("privacy_compliant"):
            threats.append({
                "type": "privacy_non_compliant",
                "source": "ai_analysis",
                "severity": "medium",
                "description": "Public camera not compliant with privacy regulations"
            })
            score += 35
        
        # Check for insecure cloud storage
        if data and data.get("cloud_storage_insecure"):
            threats.append({
                "type": "insecure_cloud_storage",
                "source": "ai_analysis",
                "severity": "high",
                "description": "Camera recordings stored on insecure cloud service"
            })
            score += 50
        
        # Check for P2P vulnerabilities (common in cheap cameras)
        if data and data.get("p2p_enabled") and data.get("p2p_vulnerable"):
            threats.append({
                "type": "p2p_vulnerability",
                "source": "ai_analysis",
                "severity": "critical",
                "description": "P2P feature has known vulnerability - remote access possible"
            })
            score += 80
        
        return score, threats
    
    async def _behavioral_analysis(
        self, 
        identifier: str, 
        segment: str
    ) -> Dict[str, Any]:
        """Behavioral anomaly detection"""
        await asyncio.sleep(0.02)
        
        # Simulate behavioral analysis
        anomaly_score = random.uniform(0, 30)  # Usually low
        
        threats = []
        if anomaly_score > 25:
            threats.append({
                "type": "behavioral_anomaly",
                "source": "behavioral_analysis",
                "severity": "medium",
                "description": "Unusual behavior pattern detected"
            })
        
        return {"score": anomaly_score, "threats": threats}
    
    def _calculate_aggregate_score(
        self,
        internal: Dict,
        external: Dict,
        ai: Dict,
        behavioral: Dict
    ) -> float:
        """Calculate weighted aggregate threat score"""
        weights = {
            "internal": 0.35,
            "external": 0.25,
            "ai": 0.30,
            "behavioral": 0.10
        }
        
        total = (
            internal["score"] * weights["internal"] +
            external["score"] * weights["external"] +
            ai["score"] * weights["ai"] +
            behavioral["score"] * weights["behavioral"]
        )
        
        return min(total, 100)
    
    def _determine_action(
        self, 
        threat_score: float, 
        segment: str
    ) -> Tuple[str, str]:
        """Determine severity and recommended action"""
        if threat_score >= 80:
            return "critical", "enforce"
        elif threat_score >= 60:
            return "high", "enforce"
        elif threat_score >= 40:
            return "medium", "protect"
        elif threat_score >= 20:
            return "low", "detect"
        else:
            return "minimal", "detect"
    
    def _severity_to_score(self, severity: str) -> float:
        """Convert severity string to numeric score"""
        mapping = {
            "critical": 40,
            "high": 30,
            "medium": 20,
            "low": 10
        }
        return mapping.get(severity, 10)
    
    async def _generate_ai_summary(
        self,
        identifier: str,
        segment: str,
        threat_score: float,
        threats: List[Dict]
    ) -> str:
        """Generate human-readable AI summary"""
        if not threats:
            return f"No significant threats detected for {segment} identifier. System monitoring active."
        
        threat_types = [t["type"] for t in threats]
        severity_counts = {}
        for t in threats:
            sev = t.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        summary = f"Threat Analysis for {segment.upper()}: "
        summary += f"Score {threat_score:.1f}/100. "
        summary += f"Found {len(threats)} potential threat(s). "
        
        if "critical" in severity_counts:
            summary += f"⚠️ {severity_counts['critical']} CRITICAL issue(s) requiring immediate action. "
        if "high" in severity_counts:
            summary += f"🔴 {severity_counts['high']} HIGH severity threat(s). "
        
        summary += f"Types: {', '.join(set(threat_types))}."
        
        return summary
    
    async def _store_for_learning(
        self,
        identifier: str,
        segment: str,
        score: float,
        threats: List[Dict]
    ):
        """Store analysis results for continuous learning"""
        learning_event = {
            "id": str(uuid4()),
            "identifier_hash": hash(identifier),
            "segment": segment,
            "threat_score": score,
            "threat_count": len(threats),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.learning_buffer.append(learning_event)
        
        # Trigger learning if buffer is full
        if len(self.learning_buffer) >= 100:
            await self._run_learning_cycle()
    
    async def _run_learning_cycle(self):
        """Run AI learning cycle to update patterns"""
        if not self.learning_buffer:
            return
        
        # Analyze patterns in buffer
        high_threat_events = [e for e in self.learning_buffer if e["threat_score"] > 60]
        
        # Update patterns based on learning
        if len(high_threat_events) > 10:
            # Would integrate with ML model here
            pass
        
        # Clear buffer
        self.learning_buffer = []
    
    async def report_false_positive(
        self, 
        identifier: str, 
        threat_type: str
    ):
        """Report false positive to improve AI accuracy"""
        self.false_positives.append({
            "identifier_hash": hash(identifier),
            "threat_type": threat_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Adjust confidence for the pattern
        if threat_type in self.THREAT_PATTERNS:
            # Would reduce confidence score in production
            pass
    
    async def get_learning_stats(self) -> Dict[str, Any]:
        """Get AI learning statistics"""
        return {
            "patterns_learned": len(self.learned_patterns),
            "false_positives_reported": len(self.false_positives),
            "learning_buffer_size": len(self.learning_buffer),
            "active_patterns": len(self.THREAT_PATTERNS),
            "external_feeds_active": len(self.EXTERNAL_FEEDS)
        }


# Singleton instance
threat_engine = ThreatIntelligenceEngine()
