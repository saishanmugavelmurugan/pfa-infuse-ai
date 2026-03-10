"""
Wearable Health Integration API Routes
Handles Apple Health, Google Fit, and other platform integrations
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from integrations.wearable_health import (
    HealthPlatform,
    DataType,
    SyncRequest,
    WebhookPayload,
    OAuthTokens,
    get_wearable_manager,
    HealthDataPoint
)
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/wearables", tags=["Wearable Health Integration"])


# Request/Response Models
class AuthUrlResponse(BaseModel):
    platform: str
    auth_url: Optional[str]
    requires_app: bool = False
    message: str


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class SyncResponse(BaseModel):
    success: bool
    platform: str
    data_points_synced: int
    last_sync_time: str
    errors: List[str] = []
    message: str


class HealthDataResponse(BaseModel):
    data_type: str
    value: float
    unit: str
    timestamp: str
    source: str
    device: Optional[str] = None


class AppleHealthExportRequest(BaseModel):
    """Request body for Apple Health data export from iOS app"""
    records: List[Dict[str, Any]]
    export_date: str
    device_info: Optional[Dict[str, str]] = None


class PlatformStatus(BaseModel):
    platform: str
    connected: bool
    last_sync: Optional[str] = None
    data_types_available: List[str] = []
    token_expires_at: Optional[str] = None


class ConnectedPlatformsResponse(BaseModel):
    platforms: List[PlatformStatus]


# API Endpoints

@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported wearable platforms"""
    return {
        "platforms": [
            {
                "id": HealthPlatform.APPLE_HEALTH.value,
                "name": "Apple Health",
                "icon": "apple",
                "requires_app": True,
                "description": "Connect via HealthTrack Pro iOS app",
                "supported_data_types": [
                    "heart_rate", "steps", "sleep", "blood_oxygen",
                    "blood_pressure", "weight", "calories", "hrv"
                ]
            },
            {
                "id": HealthPlatform.GOOGLE_FIT.value,
                "name": "Google Fit",
                "icon": "google",
                "requires_app": False,
                "description": "Direct OAuth connection",
                "supported_data_types": [
                    "heart_rate", "steps", "sleep", "blood_oxygen",
                    "weight", "calories", "distance", "active_minutes"
                ]
            },
            {
                "id": HealthPlatform.FITBIT.value,
                "name": "Fitbit",
                "icon": "fitbit",
                "requires_app": False,
                "description": "Direct OAuth connection",
                "supported_data_types": [
                    "heart_rate", "steps", "sleep", "weight", "calories"
                ],
                "status": "coming_soon"
            },
            {
                "id": HealthPlatform.SAMSUNG_HEALTH.value,
                "name": "Samsung Health",
                "icon": "samsung",
                "requires_app": True,
                "description": "Connect via Samsung Health SDK",
                "supported_data_types": [
                    "heart_rate", "steps", "sleep", "blood_pressure", "blood_oxygen"
                ],
                "status": "coming_soon"
            },
            {
                "id": HealthPlatform.GARMIN.value,
                "name": "Garmin Connect",
                "icon": "garmin",
                "requires_app": False,
                "description": "Direct OAuth connection",
                "supported_data_types": [
                    "heart_rate", "steps", "sleep", "calories", "workouts"
                ],
                "status": "coming_soon"
            }
        ]
    }


@router.get("/auth/{platform}", response_model=AuthUrlResponse)
async def get_auth_url(
    platform: HealthPlatform,
    current_user: dict = Depends(get_current_user)
):
    """Get OAuth authorization URL for connecting a wearable platform"""
    manager = await get_wearable_manager()
    
    if platform == HealthPlatform.APPLE_HEALTH:
        return AuthUrlResponse(
            platform=platform.value,
            auth_url=None,
            requires_app=True,
            message="Apple Health requires the HealthTrack Pro iOS app. Download and connect from there."
        )
    
    auth_url = await manager.get_auth_url(platform, current_user["user_id"])
    
    if not auth_url:
        raise HTTPException(
            status_code=400,
            detail=f"Platform {platform.value} is not yet supported for direct OAuth"
        )
    
    return AuthUrlResponse(
        platform=platform.value,
        auth_url=auth_url,
        requires_app=False,
        message="Redirect user to this URL to authorize access"
    )


@router.post("/auth/{platform}/callback")
async def oauth_callback(
    platform: HealthPlatform,
    request: OAuthCallbackRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Handle OAuth callback and store tokens"""
    manager = await get_wearable_manager()
    
    tokens = await manager.handle_oauth_callback(platform, request.code, request.state)
    
    if not tokens:
        raise HTTPException(
            status_code=400,
            detail="Failed to exchange authorization code"
        )
    
    # Store tokens in database
    await db.user_wearable_connections.update_one(
        {"user_id": current_user["user_id"], "platform": platform.value},
        {
            "$set": {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "expires_at": tokens.expires_at,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_sync": None
            }
        },
        upsert=True
    )
    
    return {
        "success": True,
        "platform": platform.value,
        "message": f"Successfully connected to {platform.value}"
    }


@router.post("/sync/{platform}", response_model=SyncResponse)
async def sync_platform_data(
    platform: HealthPlatform,
    data_types: List[DataType] = Query(default=[DataType.HEART_RATE, DataType.STEPS]),
    days: int = Query(default=7, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Sync health data from connected platform"""
    # Get stored tokens
    connection = await db.user_wearable_connections.find_one(
        {"user_id": current_user["user_id"], "platform": platform.value},
        {"_id": 0}
    )
    
    if not connection:
        raise HTTPException(
            status_code=400,
            detail=f"Platform {platform.value} is not connected. Please authorize first."
        )
    
    tokens = OAuthTokens(
        access_token=connection.get("access_token", ""),
        refresh_token=connection.get("refresh_token"),
        expires_at=connection.get("expires_at")
    )
    
    # Check if token expired
    if tokens.expires_at:
        expires = datetime.fromisoformat(tokens.expires_at.replace("Z", "+00:00"))
        if expires < datetime.now(timezone.utc):
            # Try to refresh
            manager = await get_wearable_manager()
            if tokens.refresh_token:
                try:
                    connector = manager.connectors.get(platform)
                    new_tokens = await connector.refresh_tokens(tokens.refresh_token)
                    tokens = new_tokens
                    
                    # Update stored tokens
                    await db.user_wearable_connections.update_one(
                        {"user_id": current_user["user_id"], "platform": platform.value},
                        {"$set": {
                            "access_token": new_tokens.access_token,
                            "refresh_token": new_tokens.refresh_token,
                            "expires_at": new_tokens.expires_at
                        }}
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=401,
                        detail="Token expired. Please reconnect the platform."
                    )
            else:
                raise HTTPException(
                    status_code=401,
                    detail="Token expired. Please reconnect the platform."
                )
    
    # Perform sync
    manager = await get_wearable_manager()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    result = await manager.sync_data(platform, tokens, data_types, start_date, end_date)
    
    if result.success and result.data:
        # Store synced data
        for data_point in result.data:
            await db.user_health_data.update_one(
                {
                    "user_id": current_user["user_id"],
                    "data_type": data_point.data_type,
                    "timestamp": data_point.timestamp,
                    "source": data_point.source
                },
                {
                    "$set": {
                        "value": data_point.value,
                        "unit": data_point.unit,
                        "device": data_point.device,
                        "metadata": data_point.metadata,
                        "synced_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
        
        # Update last sync time
        await db.user_wearable_connections.update_one(
            {"user_id": current_user["user_id"], "platform": platform.value},
            {"$set": {"last_sync": datetime.now(timezone.utc).isoformat()}}
        )
    
    return SyncResponse(
        success=result.success,
        platform=result.platform,
        data_points_synced=result.data_points_synced,
        last_sync_time=result.last_sync_time,
        errors=result.errors,
        message=f"Synced {result.data_points_synced} data points from {platform.value}"
    )


@router.post("/apple-health/import", response_model=SyncResponse)
async def import_apple_health_data(
    request: AppleHealthExportRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Import Apple Health data from iOS app export
    Called by the HealthTrack Pro iOS app
    """
    manager = await get_wearable_manager()
    
    result = await manager.process_apple_health_export({"records": request.records})
    
    if result.success and result.data:
        # Store synced data
        for data_point in result.data:
            await db.user_health_data.update_one(
                {
                    "user_id": current_user["user_id"],
                    "data_type": data_point.data_type,
                    "timestamp": data_point.timestamp,
                    "source": data_point.source
                },
                {
                    "$set": {
                        "value": data_point.value,
                        "unit": data_point.unit,
                        "device": data_point.device,
                        "metadata": data_point.metadata,
                        "synced_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
        
        # Update connection status
        await db.user_wearable_connections.update_one(
            {"user_id": current_user["user_id"], "platform": HealthPlatform.APPLE_HEALTH.value},
            {
                "$set": {
                    "connected_at": datetime.now(timezone.utc).isoformat(),
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "device_info": request.device_info
                }
            },
            upsert=True
        )
    
    return SyncResponse(
        success=result.success,
        platform=HealthPlatform.APPLE_HEALTH.value,
        data_points_synced=result.data_points_synced,
        last_sync_time=result.last_sync_time,
        errors=result.errors,
        message=f"Imported {result.data_points_synced} records from Apple Health"
    )


@router.get("/data/{data_type}", response_model=List[HealthDataResponse])
async def get_health_data(
    data_type: DataType,
    days: int = Query(default=7, ge=1, le=90),
    platform: Optional[HealthPlatform] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get synced health data for a specific data type"""
    query = {
        "user_id": current_user["user_id"],
        "data_type": data_type.value,
        "timestamp": {
            "$gte": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        }
    }
    
    if platform:
        query["source"] = {"$regex": platform.value, "$options": "i"}
    
    cursor = db.user_health_data.find(query, {"_id": 0}).sort("timestamp", -1).limit(1000)
    data = await cursor.to_list(length=1000)
    
    return [
        HealthDataResponse(
            data_type=d["data_type"],
            value=d["value"],
            unit=d.get("unit", ""),
            timestamp=d["timestamp"],
            source=d.get("source", "unknown"),
            device=d.get("device")
        )
        for d in data
    ]


@router.get("/connected", response_model=ConnectedPlatformsResponse)
async def get_connected_platforms(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get list of connected wearable platforms for current user"""
    cursor = db.user_wearable_connections.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    connections = await cursor.to_list(length=20)
    
    platforms = []
    for conn in connections:
        platform = conn.get("platform", "")
        
        # Check if token is expired
        token_expires = conn.get("expires_at")
        is_connected = True
        if token_expires:
            try:
                expires_dt = datetime.fromisoformat(token_expires.replace("Z", "+00:00"))
                is_connected = expires_dt > datetime.now(timezone.utc)
            except ValueError:
                pass
        
        platforms.append(PlatformStatus(
            platform=platform,
            connected=is_connected,
            last_sync=conn.get("last_sync"),
            token_expires_at=token_expires,
            data_types_available=conn.get("data_types", [])
        ))
    
    return ConnectedPlatformsResponse(platforms=platforms)


@router.delete("/disconnect/{platform}")
async def disconnect_platform(
    platform: HealthPlatform,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Disconnect a wearable platform"""
    result = await db.user_wearable_connections.delete_one({
        "user_id": current_user["user_id"],
        "platform": platform.value
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Platform {platform.value} was not connected"
        )
    
    return {
        "success": True,
        "message": f"Disconnected from {platform.value}"
    }


@router.post("/webhook/{platform}")
async def receive_webhook(
    platform: HealthPlatform,
    payload: WebhookPayload,
    db = Depends(get_db)
):
    """
    Receive real-time webhook updates from wearable platforms
    Used for instant data sync when new data is available
    """
    manager = await get_wearable_manager()
    
    # Verify and process webhook
    is_valid = await manager.process_webhook(platform, payload)
    
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature"
        )
    
    # Store the webhook data
    await db.user_health_data.update_one(
        {
            "user_id": payload.user_id,
            "data_type": payload.data_type,
            "timestamp": payload.timestamp,
            "source": platform.value
        },
        {
            "$set": {
                "value": payload.data.get("value"),
                "unit": payload.data.get("unit", ""),
                "metadata": payload.data,
                "synced_at": datetime.now(timezone.utc).isoformat(),
                "via_webhook": True
            }
        },
        upsert=True
    )
    
    return {"success": True, "message": "Webhook processed"}


@router.get("/summary")
async def get_health_summary(
    days: int = Query(default=7, ge=1, le=30),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get aggregated health summary from all connected platforms"""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Aggregate data by type
    pipeline = [
        {
            "$match": {
                "user_id": current_user["user_id"],
                "timestamp": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$data_type",
                "avg_value": {"$avg": "$value"},
                "min_value": {"$min": "$value"},
                "max_value": {"$max": "$value"},
                "count": {"$sum": 1},
                "latest_timestamp": {"$max": "$timestamp"},
                "sources": {"$addToSet": "$source"}
            }
        }
    ]
    
    cursor = db.user_health_data.aggregate(pipeline)
    results = await cursor.to_list(length=100)
    
    summary = {}
    for result in results:
        data_type = result["_id"]
        summary[data_type] = {
            "average": round(result["avg_value"], 2),
            "minimum": round(result["min_value"], 2),
            "maximum": round(result["max_value"], 2),
            "data_points": result["count"],
            "latest_reading": result["latest_timestamp"],
            "sources": result["sources"]
        }
    
    # Get connected platforms
    connections = await db.user_wearable_connections.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0, "platform": 1, "last_sync": 1}
    ).to_list(length=10)
    
    return {
        "period_days": days,
        "summary": summary,
        "connected_platforms": connections,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
