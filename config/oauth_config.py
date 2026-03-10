"""
Health Platform OAuth Configuration
Centralized configuration for all health platform integrations
"""

import os
from typing import Dict, Any, Optional
from enum import Enum


class HealthPlatform(str, Enum):
    APPLE_HEALTH = "apple_health"
    GOOGLE_FIT = "google_fit"
    FITBIT = "fitbit"
    SAMSUNG_HEALTH = "samsung_health"
    GARMIN_CONNECT = "garmin_connect"


class OAuthConfig:
    """OAuth configuration manager for health platforms"""
    
    def __init__(self):
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()
    
    def _get_redirect_uri(self, provider: str) -> str:
        """Get environment-aware redirect URI for OAuth providers"""
        # Check for explicit redirect URI in environment
        explicit_uri = os.environ.get("HEALTH_OAUTH_REDIRECT_URI")
        if explicit_uri:
            # If explicit URI doesn't include provider, append it
            if not explicit_uri.endswith(provider):
                return f"{explicit_uri.rstrip('/')}/{provider}"
            return explicit_uri
        
        # Build from APP_URL or REACT_APP_BACKEND_URL
        base_url = os.environ.get("APP_URL") or os.environ.get("REACT_APP_BACKEND_URL", "")
        if base_url:
            return f"{base_url.rstrip('/')}/api/health-sync/callback/{provider}"
        
        # Fallback: require environment variable to be set
        # Return empty string which will cause OAuth to fail gracefully with clear error
        return ""
    
    def _load_configs(self):
        """Load OAuth configurations from environment variables"""
        
        # Google Fit OAuth 2.0
        self._configs["google_fit"] = {
            "name": "Google Fit",
            "enabled": bool(os.environ.get("GOOGLE_FIT_CLIENT_ID")),
            "auth_type": "oauth2",
            "client_id": os.environ.get("GOOGLE_FIT_CLIENT_ID", ""),
            "client_secret": os.environ.get("GOOGLE_FIT_CLIENT_SECRET", ""),
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "api_base_url": "https://www.googleapis.com/fitness/v1/users/me",
            "scopes": [
                "https://www.googleapis.com/auth/fitness.activity.read",
                "https://www.googleapis.com/auth/fitness.body.read",
                "https://www.googleapis.com/auth/fitness.heart_rate.read",
                "https://www.googleapis.com/auth/fitness.sleep.read",
                "https://www.googleapis.com/auth/fitness.blood_glucose.read",
                "https://www.googleapis.com/auth/fitness.blood_pressure.read",
                "https://www.googleapis.com/auth/fitness.oxygen_saturation.read"
            ],
            "redirect_uri": self._get_redirect_uri("google_fit"),
            "supported_data_types": [
                "steps", "heart_rate", "sleep", "activity", "weight",
                "blood_pressure", "blood_glucose", "oxygen_saturation"
            ],
            "icon": "google",
            "color": "#4285F4"
        }
        
        # Fitbit OAuth 2.0
        self._configs["fitbit"] = {
            "name": "Fitbit",
            "enabled": bool(os.environ.get("FITBIT_CLIENT_ID")),
            "auth_type": "oauth2",
            "client_id": os.environ.get("FITBIT_CLIENT_ID", ""),
            "client_secret": os.environ.get("FITBIT_CLIENT_SECRET", ""),
            "auth_url": "https://www.fitbit.com/oauth2/authorize",
            "token_url": "https://api.fitbit.com/oauth2/token",
            "api_base_url": "https://api.fitbit.com/1/user/-",
            "scopes": ["activity", "heartrate", "sleep", "weight", "nutrition", "profile"],
            "redirect_uri": self._get_redirect_uri("fitbit"),
            "supported_data_types": [
                "steps", "heart_rate", "sleep", "activity", "weight",
                "nutrition", "hydration", "stress"
            ],
            "icon": "fitbit",
            "color": "#00B0B9",
            "rate_limit": {
                "requests_per_hour": 150,
                "requests_per_user_per_hour": 150
            }
        }
        
        # Garmin Connect OAuth 1.0a
        self._configs["garmin_connect"] = {
            "name": "Garmin Connect",
            "enabled": bool(os.environ.get("GARMIN_CONSUMER_KEY")),
            "auth_type": "oauth1",
            "consumer_key": os.environ.get("GARMIN_CONSUMER_KEY", ""),
            "consumer_secret": os.environ.get("GARMIN_CONSUMER_SECRET", ""),
            "request_token_url": "https://connectapi.garmin.com/oauth-service/oauth/request_token",
            "auth_url": "https://connect.garmin.com/oauthConfirm",
            "access_token_url": "https://connectapi.garmin.com/oauth-service/oauth/access_token",
            "api_base_url": "https://apis.garmin.com",
            "callback_url": self._get_redirect_uri("garmin_connect"),
            "supported_data_types": [
                "steps", "heart_rate", "sleep", "activity", "weight",
                "stress", "respiratory_rate", "body_temperature"
            ],
            "icon": "garmin",
            "color": "#007CC3",
            "webhook_verification_token": os.environ.get("GARMIN_WEBHOOK_TOKEN", "")
        }
        
        # Apple Health (on-device SDK)
        self._configs["apple_health"] = {
            "name": "Apple Health",
            "enabled": True,  # Always enabled, requires mobile SDK
            "auth_type": "on_device",
            "setup_url": "infuse://health/connect/apple",
            "supported_data_types": [
                "steps", "heart_rate", "sleep", "activity", "weight",
                "blood_pressure", "blood_glucose", "oxygen_saturation",
                "respiratory_rate", "menstrual_cycle", "mindfulness"
            ],
            "icon": "apple",
            "color": "#000000",
            "requires_healthkit": True,
            "info_plist_keys": [
                "NSHealthShareUsageDescription",
                "NSHealthUpdateUsageDescription"
            ]
        }
        
        # Samsung Health (SDK)
        self._configs["samsung_health"] = {
            "name": "Samsung Health",
            "enabled": True,  # Requires mobile SDK
            "auth_type": "sdk",
            "setup_url": "infuse://health/connect/samsung",
            "partner_app_id": os.environ.get("SAMSUNG_HEALTH_APP_ID", ""),
            "supported_data_types": [
                "steps", "heart_rate", "sleep", "activity", "weight",
                "blood_pressure", "blood_glucose", "oxygen_saturation", "stress"
            ],
            "icon": "samsung",
            "color": "#1428A0",
            "sdk_version": "1.5.0"
        }
    
    def get_config(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific platform"""
        return self._configs.get(platform)
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all platform configurations"""
        return self._configs
    
    def is_enabled(self, platform: str) -> bool:
        """Check if a platform is enabled (has credentials configured)"""
        config = self._configs.get(platform, {})
        return config.get("enabled", False)
    
    def get_enabled_platforms(self) -> list:
        """Get list of enabled platforms"""
        return [p for p, c in self._configs.items() if c.get("enabled", False)]
    
    def get_oauth_url(self, platform: str, state: str) -> Optional[str]:
        """Generate OAuth authorization URL for a platform"""
        config = self._configs.get(platform)
        
        if not config or not config.get("enabled"):
            return None
        
        if config["auth_type"] == "oauth2":
            scopes = "+".join(config.get("scopes", []))
            return (
                f"{config['auth_url']}?"
                f"client_id={config['client_id']}&"
                f"redirect_uri={config['redirect_uri']}&"
                f"scope={scopes}&"
                f"state={state}&"
                f"response_type=code&"
                f"access_type=offline&"
                f"prompt=consent"
            )
        
        return None
    
    def get_public_config(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get public configuration (no secrets) for a platform"""
        config = self._configs.get(platform)
        if not config:
            return None
        
        # Return only non-sensitive fields
        return {
            "name": config.get("name"),
            "enabled": config.get("enabled"),
            "auth_type": config.get("auth_type"),
            "supported_data_types": config.get("supported_data_types"),
            "icon": config.get("icon"),
            "color": config.get("color"),
            "setup_url": config.get("setup_url"),
            "requires_mobile": config["auth_type"] in ["on_device", "sdk"]
        }


# Singleton instance
oauth_config = OAuthConfig()


def get_oauth_config() -> OAuthConfig:
    """Get OAuth configuration singleton"""
    return oauth_config
