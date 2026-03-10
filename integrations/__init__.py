"""
Integrations module initialization
"""

from integrations.wearable_health import (
    HealthPlatform,
    DataType,
    HealthDataPoint,
    SyncResult,
    OAuthConfig,
    OAuthTokens,
    SyncRequest,
    WebhookPayload,
    WearableDataManager,
    AppleHealthConnector,
    GoogleFitConnector,
    get_wearable_manager
)

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
