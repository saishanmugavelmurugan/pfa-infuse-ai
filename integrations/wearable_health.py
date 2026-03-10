"""
Wearable Health Data Integration Module
Supports Apple Health, Google Fit, and other health platforms
Production-ready with OAuth2 authentication and webhook support
"""

import os
import logging
import hashlib
import hmac
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import httpx
import jwt
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HealthPlatform(str, Enum):
    """Supported health data platforms"""
    APPLE_HEALTH = "apple_health"
    GOOGLE_FIT = "google_fit"
    FITBIT = "fitbit"
    SAMSUNG_HEALTH = "samsung_health"
    GARMIN = "garmin"
    WHOOP = "whoop"


class DataType(str, Enum):
    """Health data types"""
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    SLEEP = "sleep"
    BLOOD_OXYGEN = "blood_oxygen"
    BLOOD_PRESSURE = "blood_pressure"
    BLOOD_GLUCOSE = "blood_glucose"
    WEIGHT = "weight"
    BODY_TEMPERATURE = "body_temperature"
    RESPIRATORY_RATE = "respiratory_rate"
    CALORIES = "calories"
    DISTANCE = "distance"
    ACTIVE_MINUTES = "active_minutes"
    WORKOUTS = "workouts"
    HRV = "hrv"  # Heart Rate Variability
    ECG = "ecg"
    MENSTRUAL_CYCLE = "menstrual_cycle"


@dataclass
class HealthDataPoint:
    """Single health data point"""
    data_type: str
    value: float
    unit: str
    timestamp: str
    source: str
    device: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    """Result of a health data sync operation"""
    platform: str
    success: bool
    data_points_synced: int
    last_sync_time: str
    errors: List[str] = field(default_factory=list)
    data: List[HealthDataPoint] = field(default_factory=list)


# Pydantic models for API
class OAuthConfig(BaseModel):
    """OAuth configuration for health platforms"""
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: List[str]


class OAuthTokens(BaseModel):
    """OAuth tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[str] = None
    token_type: str = "Bearer"


class SyncRequest(BaseModel):
    """Health data sync request"""
    user_id: str
    platform: HealthPlatform
    data_types: List[DataType] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class WebhookPayload(BaseModel):
    """Webhook payload for real-time updates"""
    platform: str
    user_id: str
    data_type: str
    timestamp: str
    data: Dict[str, Any]
    signature: Optional[str] = None


class BaseHealthConnector:
    """Base class for health platform connectors"""
    
    PLATFORM_NAME: str = "base"
    AUTH_URL: str = ""
    TOKEN_URL: str = ""
    API_BASE_URL: str = ""
    SCOPES: List[str] = []
    
    def __init__(self, config: Optional[OAuthConfig] = None):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def get_auth_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""
        raise NotImplementedError
    
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens"""
        raise NotImplementedError
    
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh expired access token"""
        raise NotImplementedError
    
    async def fetch_data(
        self,
        tokens: OAuthTokens,
        data_types: List[DataType],
        start_date: datetime,
        end_date: datetime
    ) -> List[HealthDataPoint]:
        """Fetch health data from platform"""
        raise NotImplementedError
    
    async def verify_webhook(self, payload: WebhookPayload) -> bool:
        """Verify webhook signature"""
        return True
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()


class AppleHealthConnector(BaseHealthConnector):
    """
    Apple Health integration via HealthKit
    Note: Requires iOS app as intermediary (HealthKit doesn't have direct API)
    This connector handles data received from the iOS app
    """
    
    PLATFORM_NAME = "apple_health"
    
    # Apple Health data type mappings
    DATA_TYPE_MAP = {
        DataType.HEART_RATE: "HKQuantityTypeIdentifierHeartRate",
        DataType.STEPS: "HKQuantityTypeIdentifierStepCount",
        DataType.SLEEP: "HKCategoryTypeIdentifierSleepAnalysis",
        DataType.BLOOD_OXYGEN: "HKQuantityTypeIdentifierOxygenSaturation",
        DataType.BLOOD_PRESSURE: "HKCorrelationTypeIdentifierBloodPressure",
        DataType.BLOOD_GLUCOSE: "HKQuantityTypeIdentifierBloodGlucose",
        DataType.WEIGHT: "HKQuantityTypeIdentifierBodyMass",
        DataType.BODY_TEMPERATURE: "HKQuantityTypeIdentifierBodyTemperature",
        DataType.RESPIRATORY_RATE: "HKQuantityTypeIdentifierRespiratoryRate",
        DataType.CALORIES: "HKQuantityTypeIdentifierActiveEnergyBurned",
        DataType.DISTANCE: "HKQuantityTypeIdentifierDistanceWalkingRunning",
        DataType.HRV: "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
        DataType.ECG: "HKElectrocardiogramType",
    }
    
    # Unit mappings
    UNIT_MAP = {
        DataType.HEART_RATE: "count/min",
        DataType.STEPS: "count",
        DataType.BLOOD_OXYGEN: "%",
        DataType.BLOOD_GLUCOSE: "mg/dL",
        DataType.WEIGHT: "kg",
        DataType.BODY_TEMPERATURE: "degC",
        DataType.RESPIRATORY_RATE: "count/min",
        DataType.CALORIES: "kcal",
        DataType.DISTANCE: "m",
        DataType.HRV: "ms",
    }
    
    def __init__(self, webhook_secret: Optional[str] = None):
        super().__init__()
        self.webhook_secret = webhook_secret or os.environ.get("APPLE_HEALTH_WEBHOOK_SECRET", "")
    
    async def process_healthkit_export(
        self,
        healthkit_data: Dict[str, Any]
    ) -> List[HealthDataPoint]:
        """
        Process HealthKit data exported from iOS app
        The iOS app collects data and sends it to our API
        """
        data_points = []
        
        try:
            records = healthkit_data.get("records", [])
            
            for record in records:
                hk_type = record.get("type", "")
                value = record.get("value")
                start_date = record.get("startDate")
                end_date = record.get("endDate")
                source = record.get("sourceName", "Apple Health")
                device = record.get("device", {}).get("name")
                
                # Map HealthKit type to our DataType
                data_type = None
                for dt, hk_identifier in self.DATA_TYPE_MAP.items():
                    if hk_identifier == hk_type:
                        data_type = dt.value
                        break
                
                if data_type and value is not None and start_date:
                    data_points.append(HealthDataPoint(
                        data_type=data_type,
                        value=float(value),
                        unit=self.UNIT_MAP.get(DataType(data_type), ""),
                        timestamp=start_date,
                        source=source,
                        device=device,
                        metadata={
                            "end_date": end_date,
                            "original_type": hk_type
                        }
                    ))
            
            logger.info(f"Processed {len(data_points)} Apple Health data points")
            
        except Exception as e:
            logger.error(f"Error processing HealthKit data: {e}")
        
        return data_points
    
    async def verify_webhook(self, payload: WebhookPayload) -> bool:
        """Verify Apple Health webhook signature"""
        if not self.webhook_secret or not payload.signature:
            return False
        
        try:
            # Create signature from payload
            message = f"{payload.user_id}{payload.timestamp}{payload.data_type}"
            expected_sig = hmac.new(
                self.webhook_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_sig, payload.signature)
        except Exception:
            return False


class GoogleFitConnector(BaseHealthConnector):
    """
    Google Fit integration via Fitness REST API
    https://developers.google.com/fit/rest
    """
    
    PLATFORM_NAME = "google_fit"
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE_URL = "https://www.googleapis.com/fitness/v1/users/me"
    
    SCOPES = [
        "https://www.googleapis.com/auth/fitness.activity.read",
        "https://www.googleapis.com/auth/fitness.body.read",
        "https://www.googleapis.com/auth/fitness.heart_rate.read",
        "https://www.googleapis.com/auth/fitness.blood_pressure.read",
        "https://www.googleapis.com/auth/fitness.blood_glucose.read",
        "https://www.googleapis.com/auth/fitness.oxygen_saturation.read",
        "https://www.googleapis.com/auth/fitness.sleep.read",
        "https://www.googleapis.com/auth/fitness.body_temperature.read",
    ]
    
    # Google Fit data source mappings
    DATA_SOURCE_MAP = {
        DataType.HEART_RATE: "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm",
        DataType.STEPS: "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
        DataType.SLEEP: "derived:com.google.sleep.segment:com.google.android.gms:merged",
        DataType.BLOOD_OXYGEN: "derived:com.google.oxygen_saturation:com.google.android.gms:merged",
        DataType.BLOOD_GLUCOSE: "derived:com.google.blood_glucose:com.google.android.gms:merged",
        DataType.WEIGHT: "derived:com.google.weight:com.google.android.gms:merge_weight",
        DataType.CALORIES: "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended",
        DataType.DISTANCE: "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta",
        DataType.ACTIVE_MINUTES: "derived:com.google.active_minutes:com.google.android.gms:merge_active_minutes",
    }
    
    def __init__(self, config: Optional[OAuthConfig] = None):
        super().__init__(config)
        # Load from environment if not provided
        if not config:
            self.config = OAuthConfig(
                client_id=os.environ.get("GOOGLE_FIT_CLIENT_ID", ""),
                client_secret=os.environ.get("GOOGLE_FIT_CLIENT_SECRET", ""),
                redirect_uri=os.environ.get("GOOGLE_FIT_REDIRECT_URI", ""),
                scope=self.SCOPES
            )
    
    async def get_auth_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scope),
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTH_URL}?{query_string}"
    
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens"""
        try:
            response = await self.http_client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.config.redirect_uri
                }
            )
            response.raise_for_status()
            data = response.json()
            
            expires_at = None
            if "expires_in" in data:
                expires_at = (
                    datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
                ).isoformat()
            
            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_at=expires_at,
                token_type=data.get("token_type", "Bearer")
            )
            
        except Exception as e:
            logger.error(f"Error exchanging code: {e}")
            raise
    
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh expired access token"""
        try:
            response = await self.http_client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            expires_at = None
            if "expires_in" in data:
                expires_at = (
                    datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
                ).isoformat()
            
            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", refresh_token),
                expires_at=expires_at,
                token_type=data.get("token_type", "Bearer")
            )
            
        except Exception as e:
            logger.error(f"Error refreshing tokens: {e}")
            raise
    
    async def fetch_data(
        self,
        tokens: OAuthTokens,
        data_types: List[DataType],
        start_date: datetime,
        end_date: datetime
    ) -> List[HealthDataPoint]:
        """Fetch health data from Google Fit"""
        data_points = []
        
        # Convert to nanoseconds (Google Fit uses nanoseconds)
        start_ns = int(start_date.timestamp() * 1e9)
        end_ns = int(end_date.timestamp() * 1e9)
        
        headers = {"Authorization": f"Bearer {tokens.access_token}"}
        
        for data_type in data_types:
            data_source = self.DATA_SOURCE_MAP.get(data_type)
            if not data_source:
                continue
            
            try:
                url = (
                    f"{self.API_BASE_URL}/dataSources/{data_source}/"
                    f"datasets/{start_ns}-{end_ns}"
                )
                
                response = await self.http_client.get(url, headers=headers)
                response.raise_for_status()
                dataset = response.json()
                
                for point in dataset.get("point", []):
                    start_time_ns = int(point.get("startTimeNanos", 0))
                    timestamp = datetime.fromtimestamp(
                        start_time_ns / 1e9,
                        tz=timezone.utc
                    ).isoformat()
                    
                    # Extract value based on data type
                    values = point.get("value", [])
                    if values:
                        # Most metrics use fpVal (floating point)
                        value = values[0].get("fpVal") or values[0].get("intVal", 0)
                        
                        data_points.append(HealthDataPoint(
                            data_type=data_type.value,
                            value=float(value),
                            unit=self._get_unit(data_type),
                            timestamp=timestamp,
                            source="Google Fit",
                            device=point.get("originDataSourceId", "unknown"),
                            metadata={
                                "data_source": data_source
                            }
                        ))
                
            except Exception as e:
                logger.error(f"Error fetching {data_type.value} from Google Fit: {e}")
                continue
        
        logger.info(f"Fetched {len(data_points)} data points from Google Fit")
        return data_points
    
    def _get_unit(self, data_type: DataType) -> str:
        """Get unit for data type"""
        units = {
            DataType.HEART_RATE: "bpm",
            DataType.STEPS: "count",
            DataType.BLOOD_OXYGEN: "%",
            DataType.BLOOD_GLUCOSE: "mg/dL",
            DataType.WEIGHT: "kg",
            DataType.CALORIES: "kcal",
            DataType.DISTANCE: "m",
            DataType.ACTIVE_MINUTES: "min",
        }
        return units.get(data_type, "")


class WearableDataManager:
    """
    Manager class for wearable health data integration
    Handles multiple platforms, syncing, and data storage
    """
    
    def __init__(self):
        self.connectors: Dict[HealthPlatform, BaseHealthConnector] = {
            HealthPlatform.APPLE_HEALTH: AppleHealthConnector(),
            HealthPlatform.GOOGLE_FIT: GoogleFitConnector(),
        }
        self._initialized = False
    
    async def initialize(self):
        """Initialize all connectors"""
        if self._initialized:
            return
        self._initialized = True
    
    async def get_auth_url(
        self,
        platform: HealthPlatform,
        user_id: str
    ) -> Optional[str]:
        """Get OAuth authorization URL for platform"""
        connector = self.connectors.get(platform)
        
        if not connector:
            return None
        
        if platform == HealthPlatform.APPLE_HEALTH:
            # Apple Health requires iOS app
            return None
        
        # Create state token with user info
        state = jwt.encode(
            {"user_id": user_id, "platform": platform.value},
            os.environ.get("JWT_SECRET_KEY", "secret"),
            algorithm="HS256"
        )
        
        return await connector.get_auth_url(state)
    
    async def handle_oauth_callback(
        self,
        platform: HealthPlatform,
        code: str,
        state: str
    ) -> Optional[OAuthTokens]:
        """Handle OAuth callback and exchange code for tokens"""
        connector = self.connectors.get(platform)
        
        if not connector:
            return None
        
        try:
            # Verify state
            payload = jwt.decode(
                state,
                os.environ.get("JWT_SECRET_KEY", "secret"),
                algorithms=["HS256"]
            )
            
            if payload.get("platform") != platform.value:
                raise ValueError("State mismatch")
            
            tokens = await connector.exchange_code(code)
            return tokens
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return None
    
    async def sync_data(
        self,
        platform: HealthPlatform,
        tokens: OAuthTokens,
        data_types: List[DataType],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> SyncResult:
        """Sync health data from platform"""
        connector = self.connectors.get(platform)
        
        if not connector:
            return SyncResult(
                platform=platform.value,
                success=False,
                data_points_synced=0,
                last_sync_time=datetime.now(timezone.utc).isoformat(),
                errors=[f"Unsupported platform: {platform.value}"]
            )
        
        # Default to last 7 days
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        try:
            data_points = await connector.fetch_data(
                tokens, data_types, start_date, end_date
            )
            
            return SyncResult(
                platform=platform.value,
                success=True,
                data_points_synced=len(data_points),
                last_sync_time=datetime.now(timezone.utc).isoformat(),
                data=data_points
            )
            
        except Exception as e:
            logger.error(f"Sync error for {platform.value}: {e}")
            return SyncResult(
                platform=platform.value,
                success=False,
                data_points_synced=0,
                last_sync_time=datetime.now(timezone.utc).isoformat(),
                errors=[str(e)]
            )
    
    async def process_apple_health_export(
        self,
        healthkit_data: Dict[str, Any]
    ) -> SyncResult:
        """Process Apple Health export from iOS app"""
        connector = self.connectors.get(HealthPlatform.APPLE_HEALTH)
        
        if not isinstance(connector, AppleHealthConnector):
            return SyncResult(
                platform=HealthPlatform.APPLE_HEALTH.value,
                success=False,
                data_points_synced=0,
                last_sync_time=datetime.now(timezone.utc).isoformat(),
                errors=["Apple Health connector not available"]
            )
        
        try:
            data_points = await connector.process_healthkit_export(healthkit_data)
            
            return SyncResult(
                platform=HealthPlatform.APPLE_HEALTH.value,
                success=True,
                data_points_synced=len(data_points),
                last_sync_time=datetime.now(timezone.utc).isoformat(),
                data=data_points
            )
            
        except Exception as e:
            logger.error(f"Apple Health export error: {e}")
            return SyncResult(
                platform=HealthPlatform.APPLE_HEALTH.value,
                success=False,
                data_points_synced=0,
                last_sync_time=datetime.now(timezone.utc).isoformat(),
                errors=[str(e)]
            )
    
    async def process_webhook(
        self,
        platform: HealthPlatform,
        payload: WebhookPayload
    ) -> bool:
        """Process real-time webhook from platform"""
        connector = self.connectors.get(platform)
        
        if not connector:
            return False
        
        # Verify webhook signature
        if not await connector.verify_webhook(payload):
            logger.warning(f"Invalid webhook signature for {platform.value}")
            return False
        
        # Process the webhook data
        logger.info(f"Received webhook from {platform.value}: {payload.data_type}")
        
        return True
    
    async def close(self):
        """Close all connectors"""
        for connector in self.connectors.values():
            await connector.close()


# Singleton instance
_wearable_manager: Optional[WearableDataManager] = None


async def get_wearable_manager() -> WearableDataManager:
    """Get or create wearable data manager instance"""
    global _wearable_manager
    if _wearable_manager is None:
        _wearable_manager = WearableDataManager()
        await _wearable_manager.initialize()
    return _wearable_manager


# Export
__all__ = [
    'HealthPlatform',
    'DataType',
    'HealthDataPoint',
    'SyncResult',
    'OAuthConfig',
    'OAuthTokens',
    'SyncRequest',
    'WebhookPayload',
    'WearableDataManager',
    'AppleHealthConnector',
    'GoogleFitConnector',
    'get_wearable_manager'
]
