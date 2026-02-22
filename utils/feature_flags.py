"""
Feature Flags System - Modular Feature Management
Allows enabling/disabling features without database changes
"""
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import os
import json

# Default feature configuration - can be overridden by environment variables
DEFAULT_FEATURES = {
    # HealthTrack Pro Features
    "healthtrack": {
        "enabled": True,
        "features": {
            "patient_management": {"enabled": True, "tier": "free"},
            "appointment_scheduling": {"enabled": True, "tier": "free"},
            "prescription_management": {"enabled": True, "tier": "free"},
            "lab_reports": {"enabled": True, "tier": "free"},
            "medical_records": {"enabled": True, "tier": "free"},
            "billing": {"enabled": True, "tier": "basic"},
            "ai_analytics": {"enabled": True, "tier": "pro"},
            "wearable_integration": {"enabled": True, "tier": "pro"},
            "abdm_integration": {"enabled": True, "tier": "enterprise"},
            "ai_health_insights": {"enabled": True, "tier": "pro"},
            "drug_database": {"enabled": True, "tier": "free"},
            "health_schemes": {"enabled": True, "tier": "free"},
        }
    },
    
    # SecureSphere Features
    "securesphere": {
        "enabled": True,
        "features": {
            "url_scanner": {"enabled": True, "tier": "free"},
            "sms_analyzer": {"enabled": True, "tier": "free"},
            "device_registry": {"enabled": True, "tier": "free"},
            "threat_scoring": {"enabled": True, "tier": "basic"},
            "iot_security": {"enabled": True, "tier": "pro"},
            "gsm_fraud_detection": {"enabled": True, "tier": "pro"},
            "telecom_integration": {"enabled": True, "tier": "enterprise"},
            "automotive_security": {"enabled": True, "tier": "enterprise"},
            "webhooks": {"enabled": True, "tier": "basic"},
            "oem_sdk": {"enabled": True, "tier": "enterprise"},
            "analytics_reports": {"enabled": True, "tier": "basic"},
        }
    },
    
    # Platform Features
    "platform": {
        "enabled": True,
        "features": {
            "multi_language": {"enabled": True, "tier": "free"},
            "dark_mode": {"enabled": True, "tier": "free"},
            "notifications": {"enabled": True, "tier": "free"},
            "email_alerts": {"enabled": False, "tier": "basic", "requires_config": ["SENDGRID_API_KEY"]},
            "sms_alerts": {"enabled": False, "tier": "pro", "requires_config": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]},
            "whatsapp_alerts": {"enabled": False, "tier": "pro", "requires_config": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]},
            "push_notifications": {"enabled": True, "tier": "basic"},
            "pwa_support": {"enabled": True, "tier": "free"},
            "mobile_apps": {"enabled": True, "tier": "free"},
        }
    },
    
    # Admin Features
    "admin": {
        "enabled": True,
        "features": {
            "user_management": {"enabled": True, "tier": "free"},
            "analytics_dashboard": {"enabled": True, "tier": "basic"},
            "audit_logs": {"enabled": True, "tier": "pro"},
            "api_key_management": {"enabled": True, "tier": "enterprise"},
            "ip_whitelisting": {"enabled": True, "tier": "enterprise"},
            "sso_integration": {"enabled": True, "tier": "enterprise"},
        }
    }
}

class FeatureFlags:
    _instance = None
    _features = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._features = cls._load_features()
        return cls._instance
    
    @classmethod
    def _load_features(cls) -> Dict:
        """Load features from environment or use defaults"""
        # Try to load from environment variable
        features_json = os.environ.get("FEATURE_FLAGS")
        if features_json:
            try:
                return json.loads(features_json)
            except json.JSONDecodeError:
                pass
        
        # Try to load from file
        config_path = os.environ.get("FEATURE_FLAGS_PATH", "/app/backend/config/features.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return DEFAULT_FEATURES.copy()
    
    @classmethod
    def reload(cls):
        """Reload features from source"""
        cls._features = cls._load_features()
    
    @classmethod
    def get_all(cls) -> Dict:
        """Get all feature flags"""
        if cls._features is None:
            cls._features = cls._load_features()
        return cls._features
    
    @classmethod
    def is_enabled(cls, product: str, feature: str) -> bool:
        """Check if a specific feature is enabled"""
        features = cls.get_all()
        
        if product not in features:
            return False
        
        product_config = features[product]
        if not product_config.get("enabled", False):
            return False
        
        feature_config = product_config.get("features", {}).get(feature, {})
        return feature_config.get("enabled", False)
    
    @classmethod
    def get_feature(cls, product: str, feature: str) -> Optional[Dict]:
        """Get feature configuration"""
        features = cls.get_all()
        
        if product not in features:
            return None
        
        return features[product].get("features", {}).get(feature)
    
    @classmethod
    def get_product_features(cls, product: str) -> Dict:
        """Get all features for a product"""
        features = cls.get_all()
        return features.get(product, {}).get("features", {})
    
    @classmethod
    def set_feature(cls, product: str, feature: str, enabled: bool):
        """Enable or disable a feature (runtime only)"""
        if cls._features is None:
            cls._features = cls._load_features()
        
        if product in cls._features and feature in cls._features[product].get("features", {}):
            cls._features[product]["features"][feature]["enabled"] = enabled
    
    @classmethod
    def set_feature_enabled(cls, product: str, feature: str, enabled: bool) -> bool:
        """Enable or disable a feature - returns success status"""
        if cls._features is None:
            cls._features = cls._load_features()
        
        if product not in cls._features:
            return False
        
        if "features" not in cls._features[product]:
            return False
        
        if feature not in cls._features[product]["features"]:
            return False
        
        cls._features[product]["features"][feature]["enabled"] = enabled
        return True
    
    @classmethod
    def set_product_enabled(cls, product: str, enabled: bool) -> bool:
        """Enable or disable an entire product - returns success status"""
        if cls._features is None:
            cls._features = cls._load_features()
        
        if product not in cls._features:
            return False
        
        cls._features[product]["enabled"] = enabled
        return True
    
    @classmethod
    def update_feature_config(cls, product: str, feature: str, config: Dict) -> bool:
        """Update feature configuration - returns success status"""
        if cls._features is None:
            cls._features = cls._load_features()
        
        if product not in cls._features:
            return False
        
        if "features" not in cls._features[product]:
            return False
        
        if feature not in cls._features[product]["features"]:
            return False
        
        # Update the configuration
        for key, value in config.items():
            cls._features[product]["features"][feature][key] = value
        
        return True
    
    @classmethod
    def get_enabled_features(cls, product: str, tier: str = "free") -> List[str]:
        """Get list of enabled features for a product and tier"""
        tier_hierarchy = ["free", "basic", "pro", "enterprise"]
        tier_index = tier_hierarchy.index(tier) if tier in tier_hierarchy else 0
        
        features = cls.get_product_features(product)
        enabled = []
        
        for name, config in features.items():
            if config.get("enabled", False):
                feature_tier = config.get("tier", "free")
                feature_tier_index = tier_hierarchy.index(feature_tier) if feature_tier in tier_hierarchy else 0
                
                if feature_tier_index <= tier_index:
                    enabled.append(name)
        
        return enabled


# Singleton instance
feature_flags = FeatureFlags()


# FastAPI dependency
def get_feature_flags():
    return feature_flags
