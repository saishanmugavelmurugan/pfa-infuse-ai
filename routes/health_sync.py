"""
Comprehensive Health Data Sync API
Integrates with: Apple Health, Google Fit, Fitbit, Samsung Health, Garmin Connect
Provides unified health data interface with smart reminders
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import dependencies
from enum import Enum

router = APIRouter(prefix="/health-sync", tags=["Health Data Sync"])


class HealthPlatform(str, Enum):
    APPLE_HEALTH = "apple_health"
    GOOGLE_FIT = "google_fit"
    FITBIT = "fitbit"
    SAMSUNG_HEALTH = "samsung_health"
    GARMIN_CONNECT = "garmin_connect"


class DataCategory(str, Enum):
    STEPS = "steps"
    HEART_RATE = "heart_rate"
    SLEEP = "sleep"
    ACTIVITY = "activity"
    NUTRITION = "nutrition"
    WEIGHT = "weight"
    BLOOD_PRESSURE = "blood_pressure"
    BLOOD_GLUCOSE = "blood_glucose"
    OXYGEN_SATURATION = "oxygen_saturation"
    RESPIRATORY_RATE = "respiratory_rate"
    BODY_TEMPERATURE = "body_temperature"
    MENSTRUAL_CYCLE = "menstrual_cycle"
    STRESS = "stress"
    HYDRATION = "hydration"
    MINDFULNESS = "mindfulness"


class HealthPlatformConnection(BaseModel):
    platform: HealthPlatform
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: List[str] = []
    last_sync: Optional[datetime] = None
    sync_enabled: bool = True
    categories_enabled: List[DataCategory] = []


class UnifiedHealthData(BaseModel):
    """Unified health data model that normalizes data from all platforms"""
    user_id: str
    source_platform: HealthPlatform
    category: DataCategory
    timestamp: datetime
    value: float
    unit: str
    metadata: Dict[str, Any] = {}
    raw_data: Optional[Dict] = None


class HealthSummary(BaseModel):
    """Daily health summary aggregated from all sources"""
    date: str
    steps: int = 0
    active_minutes: int = 0
    calories_burned: int = 0
    distance_km: float = 0.0
    floors_climbed: int = 0
    heart_rate_avg: Optional[int] = None
    heart_rate_min: Optional[int] = None
    heart_rate_max: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    sleep_hours: float = 0.0
    sleep_quality_score: Optional[int] = None
    deep_sleep_hours: float = 0.0
    rem_sleep_hours: float = 0.0
    weight_kg: Optional[float] = None
    body_fat_percent: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    blood_glucose_mg_dl: Optional[float] = None
    oxygen_saturation: Optional[int] = None
    stress_score: Optional[int] = None
    hydration_ml: int = 0
    mindfulness_minutes: int = 0
    sources: List[str] = []


class ReminderSettings(BaseModel):
    appointment_day_before: bool = True
    appointment_3_hours: bool = True
    appointment_custom_minutes: List[int] = []
    medication_reminders: bool = True
    health_goal_reminders: bool = True
    hydration_reminders: bool = False
    hydration_interval_minutes: int = 60
    activity_reminders: bool = False
    activity_interval_minutes: int = 60
    sleep_reminder: bool = False
    sleep_reminder_time: str = "22:00"
    reminder_channels: List[str] = ["push", "email", "sms"]


# Platform-specific OAuth configurations (would be in .env in production)
PLATFORM_CONFIGS = {
    HealthPlatform.APPLE_HEALTH: {
        "name": "Apple Health",
        "auth_type": "on_device",  # Apple Health requires on-device SDK
        "supported_categories": [
            DataCategory.STEPS, DataCategory.HEART_RATE, DataCategory.SLEEP,
            DataCategory.ACTIVITY, DataCategory.WEIGHT, DataCategory.BLOOD_PRESSURE,
            DataCategory.BLOOD_GLUCOSE, DataCategory.OXYGEN_SATURATION,
            DataCategory.RESPIRATORY_RATE, DataCategory.MENSTRUAL_CYCLE,
            DataCategory.MINDFULNESS
        ],
        "setup_url": "infuse://health/connect/apple",
        "icon": "apple",
        "color": "#000000"
    },
    HealthPlatform.GOOGLE_FIT: {
        "name": "Google Fit",
        "auth_type": "oauth2",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/fitness.activity.read",
            "https://www.googleapis.com/auth/fitness.body.read",
            "https://www.googleapis.com/auth/fitness.heart_rate.read",
            "https://www.googleapis.com/auth/fitness.sleep.read",
            "https://www.googleapis.com/auth/fitness.blood_glucose.read",
            "https://www.googleapis.com/auth/fitness.blood_pressure.read",
            "https://www.googleapis.com/auth/fitness.oxygen_saturation.read"
        ],
        "supported_categories": [
            DataCategory.STEPS, DataCategory.HEART_RATE, DataCategory.SLEEP,
            DataCategory.ACTIVITY, DataCategory.WEIGHT, DataCategory.BLOOD_PRESSURE,
            DataCategory.BLOOD_GLUCOSE, DataCategory.OXYGEN_SATURATION
        ],
        "icon": "google",
        "color": "#4285F4"
    },
    HealthPlatform.FITBIT: {
        "name": "Fitbit",
        "auth_type": "oauth2",
        "auth_url": "https://www.fitbit.com/oauth2/authorize",
        "token_url": "https://api.fitbit.com/oauth2/token",
        "scopes": ["activity", "heartrate", "sleep", "weight", "nutrition", "profile"],
        "supported_categories": [
            DataCategory.STEPS, DataCategory.HEART_RATE, DataCategory.SLEEP,
            DataCategory.ACTIVITY, DataCategory.WEIGHT, DataCategory.NUTRITION,
            DataCategory.HYDRATION, DataCategory.STRESS
        ],
        "icon": "fitbit",
        "color": "#00B0B9"
    },
    HealthPlatform.SAMSUNG_HEALTH: {
        "name": "Samsung Health",
        "auth_type": "sdk",
        "setup_url": "infuse://health/connect/samsung",
        "supported_categories": [
            DataCategory.STEPS, DataCategory.HEART_RATE, DataCategory.SLEEP,
            DataCategory.ACTIVITY, DataCategory.WEIGHT, DataCategory.BLOOD_PRESSURE,
            DataCategory.BLOOD_GLUCOSE, DataCategory.OXYGEN_SATURATION, DataCategory.STRESS
        ],
        "icon": "samsung",
        "color": "#1428A0"
    },
    HealthPlatform.GARMIN_CONNECT: {
        "name": "Garmin Connect",
        "auth_type": "oauth1",  # Garmin uses OAuth 1.0a
        "request_token_url": "https://connectapi.garmin.com/oauth-service/oauth/request_token",
        "auth_url": "https://connect.garmin.com/oauthConfirm",
        "access_token_url": "https://connectapi.garmin.com/oauth-service/oauth/access_token",
        "supported_categories": [
            DataCategory.STEPS, DataCategory.HEART_RATE, DataCategory.SLEEP,
            DataCategory.ACTIVITY, DataCategory.WEIGHT, DataCategory.STRESS,
            DataCategory.RESPIRATORY_RATE, DataCategory.BODY_TEMPERATURE
        ],
        "icon": "garmin",
        "color": "#007CC3"
    }
}


@router.get("/platforms")
async def get_available_platforms():
    """Get all available health platforms with their capabilities"""
    platforms = []
    for platform, config in PLATFORM_CONFIGS.items():
        platforms.append({
            "id": platform.value,
            "name": config["name"],
            "auth_type": config["auth_type"],
            "supported_categories": [cat.value for cat in config["supported_categories"]],
            "icon": config["icon"],
            "color": config["color"],
            "setup_url": config.get("setup_url")
        })
    return {"platforms": platforms}


@router.post("/connect/{platform}")
async def connect_platform(
    platform: HealthPlatform,
    user_id: str,
    categories: List[DataCategory] = []
):
    """
    Initiate connection to a health platform.
    Returns OAuth URL for web-based auth or setup instructions for SDK-based auth.
    """
    db = await dependencies.get_database()
    config = PLATFORM_CONFIGS.get(platform)
    
    if not config:
        raise HTTPException(status_code=400, detail=f"Platform {platform} not supported")
    
    # Create pending connection record
    connection = {
        "id": f"conn_{str(uuid4())[:8]}",
        "user_id": user_id,
        "platform": platform.value,
        "status": "pending",
        "categories_requested": [cat.value for cat in categories] if categories else [cat.value for cat in config["supported_categories"]],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "auth_type": config["auth_type"]
    }
    
    await db.health_connections.insert_one(connection)
    connection.pop("_id", None)
    
    if config["auth_type"] == "oauth2":
        # Generate OAuth URL
        state = f"{user_id}:{connection['id']}"
        scopes = "+".join(config.get("scopes", []))
        redirect_uri = "https://infuse.net.in/health/callback"
        
        auth_url = (
            f"{config['auth_url']}?"
            f"client_id=PLATFORM_CLIENT_ID&"
            f"redirect_uri={redirect_uri}&"
            f"scope={scopes}&"
            f"state={state}&"
            f"response_type=code"
        )
        
        return {
            "connection_id": connection["id"],
            "auth_type": "oauth2",
            "auth_url": auth_url,
            "message": "Redirect user to auth_url to complete authorization"
        }
    
    elif config["auth_type"] == "on_device" or config["auth_type"] == "sdk":
        return {
            "connection_id": connection["id"],
            "auth_type": config["auth_type"],
            "setup_url": config.get("setup_url"),
            "message": f"Use the mobile app to connect to {config['name']}",
            "instructions": [
                f"1. Open the Infuse mobile app",
                f"2. Go to Settings > Health Connections",
                f"3. Tap 'Connect {config['name']}'",
                f"4. Follow the authorization prompts"
            ]
        }
    
    return {
        "connection_id": connection["id"],
        "auth_type": config["auth_type"],
        "message": "Connection initiated. Complete setup on your device."
    }


@router.post("/callback/{platform}")
async def oauth_callback(
    platform: HealthPlatform,
    code: str,
    state: str
):
    """
    Handle OAuth callback from health platforms.
    Exchanges authorization code for access tokens.
    """
    db = await dependencies.get_database()
    
    # Parse state to get user_id and connection_id
    try:
        user_id, connection_id = state.split(":")
    except:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # In production, exchange code for tokens using platform's token endpoint
    # For now, simulate successful token exchange
    
    # Update connection with tokens
    await db.health_connections.update_one(
        {"id": connection_id},
        {
            "$set": {
                "status": "connected",
                "access_token": f"mock_access_token_{platform.value}",
                "refresh_token": f"mock_refresh_token_{platform.value}",
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "connected_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "status": "connected",
        "platform": platform.value,
        "message": f"Successfully connected to {PLATFORM_CONFIGS[platform]['name']}"
    }


@router.delete("/disconnect/{platform}")
async def disconnect_platform(platform: HealthPlatform, user_id: str):
    """Disconnect a health platform and revoke access"""
    db = await dependencies.get_database()
    
    result = await db.health_connections.update_one(
        {"user_id": user_id, "platform": platform.value, "status": "connected"},
        {
            "$set": {
                "status": "disconnected",
                "disconnected_at": datetime.now(timezone.utc).isoformat(),
                "access_token": None,
                "refresh_token": None
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return {"status": "disconnected", "platform": platform.value}


@router.get("/connections/{user_id}")
async def get_user_connections(user_id: str):
    """Get all health platform connections for a user"""
    db = await dependencies.get_database()
    
    connections = await db.health_connections.find(
        {"user_id": user_id},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with platform info
    for conn in connections:
        platform = HealthPlatform(conn["platform"])
        config = PLATFORM_CONFIGS.get(platform, {})
        conn["platform_name"] = config.get("name", conn["platform"])
        conn["platform_icon"] = config.get("icon")
        conn["platform_color"] = config.get("color")
    
    return {"user_id": user_id, "connections": connections}


@router.post("/sync/{platform}")
async def sync_platform_data(
    platform: HealthPlatform,
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    categories: Optional[List[DataCategory]] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Trigger data sync from a health platform.
    In production, this would fetch real data from the platform's API.
    """
    db = await dependencies.get_database()
    
    # Verify connection exists and is active
    connection = await db.health_connections.find_one({
        "user_id": user_id,
        "platform": platform.value,
        "status": "connected"
    })
    
    if not connection:
        raise HTTPException(status_code=404, detail=f"No active connection to {platform.value}")
    
    # Determine date range
    end = datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc)
    start = datetime.fromisoformat(start_date) if start_date else end - timedelta(days=7)
    
    # Generate mock data based on platform capabilities
    config = PLATFORM_CONFIGS.get(platform)
    sync_categories = categories or [DataCategory(cat) for cat in connection.get("categories_requested", [])]
    
    synced_data = []
    current_date = start
    
    while current_date <= end:
        for category in sync_categories:
            if category not in config["supported_categories"]:
                continue
            
            # Generate mock data point
            data_point = _generate_mock_health_data(user_id, platform, category, current_date)
            if data_point:
                synced_data.append(data_point)
        
        current_date += timedelta(days=1)
    
    # Store synced data
    if synced_data:
        await db.health_data.insert_many([d.dict() for d in synced_data])
    
    # Update last sync time
    await db.health_connections.update_one(
        {"id": connection["id"]},
        {"$set": {"last_sync": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "status": "synced",
        "platform": platform.value,
        "records_synced": len(synced_data),
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "categories_synced": [cat.value for cat in sync_categories if cat in config["supported_categories"]]
    }


@router.post("/sync-all")
async def sync_all_platforms(user_id: str, background_tasks: BackgroundTasks = None):
    """Sync data from all connected platforms"""
    db = await dependencies.get_database()
    
    connections = await db.health_connections.find({
        "user_id": user_id,
        "status": "connected"
    }).to_list(100)
    
    results = []
    for conn in connections:
        try:
            platform = HealthPlatform(conn["platform"])
            result = await sync_platform_data(
                platform=platform,
                user_id=user_id,
                background_tasks=background_tasks
            )
            results.append({"platform": platform.value, "status": "success", **result})
        except Exception as e:
            results.append({"platform": conn["platform"], "status": "error", "error": str(e)})
    
    return {
        "user_id": user_id,
        "sync_results": results,
        "total_platforms": len(connections),
        "successful_syncs": len([r for r in results if r["status"] == "success"])
    }


@router.get("/data/{user_id}")
async def get_health_data(
    user_id: str,
    category: Optional[DataCategory] = None,
    platform: Optional[HealthPlatform] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=100, le=1000)
):
    """Get health data for a user with optional filters"""
    db = await dependencies.get_database()
    
    query = {"user_id": user_id}
    
    if category:
        query["category"] = category.value
    if platform:
        query["source_platform"] = platform.value
    
    if start_date or end_date:
        query["timestamp"] = {}
        if start_date:
            query["timestamp"]["$gte"] = start_date
        if end_date:
            query["timestamp"]["$lte"] = end_date
    
    data = await db.health_data.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {
        "user_id": user_id,
        "count": len(data),
        "data": data
    }


@router.get("/summary/{user_id}")
async def get_health_summary(
    user_id: str,
    date: Optional[str] = None
):
    """
    Get aggregated health summary for a specific date.
    Combines data from all connected platforms.
    """
    db = await dependencies.get_database()
    
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Aggregate data from all sources for the date
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "timestamp": {
                    "$gte": f"{target_date}T00:00:00",
                    "$lt": f"{target_date}T23:59:59"
                }
            }
        },
        {
            "$group": {
                "_id": "$category",
                "avg_value": {"$avg": "$value"},
                "max_value": {"$max": "$value"},
                "min_value": {"$min": "$value"},
                "total_value": {"$sum": "$value"},
                "count": {"$sum": 1},
                "sources": {"$addToSet": "$source_platform"}
            }
        }
    ]
    
    aggregated = await db.health_data.aggregate(pipeline).to_list(100)
    
    # Build summary from aggregated data
    summary = HealthSummary(date=target_date)
    sources = set()
    
    for item in aggregated:
        category = item["_id"]
        sources.update(item["sources"])
        
        if category == "steps":
            summary.steps = int(item["total_value"])
        elif category == "heart_rate":
            summary.heart_rate_avg = int(item["avg_value"])
            summary.heart_rate_min = int(item["min_value"])
            summary.heart_rate_max = int(item["max_value"])
        elif category == "sleep":
            summary.sleep_hours = round(item["total_value"], 1)
        elif category == "activity":
            summary.active_minutes = int(item["total_value"])
            summary.calories_burned = int(item["total_value"] * 8)  # Rough estimate
        elif category == "weight":
            summary.weight_kg = round(item["avg_value"], 1)
        elif category == "blood_pressure":
            # Would need separate systolic/diastolic in real implementation
            pass
        elif category == "blood_glucose":
            summary.blood_glucose_mg_dl = round(item["avg_value"], 1)
        elif category == "oxygen_saturation":
            summary.oxygen_saturation = int(item["avg_value"])
        elif category == "stress":
            summary.stress_score = int(item["avg_value"])
        elif category == "hydration":
            summary.hydration_ml = int(item["total_value"])
        elif category == "mindfulness":
            summary.mindfulness_minutes = int(item["total_value"])
    
    summary.sources = list(sources)
    
    return summary.dict()


@router.get("/summary/{user_id}/week")
async def get_weekly_summary(user_id: str):
    """Get health summary for the past 7 days"""
    summaries = []
    today = datetime.now(timezone.utc)
    
    for i in range(7):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        summary = await get_health_summary(user_id, date)
        summaries.append(summary)
    
    return {
        "user_id": user_id,
        "period": "7_days",
        "summaries": summaries
    }


@router.post("/reminders/settings")
async def update_reminder_settings(user_id: str, settings: ReminderSettings):
    """Update health reminder settings for a user"""
    db = await dependencies.get_database()
    
    await db.reminder_settings.update_one(
        {"user_id": user_id},
        {
            "$set": {
                **settings.dict(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"status": "updated", "settings": settings.dict()}


@router.get("/reminders/settings/{user_id}")
async def get_reminder_settings(user_id: str):
    """Get health reminder settings for a user"""
    db = await dependencies.get_database()
    
    settings = await db.reminder_settings.find_one({"user_id": user_id}, {"_id": 0})
    
    if not settings:
        # Return defaults
        settings = ReminderSettings().dict()
    
    return settings


def _generate_mock_health_data(
    user_id: str,
    platform: HealthPlatform,
    category: DataCategory,
    timestamp: datetime
) -> Optional[UnifiedHealthData]:
    """Generate mock health data for testing"""
    import random
    
    data_generators = {
        DataCategory.STEPS: lambda: (random.randint(3000, 15000), "steps"),
        DataCategory.HEART_RATE: lambda: (random.randint(60, 100), "bpm"),
        DataCategory.SLEEP: lambda: (round(random.uniform(5.5, 8.5), 1), "hours"),
        DataCategory.ACTIVITY: lambda: (random.randint(20, 90), "minutes"),
        DataCategory.WEIGHT: lambda: (round(random.uniform(60, 85), 1), "kg"),
        DataCategory.BLOOD_PRESSURE: lambda: (random.randint(110, 140), "mmHg"),
        DataCategory.BLOOD_GLUCOSE: lambda: (round(random.uniform(80, 140), 1), "mg/dL"),
        DataCategory.OXYGEN_SATURATION: lambda: (random.randint(95, 100), "%"),
        DataCategory.STRESS: lambda: (random.randint(20, 80), "score"),
        DataCategory.HYDRATION: lambda: (random.randint(1500, 3000), "ml"),
        DataCategory.MINDFULNESS: lambda: (random.randint(0, 30), "minutes"),
    }
    
    generator = data_generators.get(category)
    if not generator:
        return None
    
    value, unit = generator()
    
    return UnifiedHealthData(
        user_id=user_id,
        source_platform=platform,
        category=category,
        timestamp=timestamp,
        value=value,
        unit=unit,
        metadata={"generated": True}
    )
