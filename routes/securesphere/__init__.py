"""
SecureSphere Routes Package
"""

from .url_scanner import router as url_scanner_router
from .sms_analyzer import router as sms_analyzer_router
from .threat_scoring import router as threat_scoring_router
from .device_registry import router as device_registry_router
from .dashboard import router as dashboard_router
from .telecom_adapter import router as telecom_adapter_router
from .automotive_security import router as automotive_security_router
from .ai_agents import router as ai_agents_router
from .iot_security import router as iot_security_router
from .gsm_fraud import router as gsm_fraud_router
from .automotive_advanced import router as automotive_advanced_router
from .analytics import router as analytics_router
from .reports import router as reports_router
from .csp_operations import router as csp_operations_router

__all__ = [
    "url_scanner_router",
    "sms_analyzer_router",
    "threat_scoring_router",
    "device_registry_router",
    "dashboard_router",
    "telecom_adapter_router",
    "automotive_security_router",
    "ai_agents_router",
    "iot_security_router",
    "gsm_fraud_router",
    "automotive_advanced_router",
    "analytics_router",
    "reports_router",
    "csp_operations_router"
]
