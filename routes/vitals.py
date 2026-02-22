"""Vitals Recording API for HealthTrack Pro
Records and tracks patient vital signs including blood pressure, heart rate, blood sugar, temperature, etc.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os

router = APIRouter(prefix="/vitals", tags=["HealthTrack - Vitals"])

# Database dependency
async def get_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    return client[os.environ.get('DB_NAME', 'test_database')]

# Models
class VitalsCreate(BaseModel):
    patient_id: str
    recorded_by: Optional[str] = None  # Doctor/nurse ID
    blood_pressure_systolic: Optional[int] = Field(None, ge=60, le=250, description="Systolic BP in mmHg")
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=150, description="Diastolic BP in mmHg")
    heart_rate: Optional[int] = Field(None, ge=30, le=220, description="Heart rate in BPM")
    temperature: Optional[float] = Field(None, ge=95.0, le=108.0, description="Temperature in Fahrenheit")
    blood_sugar: Optional[int] = Field(None, ge=20, le=600, description="Blood sugar in mg/dL")
    oxygen_saturation: Optional[int] = Field(None, ge=50, le=100, description="SpO2 percentage")
    respiratory_rate: Optional[int] = Field(None, ge=8, le=40, description="Breaths per minute")
    weight: Optional[float] = Field(None, ge=1, le=500, description="Weight in kg")
    height: Optional[float] = Field(None, ge=30, le=250, description="Height in cm")
    notes: Optional[str] = None
    source: str = Field(default="manual", description="manual, wearable, device")

class VitalsResponse(BaseModel):
    id: str
    patient_id: str
    recorded_by: Optional[str]
    blood_pressure_systolic: Optional[int]
    blood_pressure_diastolic: Optional[int]
    heart_rate: Optional[int]
    temperature: Optional[float]
    blood_sugar: Optional[int]
    oxygen_saturation: Optional[int]
    respiratory_rate: Optional[int]
    weight: Optional[float]
    height: Optional[float]
    bmi: Optional[float]
    notes: Optional[str]
    source: str
    alerts: List[str]
    recorded_at: str

def calculate_bmi(weight: float, height: float) -> Optional[float]:
    """Calculate BMI from weight (kg) and height (cm)"""
    if weight and height and height > 0:
        height_m = height / 100
        return round(weight / (height_m ** 2), 1)
    return None

def check_vital_alerts(vitals: dict) -> List[str]:
    """Check for any concerning vital values"""
    alerts = []
    
    # Blood pressure alerts
    sys = vitals.get('blood_pressure_systolic')
    dia = vitals.get('blood_pressure_diastolic')
    if sys:
        if sys >= 180:
            alerts.append("🚨 CRITICAL: Hypertensive crisis (Systolic >= 180)")
        elif sys >= 140:
            alerts.append("⚠️ HIGH: Hypertension Stage 2 (Systolic >= 140)")
        elif sys <= 90:
            alerts.append("⚠️ LOW: Hypotension (Systolic <= 90)")
    if dia:
        if dia >= 120:
            alerts.append("🚨 CRITICAL: Hypertensive crisis (Diastolic >= 120)")
        elif dia >= 90:
            alerts.append("⚠️ HIGH: Hypertension Stage 2 (Diastolic >= 90)")
    
    # Heart rate alerts
    hr = vitals.get('heart_rate')
    if hr:
        if hr > 100:
            alerts.append("⚠️ Tachycardia: Heart rate > 100 BPM")
        elif hr < 60:
            alerts.append("⚠️ Bradycardia: Heart rate < 60 BPM")
    
    # Temperature alerts
    temp = vitals.get('temperature')
    if temp:
        if temp >= 103:
            alerts.append("🚨 CRITICAL: High fever (>= 103°F)")
        elif temp >= 100.4:
            alerts.append("⚠️ Fever detected (>= 100.4°F)")
        elif temp < 97:
            alerts.append("⚠️ Low body temperature (< 97°F)")
    
    # Blood sugar alerts
    bs = vitals.get('blood_sugar')
    if bs:
        if bs >= 250:
            alerts.append("🚨 CRITICAL: Very high blood sugar (>= 250 mg/dL)")
        elif bs >= 180:
            alerts.append("⚠️ HIGH: Blood sugar >= 180 mg/dL")
        elif bs <= 70:
            alerts.append("⚠️ LOW: Hypoglycemia (<= 70 mg/dL)")
    
    # Oxygen saturation alerts
    spo2 = vitals.get('oxygen_saturation')
    if spo2:
        if spo2 < 90:
            alerts.append("🚨 CRITICAL: Severe hypoxemia (SpO2 < 90%)")
        elif spo2 < 95:
            alerts.append("⚠️ LOW: Below normal oxygen saturation (SpO2 < 95%)")
    
    # Respiratory rate alerts
    rr = vitals.get('respiratory_rate')
    if rr:
        if rr > 25:
            alerts.append("⚠️ Tachypnea: Respiratory rate > 25/min")
        elif rr < 12:
            alerts.append("⚠️ Bradypnea: Respiratory rate < 12/min")
    
    return alerts

@router.post("/", response_model=VitalsResponse)
async def record_vitals(vitals: VitalsCreate):
    """Record patient vital signs"""
    db = await get_db()
    
    # Verify patient exists - check all patient collections
    patient = await db.patients.find_one({"id": vitals.patient_id}, {"_id": 0})
    if not patient:
        patient = await db.healthtrack_patients.find_one({"id": vitals.patient_id}, {"_id": 0})
    if not patient:
        # Also check users collection
        patient = await db.users.find_one({"id": vitals.patient_id}, {"_id": 0})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
    
    vitals_dict = vitals.dict()
    vitals_dict["id"] = str(uuid4())
    vitals_dict["recorded_at"] = datetime.now(timezone.utc).isoformat()
    
    # Calculate BMI if both weight and height provided
    vitals_dict["bmi"] = calculate_bmi(vitals.weight, vitals.height)
    
    # Check for alerts
    vitals_dict["alerts"] = check_vital_alerts(vitals_dict)
    
    await db.vitals.insert_one(vitals_dict)
    vitals_dict.pop("_id", None)
    
    return vitals_dict

@router.get("/{patient_id}", response_model=List[VitalsResponse])
async def get_patient_vitals(
    patient_id: str,
    limit: int = Query(default=50, le=200),
    days: int = Query(default=30, le=365, description="Number of days to look back")
):
    """Get vitals history for a patient"""
    db = await get_db()
    
    # Calculate date range
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    cursor = db.vitals.find(
        {"patient_id": patient_id, "recorded_at": {"$gte": start_date}},
        {"_id": 0}
    ).sort("recorded_at", -1).limit(limit)
    
    vitals = await cursor.to_list(length=limit)
    return vitals

@router.get("/{patient_id}/latest")
async def get_latest_vitals(patient_id: str):
    """Get the most recent vitals for a patient"""
    db = await get_db()
    
    vitals = await db.vitals.find_one(
        {"patient_id": patient_id},
        {"_id": 0},
        sort=[("recorded_at", -1)]
    )
    
    if not vitals:
        return {"message": "No vitals recorded for this patient", "patient_id": patient_id}
    
    return vitals

@router.get("/{patient_id}/summary")
async def get_vitals_summary(patient_id: str, days: int = Query(default=7, le=90)):
    """Get vitals summary with averages and trends"""
    db = await get_db()
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    vitals_list = await db.vitals.find(
        {"patient_id": patient_id, "recorded_at": {"$gte": start_date}},
        {"_id": 0}
    ).to_list(1000)
    
    if not vitals_list:
        return {
            "patient_id": patient_id,
            "period_days": days,
            "total_readings": 0,
            "message": "No vitals recorded in this period"
        }
    
    # Calculate averages
    def avg(values):
        valid = [v for v in values if v is not None]
        return round(sum(valid) / len(valid), 1) if valid else None
    
    return {
        "patient_id": patient_id,
        "period_days": days,
        "total_readings": len(vitals_list),
        "averages": {
            "blood_pressure_systolic": avg([v.get("blood_pressure_systolic") for v in vitals_list]),
            "blood_pressure_diastolic": avg([v.get("blood_pressure_diastolic") for v in vitals_list]),
            "heart_rate": avg([v.get("heart_rate") for v in vitals_list]),
            "temperature": avg([v.get("temperature") for v in vitals_list]),
            "blood_sugar": avg([v.get("blood_sugar") for v in vitals_list]),
            "oxygen_saturation": avg([v.get("oxygen_saturation") for v in vitals_list]),
            "weight": avg([v.get("weight") for v in vitals_list])
        },
        "latest": vitals_list[0] if vitals_list else None,
        "all_alerts": list(set([alert for v in vitals_list for alert in v.get("alerts", [])]))
    }

@router.delete("/{vitals_id}")
async def delete_vitals(vitals_id: str):
    """Delete a vitals record"""
    db = await get_db()
    
    result = await db.vitals.delete_one({"id": vitals_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vitals record not found")
    
    return {"success": True, "message": "Vitals record deleted"}
