import os
import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class AISecurityService:
    """
    Enterprise/Telco-grade AI Security Service
    NetFlow-based threat detection with automated enforcement
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.environ.get('EMERGENT_LLM_KEY'),
            base_url="https://llm.emergent.sh/v1"
        )
        self.model = "gpt-4"
        
        # Telco-grade thresholds
        self.threat_thresholds = {
            'critical': 90.0,
            'high': 75.0,
            'medium': 50.0,
            'low': 25.0
        }
    
    async def analyze_netflow_anomalies(self, flow_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Real-time NetFlow analysis for threat detection
        
        Args:
            flow_data: List of NetFlow records
            
        Returns:
            Threat analysis with automated enforcement recommendations
        """
        try:
            # Aggregate flow statistics for AI analysis
            flow_summary = self._aggregate_flows(flow_data)
            
            prompt = f"""Analyze these NetFlow patterns for security threats:

**Flow Summary:**
- Total Flows: {flow_summary['total_flows']:,}
- Total Bytes: {flow_summary['total_bytes']:,} ({flow_summary['total_bytes']/1024/1024:.2f} MB)
- Total Packets: {flow_summary['total_packets']:,}
- Unique Source IPs: {flow_summary['unique_src_ips']}
- Unique Destination IPs: {flow_summary['unique_dst_ips']}
- Time Window: {flow_summary['duration_minutes']} minutes

**Top Source IPs:**
{json.dumps(flow_summary['top_sources'][:10], indent=2)}

**Top Destination IPs:**
{json.dumps(flow_summary['top_destinations'][:10], indent=2)}

**Port Distribution:**
{json.dumps(flow_summary['port_distribution'][:15], indent=2)}

**Protocol Distribution:**
{json.dumps(flow_summary['protocol_distribution'], indent=2)}

**Unusual Patterns Detected:**
{json.dumps(flow_summary.get('anomalies', []), indent=2)}

Provide threat analysis in JSON format:
{{
    "threat_level": "none|low|medium|high|critical",
    "confidence_score": 0-100,
    "threats_identified": [
        {{
            "threat_type": "ddos|port_scan|brute_force|data_exfiltration|botnet|malware_c2|gsm_jamming|unauthorized_access",
            "severity": "low|medium|high|critical",
            "source_ips": ["list of malicious IPs"],
            "target_ips": ["list of targeted IPs"],
            "indicators": ["specific indicators of compromise"],
            "evidence": "flow patterns supporting this threat",
            "confidence": 0-100
        }}
    ],
    "anomalies": [
        {{
            "anomaly_type": "description",
            "severity": "low|medium|high",
            "details": "specific details",
            "affected_ips": []
        }}
    ],
    "enforcement_recommendations": [
        {{
            "action": "block_ip|rate_limit|isolate_device|alert_only",
            "target": "specific IP or device",
            "justification": "reason for this action",
            "priority": "immediate|high|medium|low",
            "auto_executable": true/false,
            "estimated_impact": "impact on operations"
        }}
    ],
    "operational_insights": {{
        "bandwidth_utilization": "assessment",
        "traffic_efficiency": "assessment",
        "optimization_opportunities": []
    }}
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert security analyst specializing in network traffic analysis, 
                        threat detection, and incident response for enterprise and telecom networks. 
                        You have deep knowledge of NetFlow analysis, attack patterns, and automated security enforcement."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for consistent security analysis
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result['analysis_timestamp'] = datetime.utcnow().isoformat()
            result['flows_analyzed'] = len(flow_data)
            
            logger.info(f"Analyzed {len(flow_data)} flows, detected {len(result.get('threats_identified', []))} threats")
            return result
            
        except Exception as e:
            logger.error(f"Error in NetFlow analysis: {str(e)}")
            raise
    
    def _aggregate_flows(self, flow_data: List[Dict]) -> Dict[str, Any]:
        """Aggregate NetFlow data for efficient analysis"""
        
        from collections import Counter
        
        total_flows = len(flow_data)
        total_bytes = sum(f.get('bytes_transferred', 0) for f in flow_data)
        total_packets = sum(f.get('packets', 0) for f in flow_data)
        
        src_ips = [f['src_ip'] for f in flow_data]
        dst_ips = [f['dst_ip'] for f in flow_data]
        
        src_counter = Counter(src_ips)
        dst_counter = Counter(dst_ips)
        
        # Port analysis
        port_counter = Counter()
        for f in flow_data:
            port_counter[f.get('dst_port')] += 1
        
        # Protocol analysis
        protocol_map = {6: 'TCP', 17: 'UDP', 1: 'ICMP'}
        protocol_counter = Counter()
        for f in flow_data:
            proto = protocol_map.get(f.get('protocol'), f'OTHER_{f.get("protocol")}')
            protocol_counter[proto] += 1
        
        # Detect anomalies
        anomalies = []
        
        # Single source flooding multiple destinations
        for src, count in src_counter.most_common(5):
            if count > total_flows * 0.2:  # Single source > 20% of traffic
                anomalies.append({
                    'type': 'potential_scanning',
                    'source_ip': src,
                    'flow_count': count,
                    'percentage': (count/total_flows)*100
                })
        
        return {
            'total_flows': total_flows,
            'total_bytes': total_bytes,
            'total_packets': total_packets,
            'unique_src_ips': len(src_counter),
            'unique_dst_ips': len(dst_counter),
            'top_sources': [{'ip': ip, 'flows': count} for ip, count in src_counter.most_common(20)],
            'top_destinations': [{'ip': ip, 'flows': count} for ip, count in dst_counter.most_common(20)],
            'port_distribution': [{'port': port, 'connections': count} for port, count in port_counter.most_common(20)],
            'protocol_distribution': dict(protocol_counter),
            'duration_minutes': 5,  # Configurable analysis window
            'anomalies': anomalies
        }
    
    async def threat_intelligence_lookup(self, ip_address: str) -> Dict[str, Any]:
        """
        AI-powered threat intelligence lookup
        """
        try:
            prompt = f"""Analyze this IP address for threat intelligence: {ip_address}

Based on the IP address pattern and characteristics, provide threat assessment:

{{
    "is_malicious": true/false,
    "threat_level": "none|low|medium|high|critical",
    "threat_categories": ["botnet", "spam", "malware", "proxy", etc.],
    "geolocation_risk": "assessment based on IP origin",
    "recommended_action": "allow|monitor|rate_limit|block",
    "confidence": 0-100,
    "reasoning": "explanation of assessment"
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a threat intelligence analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error in threat intelligence lookup: {str(e)}")
            raise
    
    async def generate_enforcement_policy(self, threat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate automated enforcement policy based on threat analysis
        """
        try:
            prompt = f"""Generate an automated enforcement policy for this threat:

**Threat Details:**
{json.dumps(threat_data, indent=2)}

Create enforcement policy in JSON format:
{{
    "policy_name": "descriptive name",
    "enforcement_type": "block|rate_limit|isolate|monitor",
    "rules": [
        {{
            "condition": "specific condition to match",
            "action": "specific action to take",
            "parameters": {{}}
        }}
    ],
    "auto_execute": true/false,
    "duration": "temporary|permanent",
    "duration_hours": number (if temporary),
    "rollback_conditions": ["conditions to rollback policy"],
    "impact_assessment": {{
        "affected_services": [],
        "business_impact": "low|medium|high",
        "estimated_downtime": "none|minimal|significant"
    }},
    "approval_required": true/false,
    "notification_required": true/false
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security automation engineer specializing in policy creation and enforcement."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error generating enforcement policy: {str(e)}")
            raise
    
    async def predict_threat_progression(self, threat_history: List[Dict]) -> Dict[str, Any]:
        """
        Predict how a threat will evolve - Telco-grade predictive analysis
        """
        try:
            prompt = f"""Analyze this threat progression and predict next steps:

**Threat Timeline:**
{json.dumps(threat_history, indent=2)}

Provide prediction in JSON format:
{{
    "progression_likelihood": "low|medium|high",
    "predicted_next_steps": ["list of likely next attack steps"],
    "estimated_timeline": "minutes|hours|days",
    "potential_targets": ["likely next targets"],
    "recommended_preemptive_actions": [
        {{
            "action": "description",
            "justification": "why this is needed",
            "urgency": "immediate|soon|monitor"
        }}
    ],
    "threat_sophistication": "low|medium|high|advanced_persistent",
    "attacker_profile": "description of likely attacker type",
    "mitigation_priority": "critical|high|medium|low"
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a threat prediction specialist with expertise in attack patterns and progression analysis."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error predicting threat progression: {str(e)}")
            raise
    
    async def analyze_gsm_security(self, gsm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Telco-specific GSM/4G/5G security analysis
        """
        try:
            prompt = f"""Analyze GSM/cellular network security:

**GSM Network Data:**
{json.dumps(gsm_data, indent=2)}

Provide security analysis in JSON format:
{{
    "security_status": "secure|at_risk|compromised",
    "threats_detected": [
        {{
            "threat_type": "gsm_jamming|imsi_catcher|ss7_attack|roaming_fraud|etc",
            "severity": "low|medium|high|critical",
            "indicators": [],
            "affected_subscribers": number,
            "estimated_impact": "description"
        }}
    ],
    "network_vulnerabilities": [],
    "encryption_status": "assessment of encryption",
    "recommendations": [
        {{
            "action": "specific recommendation",
            "priority": "immediate|high|medium",
            "complexity": "simple|moderate|complex"
        }}
    ],
    "compliance_issues": []
}}"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a telecommunications security expert specializing in GSM, 4G, and 5G network security."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing GSM security: {str(e)}")
            raise

# Singleton instance
ai_security_service = AISecurityService()
