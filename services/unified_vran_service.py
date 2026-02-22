"""
Unified vRAN Service - Telco-Grade Integration
Integrates all existing telecom components with the new vRAN system

Components Integrated:
- vran_connector.py (Mobile/APN connections)
- threat_engine.py (AI threat analysis)
- telecom_adapter.py (CSP integration)
- gsm_fraud.py (SIM swap, OTP interception, Caller ID spoofing)
- ai_security_agent.py (AI-powered analysis)
- ai_learning_agent.py (Continuous learning)
- enforcement_engine.py (Automated enforcement)
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

# Import all existing components
from services.vran_connector import vran_connector
from services.threat_engine import threat_engine
from services.alert_service import alert_service
from services.enforcement_engine import enforcement_engine
from services.securesphere.ai_security_agent import security_agent
from services.securesphere.ai_learning_agent import ai_learning_agent

logger = logging.getLogger(__name__)


class SelfProtectionPolicy:
    """
    Mandatory Self-Protection Policy for vRAN
    This policy is ALWAYS active and cannot be disabled
    """
    
    # Self-protection is MANDATORY - cannot be disabled
    ENFORCEMENT_MODE = "mandatory"  # Options: mandatory (only option)
    
    PROTECTION_RULES = {
        "ddos_mitigation": {
            "enabled": True,
            "threshold_requests_per_second": 1000,
            "action": "rate_limit",
            "cannot_disable": True
        },
        "intrusion_detection": {
            "enabled": True,
            "sensitivity": "high",
            "action": "block_and_alert",
            "cannot_disable": True
        },
        "auto_healing": {
            "enabled": True,
            "restart_on_crash": True,
            "failover_enabled": True,
            "cannot_disable": True
        },
        "rate_limiting": {
            "enabled": True,
            "per_user_limit": 100,
            "per_ip_limit": 500,
            "cannot_disable": True
        },
        "threat_auto_block": {
            "enabled": True,
            "min_threat_score": 80,
            "auto_enforce": True,
            "cannot_disable": True
        }
    }
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get self-protection status - always active"""
        return {
            "enforcement_mode": cls.ENFORCEMENT_MODE,
            "status": "active",
            "can_disable": False,
            "rules": cls.PROTECTION_RULES,
            "message": "Self-protection is mandatory and cannot be disabled"
        }
    
    @classmethod
    def validate_enforcement(cls, action: str, threat_score: float) -> bool:
        """Check if enforcement should be applied"""
        if threat_score >= cls.PROTECTION_RULES["threat_auto_block"]["min_threat_score"]:
            return True
        return False


class UnifiedVRANService:
    """
    Unified vRAN Service that integrates all telco-grade components
    Provides a single interface for all vRAN operations
    """
    
    def __init__(self):
        self.vran_connector = vran_connector
        self.threat_engine = threat_engine
        self.alert_service = alert_service
        self.enforcement_engine = enforcement_engine
        self.security_agent = security_agent
        self.learning_agent = ai_learning_agent
        self.self_protection = SelfProtectionPolicy()
        
        # Unified session store
        self.sessions: Dict[str, Dict] = {}
        
        # Segment configurations
        self.segment_configs = {
            "telco": {
                "identifiers": ["msisdn", "imsi", "apn"],
                "actions": ["detect", "protect", "enforce"],
                "features": ["gsm_fraud", "sim_swap", "otp_protection", "caller_id"]
            },
            "mobile": {
                "identifiers": ["phone_number", "imei", "device_id"],
                "actions": ["detect", "protect", "enforce"],
                "features": ["sms_analysis", "url_scanning", "app_security"]
            },
            "enterprise": {
                "identifiers": ["ip_address", "domain", "apn"],
                "actions": ["detect", "protect", "enforce"],
                "features": ["network_security", "endpoint_protection", "sso"]
            },
            "automotive": {
                "identifiers": ["vin", "esim_iccid", "apn"],
                "actions": ["detect", "protect", "enforce"],
                "features": ["can_bus_security", "telematics", "ota_protection"]
            },
            "white_goods": {
                "identifiers": ["device_id", "mac_address", "imei", "apn"],
                "actions": ["detect", "protect", "enforce"],
                "features": ["botnet_detection", "firmware_protection", "iot_security"]
            },
            "cctv": {
                "identifiers": ["camera_id", "ip_address", "mac_address", "rtsp_url"],
                "actions": ["detect", "protect", "enforce"],
                "features": ["stream_protection", "privacy_compliance", "access_control"]
            }
        }
    
    async def connect_and_analyze(
        self,
        identifier: str,
        segment: str,
        connection_type: str = "mobile_number",
        user_id: str = "default",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Unified connection and analysis flow
        1. Establish vRAN connection
        2. Run threat analysis (integrated)
        3. Apply self-protection if needed
        4. Trigger learning
        5. Return comprehensive result
        """
        session_id = str(uuid4())
        start_time = datetime.now(timezone.utc)
        
        try:
            # Step 1: Establish connection
            if connection_type == "apn":
                conn_result = await self.vran_connector.connect_apn(
                    apn=identifier, user_id=user_id, segment=segment, metadata=metadata
                )
            else:
                conn_result = await self.vran_connector.connect_mobile_number(
                    mobile_number=identifier, user_id=user_id, segment=segment, metadata=metadata
                )
            
            if not conn_result.get("success"):
                return {"success": False, "error": conn_result.get("error", "Connection failed")}
            
            # Step 2: Run integrated threat analysis
            analysis_result = await self._run_integrated_analysis(
                identifier=identifier,
                segment=segment,
                connection_type=connection_type,
                additional_data=metadata
            )
            
            # Step 3: Apply self-protection enforcement if needed
            enforcement_result = None
            if self.self_protection.validate_enforcement(
                action=analysis_result.get("recommended_action", "detect"),
                threat_score=analysis_result.get("threat_score", 0)
            ):
                enforcement_result = await self._apply_enforcement(
                    identifier=identifier,
                    segment=segment,
                    threat_data=analysis_result
                )
            
            # Step 4: Trigger learning
            await self.learning_agent.learn_from_vran_session(
                session_id=session_id,
                segment=segment,
                threat_data=analysis_result
            )
            
            # Step 5: Send alerts if threats detected
            if analysis_result.get("threat_detected"):
                await self.alert_service.send_alert(
                    user_id=user_id,
                    threat_event=analysis_result,
                    connection_id=identifier
                )
            
            # Store session
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "segment": segment,
                "identifier": identifier,
                "connection": conn_result,
                "analysis": analysis_result,
                "enforcement": enforcement_result,
                "self_protection_active": True,
                "created_at": start_time.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            self.sessions[session_id] = session_data
            
            return {
                "success": True,
                "session_id": session_id,
                "connection": conn_result,
                "analysis": analysis_result,
                "enforcement": enforcement_result,
                "self_protection": self.self_protection.get_status(),
                "processing_time_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Error in unified connect_and_analyze: {e}")
            return {"success": False, "error": str(e)}
    
    async def _run_integrated_analysis(
        self,
        identifier: str,
        segment: str,
        connection_type: str,
        additional_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Run integrated threat analysis using all available engines
        """
        # Run analyses in parallel
        analysis_tasks = [
            # Primary vRAN threat engine
            self.threat_engine.analyze_identifier(
                identifier=identifier,
                segment=segment,
                connection_type=connection_type,
                additional_data=additional_data
            ),
        ]
        
        # Add segment-specific analysis
        if segment == "telco":
            # Add GSM fraud checks (integrated from gsm_fraud.py)
            analysis_tasks.append(self._analyze_gsm_threats(identifier, additional_data))
        elif segment == "mobile":
            # Add mobile-specific SMS/URL analysis
            analysis_tasks.append(self._analyze_mobile_threats(identifier, additional_data))
        
        # Execute all analyses
        all_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
        
        # Merge results
        primary_result = all_results[0] if not isinstance(all_results[0], Exception) else {}
        
        # Combine additional analysis results
        combined_threats = primary_result.get("threats_found", [])
        combined_score = primary_result.get("threat_score", 0)
        
        for i, result in enumerate(all_results[1:], 1):
            if not isinstance(result, Exception) and result:
                if result.get("threats"):
                    combined_threats.extend(result["threats"])
                if result.get("additional_score"):
                    combined_score = min(100, combined_score + result["additional_score"])
        
        # Final severity determination
        severity, action = self._determine_final_action(combined_score)
        
        return {
            **primary_result,
            "threats_found": combined_threats,
            "threat_score": combined_score,
            "severity": severity,
            "recommended_action": action,
            "integrated_analysis": True,
            "engines_used": ["vran_threat_engine", "gsm_fraud" if segment == "telco" else "mobile_security"]
        }
    
    async def _analyze_gsm_threats(self, identifier: str, data: Optional[Dict]) -> Dict[str, Any]:
        """
        GSM-specific threat analysis (integrated from gsm_fraud.py)
        """
        threats = []
        additional_score = 0
        
        # Check for SIM swap indicators
        if data and data.get("sim_change_recent"):
            threats.append({
                "type": "sim_swap_indicator",
                "source": "gsm_fraud_detector",
                "severity": "critical",
                "description": "Recent SIM change detected - potential SIM swap attack"
            })
            additional_score += 40
        
        # Check for OTP interception patterns
        if data and data.get("failed_otp_attempts", 0) > 3:
            threats.append({
                "type": "otp_interception_risk",
                "source": "gsm_fraud_detector",
                "severity": "high",
                "description": f"Multiple failed OTP attempts ({data['failed_otp_attempts']}) - possible interception"
            })
            additional_score += 30
        
        # Check for caller ID spoofing
        if data and data.get("ani_mismatch"):
            threats.append({
                "type": "caller_id_spoof",
                "source": "gsm_fraud_detector",
                "severity": "high",
                "description": "ANI mismatch detected - possible caller ID spoofing"
            })
            additional_score += 35
        
        return {
            "threats": threats,
            "additional_score": additional_score
        }
    
    async def _analyze_mobile_threats(self, identifier: str, data: Optional[Dict]) -> Dict[str, Any]:
        """
        Mobile-specific threat analysis (integrated from ai_security_agent.py)
        """
        threats = []
        additional_score = 0
        
        # Check for suspicious URLs in device data
        if data and data.get("recent_urls"):
            for url in data.get("recent_urls", [])[:5]:
                url_analysis = await self.security_agent.analyze_url(url)
                if url_analysis.get("risk_score", 0) > 60:
                    threats.append({
                        "type": "malicious_url_detected",
                        "source": "ai_security_agent",
                        "severity": "high",
                        "description": f"Malicious URL detected: {url[:30]}..."
                    })
                    additional_score += 20
        
        # Check for suspicious SMS
        if data and data.get("recent_sms"):
            for sms in data.get("recent_sms", [])[:5]:
                sms_analysis = await self.security_agent.analyze_sms(
                    message=sms.get("content", ""),
                    sender=sms.get("sender")
                )
                if sms_analysis.get("is_fraud"):
                    threats.append({
                        "type": "fraud_sms_detected",
                        "source": "ai_security_agent",
                        "severity": "high",
                        "description": f"Fraud SMS detected from {sms.get('sender', 'unknown')}"
                    })
                    additional_score += 25
        
        return {
            "threats": threats,
            "additional_score": additional_score
        }
    
    async def _apply_enforcement(
        self,
        identifier: str,
        segment: str,
        threat_data: Dict
    ) -> Dict[str, Any]:
        """
        Apply enforcement action based on threat data
        Self-protection ensures this is ALWAYS executed for high threats
        """
        action = threat_data.get("recommended_action", "detect")
        threat_score = threat_data.get("threat_score", 0)
        
        if action == "enforce" or threat_score >= 80:
            # Execute enforcement
            enforcement_result = await self.enforcement_engine.execute_enforcement(
                action_type="block_ip" if segment == "enterprise" else "rate_limit",
                target=identifier,
                parameters={
                    "reason": "Auto-enforced by vRAN self-protection",
                    "threat_score": threat_score,
                    "threats": threat_data.get("threats_found", [])
                },
                auto_rollback=True,
                rollback_after_minutes=60
            )
            
            return {
                "enforced": True,
                "action_taken": enforcement_result.get("action"),
                "result": enforcement_result,
                "self_protection_triggered": True
            }
        
        return {
            "enforced": False,
            "reason": "Threat score below enforcement threshold"
        }
    
    def _determine_final_action(self, threat_score: float) -> tuple:
        """Determine severity and action based on combined score"""
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
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics from all integrated components
        """
        return {
            "vran_connector": {
                "active_sessions": len(self.vran_connector.active_sessions),
                "pool_size": self.vran_connector.connection_pool_size
            },
            "threat_engine": {
                "patterns_active": len(self.threat_engine.THREAT_PATTERNS),
                "external_feeds": len(self.threat_engine.EXTERNAL_FEEDS),
                "learning_buffer": len(self.threat_engine.learning_buffer)
            },
            "ai_security": self.security_agent.get_learning_stats(),
            "ai_learning": self.learning_agent.get_learning_status(),
            "enforcement": self.enforcement_engine.get_metrics(),
            "self_protection": self.self_protection.get_status(),
            "unified_sessions": len(self.sessions),
            "segment_configs": self.segment_configs
        }


# Singleton instance
unified_vran_service = UnifiedVRANService()
