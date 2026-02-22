from fastapi import APIRouter, HTTPException, status, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import random

router = APIRouter(prefix="/healthtrack/wearables", tags=["HealthTrack - Wearable Devices"])

# Database dependency - defined locally to avoid circular imports
async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'test_database')]

class WearableDevice(BaseModel):
    device_type: str  # apple_watch, fitbit, garmin, samsung_health
    device_name: str
    device_id: Optional[str] = None
    is_connected: bool = True

class WearableDataPoint(BaseModel):
    heart_rate: Optional[int] = None
    steps: Optional[int] = None
    calories_burned: Optional[int] = None
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[str] = None
    blood_oxygen: Optional[float] = None
    stress_level: Optional[int] = None
    active_minutes: Optional[int] = None

@router.get("/devices/{patient_id}")
async def get_patient_devices(patient_id: str):
    """Get all connected wearable devices for a patient"""
    db = await get_db()
    devices = await db.healthtrack_wearable_devices.find(
        {"patient_id": patient_id},
        {"_id": 0}
    ).to_list(20)
    
    return {"devices": devices, "total": len(devices)}

@router.post("/devices/{patient_id}/connect")
async def connect_wearable_device(patient_id: str, device: WearableDevice):
    """Connect a new wearable device for a patient"""
    db = await get_db()
    
    # Check if device already connected
    existing = await db.healthtrack_wearable_devices.find_one({
        "patient_id": patient_id,
        "device_type": device.device_type
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Device type already connected")
    
    device_record = {
        "id": str(uuid4()),
        "patient_id": patient_id,
        "device_type": device.device_type,
        "device_name": device.device_name,
        "device_id": device.device_id or str(uuid4()),
        "is_connected": True,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_sync": datetime.now(timezone.utc).isoformat()
    }
    
    await db.healthtrack_wearable_devices.insert_one(device_record)
    device_record.pop("_id", None)
    
    return device_record

@router.delete("/devices/{patient_id}/{device_id}")
async def disconnect_wearable_device(patient_id: str, device_id: str):
    """Disconnect a wearable device"""
    db = await get_db()
    result = await db.healthtrack_wearable_devices.delete_one({
        "patient_id": patient_id,
        "id": device_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {"message": "Device disconnected successfully"}

@router.get("/data/{patient_id}")
async def get_wearable_data(
    patient_id: str,
    device_type: Optional[str] = None,
    days: int = Query(7, ge=1, le=90)
):
    """Get wearable health data for a patient"""
    db = await get_db()
    query = {"patient_id": patient_id}
    if device_type:
        query["device_type"] = device_type
    
    # Get data for specified period
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query["recorded_at"] = {"$gte": cutoff.isoformat()}
    
    data = await db.healthtrack_wearable_data.find(
        query,
        {"_id": 0}
    ).sort("recorded_at", -1).to_list(1000)
    
    # Calculate summary stats
    heart_rates = [d["heart_rate"] for d in data if d.get("heart_rate")]
    steps = [d["steps"] for d in data if d.get("steps")]
    sleep_hours = [d["sleep_hours"] for d in data if d.get("sleep_hours")]
    calories = [d["calories_burned"] for d in data if d.get("calories_burned")]
    
    summary = {
        "period_days": days,
        "data_points": len(data),
        "heart_rate": {
            "average": round(sum(heart_rates) / len(heart_rates), 1) if heart_rates else None,
            "min": min(heart_rates) if heart_rates else None,
            "max": max(heart_rates) if heart_rates else None
        },
        "steps": {
            "total": sum(steps),
            "daily_average": round(sum(steps) / days) if steps else 0
        },
        "sleep": {
            "average_hours": round(sum(sleep_hours) / len(sleep_hours), 1) if sleep_hours else None
        },
        "calories": {
            "total": sum(calories),
            "daily_average": round(sum(calories) / days) if calories else 0
        }
    }
    
    return {
        "patient_id": patient_id,
        "summary": summary,
        "data": data[:100]  # Return latest 100 data points
    }

@router.post("/data/{patient_id}/sync")
async def sync_wearable_data(patient_id: str, device_type: str):
    """Simulate syncing data from wearable device (generates demo data)"""
    db = await get_db()
    
    # Check if device is connected
    device = await db.healthtrack_wearable_devices.find_one({
        "patient_id": patient_id,
        "device_type": device_type
    })
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not connected")
    
    # Generate demo data for last 7 days (hourly)
    data_points = []
    now = datetime.now(timezone.utc)
    
    for day in range(7):
        for hour in range(24):
            timestamp = now - timedelta(days=day, hours=hour)
            
            # Generate realistic health data
            is_sleeping = 0 <= hour <= 6 or hour >= 23
            is_active = 8 <= hour <= 20
            
            data_point = {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "device_type": device_type,
                "recorded_at": timestamp.isoformat(),
                "heart_rate": random.randint(55, 65) if is_sleeping else random.randint(65, 95) if is_active else random.randint(60, 75),
                "steps": 0 if is_sleeping else random.randint(100, 800) if is_active else random.randint(0, 200),
                "calories_burned": random.randint(50, 80) if is_sleeping else random.randint(80, 200) if is_active else random.randint(60, 100),
                "blood_oxygen": round(random.uniform(95, 99), 1),
                "stress_level": random.randint(10, 30) if is_sleeping else random.randint(20, 60) if is_active else random.randint(15, 40),
                "active_minutes": 0 if is_sleeping else random.randint(10, 45) if is_active else random.randint(0, 15)
            }
            
            # Add sleep data only for night hours
            if is_sleeping and hour == 6:  # End of sleep cycle
                data_point["sleep_hours"] = round(random.uniform(6, 8.5), 1)
                data_point["sleep_quality"] = random.choice(["good", "fair", "excellent"])
            
            data_points.append(data_point)
    
    # Insert data
    if data_points:
        await db.healthtrack_wearable_data.insert_many(data_points)
    
    # Update last sync time
    await db.healthtrack_wearable_devices.update_one(
        {"id": device["id"]},
        {"$set": {"last_sync": now.isoformat()}}
    )
    
    return {
        "message": "Data synced successfully",
        "data_points_added": len(data_points),
        "last_sync": now.isoformat()
    }

@router.get("/trends/{patient_id}")
async def get_health_trends(
    patient_id: str,
    metric: str = Query("heart_rate", enum=["heart_rate", "steps", "sleep", "calories"]),
    days: int = Query(30, ge=7, le=90)
):
    """Get health metric trends over time"""
    db = await get_db()
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    data = await db.healthtrack_wearable_data.find(
        {
            "patient_id": patient_id,
            "recorded_at": {"$gte": cutoff.isoformat()}
        },
        {"_id": 0}
    ).sort("recorded_at", 1).to_list(5000)
    
    # Group by day
    daily_data = {}
    for point in data:
        date = point["recorded_at"][:10]  # YYYY-MM-DD
        if date not in daily_data:
            daily_data[date] = []
        daily_data[date].append(point)
    
    # Calculate daily averages
    trends = []
    for date, points in sorted(daily_data.items()):
        if metric == "heart_rate":
            values = [p["heart_rate"] for p in points if p.get("heart_rate")]
            avg = sum(values) / len(values) if values else 0
        elif metric == "steps":
            values = [p["steps"] for p in points if p.get("steps")]
            avg = sum(values)
        elif metric == "sleep":
            values = [p["sleep_hours"] for p in points if p.get("sleep_hours")]
            avg = sum(values) / len(values) if values else 0
        elif metric == "calories":
            values = [p["calories_burned"] for p in points if p.get("calories_burned")]
            avg = sum(values)
        
        trends.append({
            "date": date,
            "value": round(avg, 1)
        })
    
    return {
        "patient_id": patient_id,
        "metric": metric,
        "period_days": days,
        "trends": trends
    }
