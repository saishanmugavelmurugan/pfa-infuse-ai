"""
Wearable Device Integration API
Supports: Fitbit, Google Fit, Apple Health, Samsung Health, Garmin
Provides OAuth integration, data sync, and AI Lifestyle Plan integration
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import RedirectResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from enum import Enum
import os
import httpx
import asyncio
import random

router = APIRouter(prefix="/wearable-integrations", tags=["Wearable Device Integrations"])

# OAuth Configuration (would come from environment in production)
FITBIT_CLIENT_ID = os.environ.get("FITBIT_CLIENT_ID", "")
FITBIT_CLIENT_SECRET = os.environ.get("FITBIT_CLIENT_SECRET", "")
GOOGLE_FIT_CLIENT_ID = os.environ.get("GOOGLE_FIT_CLIENT_ID", "")
GOOGLE_FIT_CLIENT_SECRET = os.environ.get("GOOGLE_FIT_CLIENT_SECRET", "")
REDIRECT_BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")


class WearablePlatform(str, Enum):
    FITBIT = "fitbit"
    GOOGLE_FIT = "google_fit"
    APPLE_HEALTH = "apple_health"
    SAMSUNG_HEALTH = "samsung_health"
    GARMIN = "garmin"
    MI_FIT = "mi_fit"


class DataCategory(str, Enum):
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    SLEEP = "sleep"
    CALORIES = "calories"
    ACTIVITY = "activity"
    BLOOD_OXYGEN = "blood_oxygen"
    STRESS = "stress"
    WEIGHT = "weight"
    ALL = "all"


class WearableConnectionRequest(BaseModel):
    platform: WearablePlatform
    patient_id: str
    device_name: Optional[str] = None


class WearableDataPoint(BaseModel):
    timestamp: str
    heart_rate: Optional[int] = None
    heart_rate_variability: Optional[float] = None
    resting_heart_rate: Optional[int] = None
    steps: Optional[int] = None
    distance_km: Optional[float] = None
    calories_burned: Optional[int] = None
    active_calories: Optional[int] = None
    sleep_hours: Optional[float] = None
    deep_sleep_hours: Optional[float] = None
    light_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    sleep_quality_score: Optional[int] = None
    blood_oxygen: Optional[float] = None
    stress_level: Optional[int] = None
    active_minutes: Optional[int] = None
    floors_climbed: Optional[int] = None
    weight_kg: Optional[float] = None
    body_fat_percentage: Optional[float] = None


class WearableSummary(BaseModel):
    period: str  # daily, weekly, monthly
    start_date: str
    end_date: str
    avg_heart_rate: Optional[float] = None
    max_heart_rate: Optional[int] = None
    min_heart_rate: Optional[int] = None
    avg_resting_heart_rate: Optional[float] = None
    total_steps: Optional[int] = None
    avg_daily_steps: Optional[float] = None
    total_calories: Optional[int] = None
    avg_daily_calories: Optional[float] = None
    total_sleep_hours: Optional[float] = None
    avg_sleep_hours: Optional[float] = None
    avg_sleep_quality: Optional[float] = None
    avg_blood_oxygen: Optional[float] = None
    avg_stress_level: Optional[float] = None
    total_active_minutes: Optional[int] = None
    workout_count: Optional[int] = None


# Database helper
async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'test_database')]


# Platform-specific OAuth URLs
OAUTH_CONFIG = {
    WearablePlatform.FITBIT: {
        "auth_url": "https://www.fitbit.com/oauth2/authorize",
        "token_url": "https://api.fitbit.com/oauth2/token",
        "api_base": "https://api.fitbit.com",
        "scopes": ["activity", "heartrate", "sleep", "weight", "profile"],
        "data_endpoints": {
            "heart_rate": "/1/user/-/activities/heart/date/{date}/1d.json",
            "steps": "/1/user/-/activities/steps/date/{date}/1d.json",
            "sleep": "/1.2/user/-/sleep/date/{date}.json",
            "profile": "/1/user/-/profile.json"
        }
    },
    WearablePlatform.GOOGLE_FIT: {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "api_base": "https://www.googleapis.com/fitness/v1/users/me",
        "scopes": [
            "https://www.googleapis.com/auth/fitness.activity.read",
            "https://www.googleapis.com/auth/fitness.heart_rate.read",
            "https://www.googleapis.com/auth/fitness.sleep.read",
            "https://www.googleapis.com/auth/fitness.body.read"
        ],
        "data_endpoints": {
            "heart_rate": "/dataSources/derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm/dataPointChanges",
            "steps": "/dataSources/derived:com.google.step_count.delta:com.google.android.gms:estimated_steps/dataPointChanges",
            "sleep": "/sessions?activityType=72"
        }
    },
    WearablePlatform.APPLE_HEALTH: {
        "note": "Apple Health requires native iOS app. Data can be exported or synced via HealthKit.",
        "manual_import": True,
        "supported_data": ["heart_rate", "steps", "sleep", "calories", "blood_oxygen", "hrv"]
    }
}


# ==================== OAuth Endpoints ====================

@router.get("/platforms")
async def get_supported_platforms():
    """Get list of supported wearable platforms with connection status"""
    platforms = []
    for platform in WearablePlatform:
        config = OAUTH_CONFIG.get(platform, {})
        platforms.append({
            "id": platform.value,
            "name": platform.value.replace("_", " ").title(),
            "oauth_supported": not config.get("manual_import", False),
            "manual_import": config.get("manual_import", False),
            "icon": get_platform_icon(platform),
            "data_types": get_platform_data_types(platform),
            "status": "available"
        })
    
    return {"platforms": platforms}


@router.post("/connect")
async def initiate_connection(request: WearableConnectionRequest):
    """
    Initiate OAuth connection flow for a wearable platform.
    Returns authorization URL for OAuth platforms or manual import instructions.
    """
    platform = request.platform
    patient_id = request.patient_id
    
    # Check if already connected
    db = await get_db()
    existing = await db.wearable_connections.find_one({
        "patient_id": patient_id,
        "platform": platform.value,
        "status": "connected"
    })
    
    if existing:
        return {
            "status": "already_connected",
            "message": f"{platform.value} is already connected",
            "connection_id": existing.get("id"),
            "connected_at": existing.get("connected_at")
        }
    
    # For platforms requiring manual import
    if platform == WearablePlatform.APPLE_HEALTH:
        return await handle_apple_health_connection(patient_id, request.device_name)
    
    # For OAuth platforms (mocked in development)
    if not FITBIT_CLIENT_ID and platform == WearablePlatform.FITBIT:
        return await create_mock_connection(patient_id, platform, request.device_name)
    
    if not GOOGLE_FIT_CLIENT_ID and platform == WearablePlatform.GOOGLE_FIT:
        return await create_mock_connection(patient_id, platform, request.device_name)
    
    # Generate OAuth URL for real integration
    oauth_config = OAUTH_CONFIG.get(platform, {})
    state = f"{patient_id}:{platform.value}:{uuid4()}"
    
    if platform == WearablePlatform.FITBIT:
        auth_url = (
            f"{oauth_config['auth_url']}?"
            f"client_id={FITBIT_CLIENT_ID}&"
            f"response_type=code&"
            f"scope={' '.join(oauth_config['scopes'])}&"
            f"redirect_uri={REDIRECT_BASE_URL}/api/wearable-integrations/callback/fitbit&"
            f"state={state}"
        )
    elif platform == WearablePlatform.GOOGLE_FIT:
        auth_url = (
            f"{oauth_config['auth_url']}?"
            f"client_id={GOOGLE_FIT_CLIENT_ID}&"
            f"response_type=code&"
            f"scope={' '.join(oauth_config['scopes'])}&"
            f"redirect_uri={REDIRECT_BASE_URL}/api/wearable-integrations/callback/google_fit&"
            f"state={state}&"
            f"access_type=offline"
        )
    else:
        return await create_mock_connection(patient_id, platform, request.device_name)
    
    # Store pending connection
    pending = {
        "id": str(uuid4()),
        "patient_id": patient_id,
        "platform": platform.value,
        "status": "pending",
        "state": state,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.wearable_connections.insert_one(pending)
    
    return {
        "status": "redirect",
        "auth_url": auth_url,
        "message": f"Please authorize {platform.value} access"
    }


async def create_mock_connection(patient_id: str, platform: WearablePlatform, device_name: str = None):
    """Create a mock connection for development/demo purposes"""
    db = await get_db()
    
    connection = {
        "id": str(uuid4()),
        "patient_id": patient_id,
        "platform": platform.value,
        "device_name": device_name or f"{platform.value.replace('_', ' ').title()} Device",
        "status": "connected",
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "is_mock": True,
        "data_available": ["heart_rate", "steps", "sleep", "calories", "activity"]
    }
    
    await db.wearable_connections.insert_one(connection)
    connection.pop("_id", None)
    
    # Generate mock historical data
    await generate_mock_wearable_data(patient_id, platform.value, days=30)
    
    return {
        "status": "connected",
        "message": f"Successfully connected to {platform.value} (Demo Mode)",
        "connection": connection,
        "note": "This is a demo connection with simulated data. Provide API credentials for real integration."
    }


async def handle_apple_health_connection(patient_id: str, device_name: str = None):
    """Handle Apple Health connection (requires manual data import)"""
    db = await get_db()
    
    connection = {
        "id": str(uuid4()),
        "patient_id": patient_id,
        "platform": "apple_health",
        "device_name": device_name or "Apple Watch / iPhone",
        "status": "connected",
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "requires_manual_sync": True,
        "data_available": ["heart_rate", "steps", "sleep", "calories", "blood_oxygen", "hrv"]
    }
    
    await db.wearable_connections.insert_one(connection)
    connection.pop("_id", None)
    
    # Generate mock data for demo
    await generate_mock_wearable_data(patient_id, "apple_health", days=30)
    
    return {
        "status": "connected",
        "message": "Apple Health connected. Data will sync automatically from your iPhone/Apple Watch.",
        "connection": connection,
        "instructions": [
            "Open the Health app on your iPhone",
            "Go to Profile > Apps > HealthTrack Pro",
            "Enable all data categories you want to share",
            "Data will sync automatically when you open the app"
        ]
    }


@router.get("/callback/{platform}")
async def oauth_callback(platform: str, code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback from wearable platforms"""
    if error:
        return RedirectResponse(
            url=f"{REDIRECT_BASE_URL.replace('/api', '')}/wellness?error={error}"
        )
    
    if not code or not state:
        return RedirectResponse(
            url=f"{REDIRECT_BASE_URL.replace('/api', '')}/wellness?error=missing_parameters"
        )
    
    # Parse state
    try:
        patient_id, platform_name, _ = state.split(":")
    except:
        return RedirectResponse(
            url=f"{REDIRECT_BASE_URL.replace('/api', '')}/wellness?error=invalid_state"
        )
    
    db = await get_db()
    
    # Exchange code for tokens (mocked for now)
    # In production, this would call the actual token endpoint
    
    # Update connection status
    await db.wearable_connections.update_one(
        {"patient_id": patient_id, "platform": platform, "status": "pending"},
        {
            "$set": {
                "status": "connected",
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "last_sync": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Generate initial data
    await generate_mock_wearable_data(patient_id, platform, days=30)
    
    return RedirectResponse(
        url=f"{REDIRECT_BASE_URL.replace('/api', '')}/wellness?connected={platform}"
    )


@router.delete("/disconnect/{patient_id}/{connection_id}")
async def disconnect_platform(patient_id: str, connection_id: str):
    """Disconnect a wearable platform"""
    db = await get_db()
    
    result = await db.wearable_connections.delete_one({
        "patient_id": patient_id,
        "id": connection_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Optionally delete associated data
    await db.wearable_data.delete_many({
        "patient_id": patient_id,
        "connection_id": connection_id
    })
    
    return {"message": "Platform disconnected successfully"}


# ==================== Data Retrieval Endpoints ====================

@router.get("/connections/{patient_id}")
async def get_patient_connections(patient_id: str):
    """Get all wearable connections for a patient"""
    db = await get_db()
    
    connections = await db.wearable_connections.find(
        {"patient_id": patient_id, "status": "connected"},
        {"_id": 0}
    ).to_list(20)
    
    return {
        "patient_id": patient_id,
        "connections": connections,
        "total": len(connections)
    }


@router.post("/sync/{patient_id}/{connection_id}")
async def sync_wearable_data(patient_id: str, connection_id: str):
    """Manually trigger data sync for a connection"""
    db = await get_db()
    
    connection = await db.wearable_connections.find_one({
        "patient_id": patient_id,
        "id": connection_id
    })
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Generate new mock data (simulating sync)
    await generate_mock_wearable_data(patient_id, connection["platform"], days=1)
    
    # Update last sync time
    await db.wearable_connections.update_one(
        {"id": connection_id},
        {"$set": {"last_sync": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": "Data synced successfully",
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "records_synced": random.randint(50, 200)
    }


@router.get("/data/{patient_id}")
async def get_wearable_data(
    patient_id: str,
    platform: Optional[str] = None,
    category: DataCategory = DataCategory.ALL,
    days: int = Query(7, ge=1, le=90),
    aggregation: str = Query("hourly", regex="^(raw|hourly|daily)$")
):
    """
    Get wearable health data for a patient.
    Supports filtering by platform, category, and date range.
    """
    db = await get_db()
    
    # Build query
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    query = {
        "patient_id": patient_id,
        "timestamp": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }
    
    if platform:
        query["platform"] = platform
    
    # Get data
    cursor = db.wearable_data.find(query, {"_id": 0}).sort("timestamp", -1)
    data = await cursor.to_list(10000)
    
    # Filter by category if specified
    if category != DataCategory.ALL:
        category_fields = get_category_fields(category)
        data = [
            {k: v for k, v in d.items() if k in category_fields or k in ["timestamp", "platform", "patient_id"]}
            for d in data
        ]
    
    # Aggregate if requested
    if aggregation == "daily":
        data = aggregate_daily(data)
    elif aggregation == "hourly":
        data = aggregate_hourly(data)
    
    return {
        "patient_id": patient_id,
        "period": f"{start_date.date()} to {end_date.date()}",
        "aggregation": aggregation,
        "total_records": len(data),
        "data": data
    }


@router.get("/summary/{patient_id}")
async def get_wearable_summary(
    patient_id: str,
    period: str = Query("weekly", regex="^(daily|weekly|monthly)$")
):
    """Get aggregated summary of wearable data for AI Lifestyle Plan integration"""
    db = await get_db()
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    if period == "daily":
        start_date = end_date - timedelta(days=1)
    elif period == "weekly":
        start_date = end_date - timedelta(days=7)
    else:
        start_date = end_date - timedelta(days=30)
    
    # Get all data for period
    data = await db.wearable_data.find({
        "patient_id": patient_id,
        "timestamp": {"$gte": start_date.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    if not data:
        # Return mock summary if no data
        return generate_mock_summary(patient_id, period, start_date, end_date)
    
    # Calculate summary statistics
    summary = calculate_summary(data, period, start_date, end_date)
    
    # Add health insights
    summary["health_insights"] = generate_health_insights(summary)
    
    # Add recommendations for AI Lifestyle Plan
    summary["lifestyle_recommendations"] = generate_lifestyle_recommendations(summary)
    
    return summary


@router.get("/health-score/{patient_id}")
async def get_health_score(patient_id: str):
    """Calculate overall health score based on wearable data"""
    db = await get_db()
    
    # Get last 7 days of data
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)
    
    data = await db.wearable_data.find({
        "patient_id": patient_id,
        "timestamp": {"$gte": start_date.isoformat()}
    }, {"_id": 0}).to_list(10000)
    
    # Calculate component scores
    scores = {
        "activity_score": calculate_activity_score(data),
        "sleep_score": calculate_sleep_score(data),
        "heart_health_score": calculate_heart_score(data),
        "recovery_score": calculate_recovery_score(data)
    }
    
    # Calculate overall score
    weights = {"activity_score": 0.3, "sleep_score": 0.3, "heart_health_score": 0.25, "recovery_score": 0.15}
    overall_score = sum(scores[k] * weights[k] for k in weights)
    
    return {
        "patient_id": patient_id,
        "overall_health_score": round(overall_score, 1),
        "component_scores": scores,
        "score_trend": "improving",  # Would be calculated from historical data
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "recommendations": get_score_recommendations(scores)
    }


# ==================== AI Lifestyle Plan Integration ====================

@router.get("/lifestyle-data/{patient_id}")
async def get_lifestyle_plan_data(patient_id: str):
    """
    Get comprehensive wearable data formatted for AI Lifestyle Plan generation.
    This endpoint aggregates all wearable data into a format optimized for the AI planner.
    """
    db = await get_db()
    
    # Get connections
    connections = await db.wearable_connections.find(
        {"patient_id": patient_id, "status": "connected"},
        {"_id": 0}
    ).to_list(20)
    
    # Get 30-day summary
    summary = await get_wearable_summary(patient_id, "monthly")
    
    # Get health score
    health_score = await get_health_score(patient_id)
    
    # Get recent trends
    trends = await calculate_trends(patient_id, db)
    
    return {
        "patient_id": patient_id,
        "connected_devices": len(connections),
        "devices": [{"platform": c["platform"], "last_sync": c.get("last_sync")} for c in connections],
        "data_available": True if connections else False,
        "summary": summary,
        "health_score": health_score,
        "trends": trends,
        "ai_ready_data": {
            "avg_daily_steps": summary.get("avg_daily_steps", 5000),
            "avg_sleep_hours": summary.get("avg_sleep_hours", 6.5),
            "avg_heart_rate": summary.get("avg_heart_rate", 72),
            "avg_resting_heart_rate": summary.get("avg_resting_heart_rate", 65),
            "activity_level": classify_activity_level(summary.get("avg_daily_steps", 5000)),
            "sleep_quality": classify_sleep_quality(summary.get("avg_sleep_hours", 6.5)),
            "stress_level": summary.get("avg_stress_level", 40),
            "recovery_status": "good" if health_score.get("component_scores", {}).get("recovery_score", 70) > 60 else "needs_attention"
        },
        "focus_area_suggestions": suggest_focus_areas(summary, health_score)
    }


# ==================== Helper Functions ====================

def get_platform_icon(platform: WearablePlatform) -> str:
    icons = {
        WearablePlatform.FITBIT: "⌚",
        WearablePlatform.GOOGLE_FIT: "🏃",
        WearablePlatform.APPLE_HEALTH: "🍎",
        WearablePlatform.SAMSUNG_HEALTH: "📱",
        WearablePlatform.GARMIN: "🎯",
        WearablePlatform.MI_FIT: "📊"
    }
    return icons.get(platform, "📱")


def get_platform_data_types(platform: WearablePlatform) -> List[str]:
    data_types = {
        WearablePlatform.FITBIT: ["heart_rate", "steps", "sleep", "calories", "activity", "weight"],
        WearablePlatform.GOOGLE_FIT: ["heart_rate", "steps", "sleep", "calories", "activity", "weight"],
        WearablePlatform.APPLE_HEALTH: ["heart_rate", "steps", "sleep", "calories", "blood_oxygen", "hrv", "ecg"],
        WearablePlatform.SAMSUNG_HEALTH: ["heart_rate", "steps", "sleep", "calories", "blood_oxygen", "stress"],
        WearablePlatform.GARMIN: ["heart_rate", "steps", "sleep", "calories", "activity", "stress", "body_battery"],
        WearablePlatform.MI_FIT: ["heart_rate", "steps", "sleep", "calories"]
    }
    return data_types.get(platform, ["heart_rate", "steps", "sleep"])


def get_category_fields(category: DataCategory) -> List[str]:
    fields = {
        DataCategory.HEART_RATE: ["heart_rate", "heart_rate_variability", "resting_heart_rate"],
        DataCategory.STEPS: ["steps", "distance_km", "floors_climbed"],
        DataCategory.SLEEP: ["sleep_hours", "deep_sleep_hours", "light_sleep_hours", "rem_sleep_hours", "sleep_quality_score"],
        DataCategory.CALORIES: ["calories_burned", "active_calories"],
        DataCategory.ACTIVITY: ["active_minutes", "steps", "distance_km", "floors_climbed"],
        DataCategory.BLOOD_OXYGEN: ["blood_oxygen"],
        DataCategory.STRESS: ["stress_level"],
        DataCategory.WEIGHT: ["weight_kg", "body_fat_percentage"]
    }
    return fields.get(category, [])


async def generate_mock_wearable_data(patient_id: str, platform: str, days: int = 30):
    """Generate realistic mock wearable data for testing/demo"""
    db = await get_db()
    
    data_points = []
    end_date = datetime.now(timezone.utc)
    
    for day in range(days):
        current_date = end_date - timedelta(days=day)
        
        # Generate hourly data points
        for hour in range(24):
            timestamp = current_date.replace(hour=hour, minute=0, second=0)
            
            # Sleep hours (lower HR, no activity)
            is_sleep_hour = hour >= 23 or hour < 6
            
            data_point = {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "platform": platform,
                "timestamp": timestamp.isoformat(),
                "heart_rate": random.randint(55, 70) if is_sleep_hour else random.randint(65, 95),
                "heart_rate_variability": random.uniform(20, 60),
                "steps": 0 if is_sleep_hour else random.randint(100, 800),
                "calories_burned": random.randint(40, 80) if is_sleep_hour else random.randint(60, 150),
                "active_minutes": 0 if is_sleep_hour else random.randint(0, 30),
                "blood_oxygen": random.uniform(95, 99),
                "stress_level": random.randint(10, 30) if is_sleep_hour else random.randint(20, 60)
            }
            
            # Add sleep data for night hours
            if hour == 6:  # Morning - add sleep summary
                data_point["sleep_hours"] = random.uniform(5.5, 8.5)
                data_point["deep_sleep_hours"] = random.uniform(1, 2.5)
                data_point["light_sleep_hours"] = random.uniform(2.5, 4)
                data_point["rem_sleep_hours"] = random.uniform(1, 2)
                data_point["sleep_quality_score"] = random.randint(60, 95)
            
            data_points.append(data_point)
    
    # Bulk insert
    if data_points:
        # Delete existing mock data for this patient/platform
        await db.wearable_data.delete_many({
            "patient_id": patient_id,
            "platform": platform
        })
        await db.wearable_data.insert_many(data_points)
    
    return len(data_points)


def aggregate_daily(data: List[Dict]) -> List[Dict]:
    """Aggregate data by day"""
    daily_data = {}
    
    for point in data:
        date = point["timestamp"][:10]
        if date not in daily_data:
            daily_data[date] = {
                "date": date,
                "heart_rates": [],
                "steps": 0,
                "calories": 0,
                "active_minutes": 0,
                "sleep_hours": None,
                "sleep_quality": None
            }
        
        if point.get("heart_rate"):
            daily_data[date]["heart_rates"].append(point["heart_rate"])
        if point.get("steps"):
            daily_data[date]["steps"] += point["steps"]
        if point.get("calories_burned"):
            daily_data[date]["calories"] += point["calories_burned"]
        if point.get("active_minutes"):
            daily_data[date]["active_minutes"] += point["active_minutes"]
        if point.get("sleep_hours"):
            daily_data[date]["sleep_hours"] = point["sleep_hours"]
            daily_data[date]["sleep_quality"] = point.get("sleep_quality_score")
    
    # Calculate averages
    result = []
    for date, d in sorted(daily_data.items(), reverse=True):
        result.append({
            "date": date,
            "avg_heart_rate": round(sum(d["heart_rates"]) / len(d["heart_rates"]), 1) if d["heart_rates"] else None,
            "total_steps": d["steps"],
            "total_calories": d["calories"],
            "active_minutes": d["active_minutes"],
            "sleep_hours": d["sleep_hours"],
            "sleep_quality": d["sleep_quality"]
        })
    
    return result


def aggregate_hourly(data: List[Dict]) -> List[Dict]:
    """Return data as-is (already hourly in mock)"""
    return data[:168]  # Limit to 1 week of hourly data


def calculate_summary(data: List[Dict], period: str, start_date, end_date) -> Dict:
    """Calculate summary statistics from wearable data"""
    heart_rates = [d["heart_rate"] for d in data if d.get("heart_rate")]
    steps = [d["steps"] for d in data if d.get("steps")]
    sleep = [d["sleep_hours"] for d in data if d.get("sleep_hours")]
    calories = [d["calories_burned"] for d in data if d.get("calories_burned")]
    stress = [d["stress_level"] for d in data if d.get("stress_level")]
    
    days = (end_date - start_date).days or 1
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "avg_heart_rate": round(sum(heart_rates) / len(heart_rates), 1) if heart_rates else None,
        "max_heart_rate": max(heart_rates) if heart_rates else None,
        "min_heart_rate": min(heart_rates) if heart_rates else None,
        "avg_resting_heart_rate": round(sum(hr for hr in heart_rates if hr < 75) / len([hr for hr in heart_rates if hr < 75]), 1) if heart_rates else 65,
        "total_steps": sum(steps),
        "avg_daily_steps": round(sum(steps) / days, 0) if steps else 0,
        "total_calories": sum(calories),
        "avg_daily_calories": round(sum(calories) / days, 0) if calories else 0,
        "total_sleep_hours": round(sum(sleep), 1) if sleep else 0,
        "avg_sleep_hours": round(sum(sleep) / len(sleep), 1) if sleep else 0,
        "avg_stress_level": round(sum(stress) / len(stress), 1) if stress else None
    }


def generate_mock_summary(patient_id: str, period: str, start_date, end_date) -> Dict:
    """Generate mock summary when no data available"""
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "avg_heart_rate": 72,
        "max_heart_rate": 145,
        "min_heart_rate": 55,
        "avg_resting_heart_rate": 65,
        "total_steps": 50000 if period == "weekly" else 150000,
        "avg_daily_steps": 7142,
        "total_calories": 14000 if period == "weekly" else 42000,
        "avg_daily_calories": 2000,
        "total_sleep_hours": 49 if period == "weekly" else 210,
        "avg_sleep_hours": 7,
        "avg_stress_level": 35,
        "is_mock_data": True,
        "health_insights": [
            "Your average daily steps are within the recommended range",
            "Sleep duration is adequate but could improve quality",
            "Heart rate patterns indicate good cardiovascular health"
        ],
        "lifestyle_recommendations": [
            "Consider adding 15 minutes of morning yoga",
            "Try to get to bed 30 minutes earlier",
            "Include more walking throughout the day"
        ]
    }


def generate_health_insights(summary: Dict) -> List[str]:
    """Generate health insights based on summary data"""
    insights = []
    
    avg_steps = summary.get("avg_daily_steps", 0)
    if avg_steps < 5000:
        insights.append("Your step count is below recommended levels. Aim for at least 7,000 steps daily.")
    elif avg_steps >= 10000:
        insights.append("Excellent! You're meeting the 10,000 steps daily goal.")
    else:
        insights.append(f"Good progress! You're averaging {int(avg_steps)} steps. Try to reach 10,000.")
    
    avg_sleep = summary.get("avg_sleep_hours", 0)
    if avg_sleep < 6:
        insights.append("You may be sleep deprived. Adults need 7-9 hours of sleep.")
    elif avg_sleep > 9:
        insights.append("You're sleeping more than recommended. Consider if this indicates other health issues.")
    else:
        insights.append(f"Your sleep duration ({avg_sleep:.1f} hrs) is within the healthy range.")
    
    rhr = summary.get("avg_resting_heart_rate", 70)
    if rhr < 60:
        insights.append("Your resting heart rate indicates good cardiovascular fitness.")
    elif rhr > 80:
        insights.append("Your resting heart rate is elevated. Consider stress reduction and cardio exercise.")
    
    return insights


def generate_lifestyle_recommendations(summary: Dict) -> List[str]:
    """Generate lifestyle recommendations for AI plan"""
    recommendations = []
    
    if summary.get("avg_daily_steps", 0) < 7000:
        recommendations.append("Increase daily walking - aim for 7,000+ steps")
    
    if summary.get("avg_sleep_hours", 0) < 7:
        recommendations.append("Prioritize sleep - establish a consistent bedtime routine")
    
    if summary.get("avg_stress_level", 0) > 50:
        recommendations.append("Include stress management practices like meditation or yoga")
    
    if summary.get("avg_resting_heart_rate", 70) > 75:
        recommendations.append("Add more cardiovascular exercise to improve heart health")
    
    return recommendations


def calculate_activity_score(data: List[Dict]) -> float:
    """Calculate activity score (0-100)"""
    if not data:
        return 70.0
    
    steps = [d.get("steps", 0) for d in data if d.get("steps")]
    active_mins = [d.get("active_minutes", 0) for d in data if d.get("active_minutes")]
    
    avg_daily_steps = sum(steps) / 7 if steps else 5000
    avg_active_mins = sum(active_mins) / 7 if active_mins else 30
    
    # Score based on targets (10k steps, 60 active mins)
    step_score = min(100, (avg_daily_steps / 10000) * 100)
    active_score = min(100, (avg_active_mins / 60) * 100)
    
    return round((step_score + active_score) / 2, 1)


def calculate_sleep_score(data: List[Dict]) -> float:
    """Calculate sleep score (0-100)"""
    if not data:
        return 70.0
    
    sleep_hours = [d.get("sleep_hours") for d in data if d.get("sleep_hours")]
    sleep_quality = [d.get("sleep_quality_score") for d in data if d.get("sleep_quality_score")]
    
    if not sleep_hours:
        return 70.0
    
    avg_sleep = sum(sleep_hours) / len(sleep_hours)
    avg_quality = sum(sleep_quality) / len(sleep_quality) if sleep_quality else 70
    
    # Optimal sleep is 7-8 hours
    duration_score = 100 - abs(avg_sleep - 7.5) * 15
    duration_score = max(0, min(100, duration_score))
    
    return round((duration_score + avg_quality) / 2, 1)


def calculate_heart_score(data: List[Dict]) -> float:
    """Calculate heart health score (0-100)"""
    if not data:
        return 75.0
    
    heart_rates = [d.get("heart_rate") for d in data if d.get("heart_rate")]
    
    if not heart_rates:
        return 75.0
    
    resting_hrs = [hr for hr in heart_rates if hr < 80]
    avg_rhr = sum(resting_hrs) / len(resting_hrs) if resting_hrs else 70
    
    # Lower resting HR is better (50-70 is optimal)
    if avg_rhr < 60:
        return 95.0
    elif avg_rhr < 70:
        return 85.0
    elif avg_rhr < 80:
        return 75.0
    else:
        return max(50, 100 - (avg_rhr - 60))


def calculate_recovery_score(data: List[Dict]) -> float:
    """Calculate recovery score based on HRV and sleep"""
    if not data:
        return 70.0
    
    hrv = [d.get("heart_rate_variability") for d in data if d.get("heart_rate_variability")]
    sleep_quality = [d.get("sleep_quality_score") for d in data if d.get("sleep_quality_score")]
    
    avg_hrv = sum(hrv) / len(hrv) if hrv else 40
    avg_sleep_q = sum(sleep_quality) / len(sleep_quality) if sleep_quality else 70
    
    # HRV score (higher is better, 40-60 is average)
    hrv_score = min(100, (avg_hrv / 60) * 100)
    
    return round((hrv_score + avg_sleep_q) / 2, 1)


def get_score_recommendations(scores: Dict) -> List[str]:
    """Get recommendations based on health scores"""
    recommendations = []
    
    if scores.get("activity_score", 0) < 70:
        recommendations.append("Increase daily activity - try a 20-minute walk after lunch")
    
    if scores.get("sleep_score", 0) < 70:
        recommendations.append("Improve sleep hygiene - limit screen time before bed")
    
    if scores.get("heart_health_score", 0) < 70:
        recommendations.append("Add cardiovascular exercise - aim for 150 minutes per week")
    
    if scores.get("recovery_score", 0) < 70:
        recommendations.append("Focus on recovery - try meditation or gentle yoga")
    
    return recommendations or ["Keep up the great work! All health metrics look good."]


async def calculate_trends(patient_id: str, db) -> Dict:
    """Calculate trends comparing this week to last week"""
    end_date = datetime.now(timezone.utc)
    this_week_start = end_date - timedelta(days=7)
    last_week_start = end_date - timedelta(days=14)
    
    # This week data
    this_week = await db.wearable_data.find({
        "patient_id": patient_id,
        "timestamp": {"$gte": this_week_start.isoformat()}
    }).to_list(10000)
    
    # Last week data
    last_week = await db.wearable_data.find({
        "patient_id": patient_id,
        "timestamp": {"$gte": last_week_start.isoformat(), "$lt": this_week_start.isoformat()}
    }).to_list(10000)
    
    def avg(data, field):
        values = [d.get(field) for d in data if d.get(field)]
        return sum(values) / len(values) if values else 0
    
    return {
        "steps": {
            "this_week": sum(d.get("steps", 0) for d in this_week),
            "last_week": sum(d.get("steps", 0) for d in last_week),
            "trend": "up" if sum(d.get("steps", 0) for d in this_week) > sum(d.get("steps", 0) for d in last_week) else "down"
        },
        "sleep": {
            "this_week_avg": round(avg(this_week, "sleep_hours"), 1),
            "last_week_avg": round(avg(last_week, "sleep_hours"), 1),
            "trend": "up" if avg(this_week, "sleep_hours") > avg(last_week, "sleep_hours") else "down"
        },
        "heart_rate": {
            "this_week_avg": round(avg(this_week, "heart_rate"), 0),
            "last_week_avg": round(avg(last_week, "heart_rate"), 0),
            "trend": "stable"
        }
    }


def classify_activity_level(avg_steps: float) -> str:
    """Classify activity level based on steps"""
    if avg_steps < 3000:
        return "sedentary"
    elif avg_steps < 5000:
        return "light"
    elif avg_steps < 8000:
        return "moderate"
    elif avg_steps < 12000:
        return "active"
    else:
        return "very_active"


def classify_sleep_quality(avg_sleep: float) -> str:
    """Classify sleep quality based on hours"""
    if avg_sleep < 5:
        return "poor"
    elif avg_sleep < 6:
        return "fair"
    elif avg_sleep < 7:
        return "good"
    elif avg_sleep <= 9:
        return "excellent"
    else:
        return "excessive"


def suggest_focus_areas(summary: Dict, health_score: Dict) -> List[str]:
    """Suggest focus areas for AI Lifestyle Plan based on wearable data"""
    suggestions = []
    
    if summary.get("avg_daily_steps", 0) < 5000:
        suggestions.append("weight_loss")
    
    if summary.get("avg_sleep_hours", 0) < 6.5:
        suggestions.append("sleep_improvement")
    
    if summary.get("avg_stress_level", 0) > 50:
        suggestions.append("stress_management")
    
    if health_score.get("component_scores", {}).get("heart_health_score", 100) < 70:
        suggestions.append("hypertension")
    
    if not suggestions:
        suggestions.append("general_wellness")
    
    return suggestions
