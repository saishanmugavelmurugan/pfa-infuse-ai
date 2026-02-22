"""
Seed comprehensive demo data for HealthTrack Pro AI Analytics
Includes: Lab Tests, Wearable Devices, and Health Data
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import random
import os

async def seed_ai_analytics_data():
    """Seed comprehensive demo data for AI analytics"""
    
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017/?authSource=admin"))
    db = client[os.environ.get('DB_NAME', 'healthtrack_pro')]
    
    print("🔬 Seeding AI Analytics Demo Data...")
    
    # Get the demo patient
    patient = await db.healthtrack_patients.find_one({"email": "patient.rahul@infuse.demo"})
    if not patient:
        print("❌ Demo patient not found. Run seed_demo_data.py first.")
        return
    
    patient_id = patient["id"]
    org_id = patient["organization_id"]
    
    # Get demo doctor
    doctor = await db.users.find_one({"email": "doctor.priya@infuse.demo"})
    doctor_id = doctor["id"] if doctor else str(uuid4())
    
    # =============================================
    # 1. SEED COMPREHENSIVE LAB TEST DATA
    # =============================================
    print("📊 Creating lab test data...")
    
    lab_tests = [
        {
            "id": str(uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_name": "Complete Blood Count (CBC)",
            "test_type": "hematology",
            "order_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "status": "completed",
            "priority": "routine",
            "results": {
                "hemoglobin": {"value": 14.2, "unit": "g/dL", "reference_range": "13.5-17.5", "status": "normal"},
                "wbc": {"value": 7500, "unit": "cells/mcL", "reference_range": "4500-11000", "status": "normal"},
                "rbc": {"value": 5.1, "unit": "million/mcL", "reference_range": "4.5-5.5", "status": "normal"},
                "platelets": {"value": 250000, "unit": "cells/mcL", "reference_range": "150000-400000", "status": "normal"},
                "hematocrit": {"value": 42, "unit": "%", "reference_range": "38.8-50", "status": "normal"},
                "mcv": {"value": 88, "unit": "fL", "reference_range": "80-100", "status": "normal"}
            },
            "result_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "notes": "All values within normal range",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_name": "Lipid Profile",
            "test_type": "biochemistry",
            "order_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "status": "completed",
            "priority": "routine",
            "results": {
                "total_cholesterol": {"value": 215, "unit": "mg/dL", "reference_range": "<200", "status": "high"},
                "ldl_cholesterol": {"value": 142, "unit": "mg/dL", "reference_range": "<100", "status": "high"},
                "hdl_cholesterol": {"value": 48, "unit": "mg/dL", "reference_range": ">40", "status": "normal"},
                "triglycerides": {"value": 165, "unit": "mg/dL", "reference_range": "<150", "status": "borderline_high"},
                "vldl": {"value": 33, "unit": "mg/dL", "reference_range": "5-40", "status": "normal"}
            },
            "result_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
            "notes": "Elevated LDL and triglycerides. Lifestyle modifications recommended.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_name": "Diabetes Panel (HbA1c)",
            "test_type": "biochemistry",
            "order_date": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            "status": "completed",
            "priority": "routine",
            "results": {
                "fasting_glucose": {"value": 118, "unit": "mg/dL", "reference_range": "70-100", "status": "pre_diabetic"},
                "hba1c": {"value": 6.2, "unit": "%", "reference_range": "<5.7", "status": "pre_diabetic"},
                "post_prandial_glucose": {"value": 145, "unit": "mg/dL", "reference_range": "<140", "status": "borderline_high"},
                "insulin_fasting": {"value": 12, "unit": "μU/mL", "reference_range": "2.6-24.9", "status": "normal"}
            },
            "result_date": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
            "notes": "Pre-diabetic range. Strict dietary control and regular exercise recommended.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_name": "Thyroid Function Test",
            "test_type": "endocrine",
            "order_date": (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(),
            "status": "completed",
            "priority": "routine",
            "results": {
                "tsh": {"value": 2.8, "unit": "mIU/L", "reference_range": "0.4-4.0", "status": "normal"},
                "t3": {"value": 120, "unit": "ng/dL", "reference_range": "80-200", "status": "normal"},
                "t4": {"value": 8.5, "unit": "μg/dL", "reference_range": "4.5-12.5", "status": "normal"},
                "free_t4": {"value": 1.2, "unit": "ng/dL", "reference_range": "0.8-1.8", "status": "normal"}
            },
            "result_date": (datetime.now(timezone.utc) - timedelta(days=12)).isoformat(),
            "notes": "Thyroid function normal",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_name": "Liver Function Test (LFT)",
            "test_type": "biochemistry",
            "order_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "status": "completed",
            "priority": "routine",
            "results": {
                "sgpt_alt": {"value": 35, "unit": "U/L", "reference_range": "7-56", "status": "normal"},
                "sgot_ast": {"value": 28, "unit": "U/L", "reference_range": "10-40", "status": "normal"},
                "alkaline_phosphatase": {"value": 85, "unit": "U/L", "reference_range": "44-147", "status": "normal"},
                "total_bilirubin": {"value": 0.8, "unit": "mg/dL", "reference_range": "0.1-1.2", "status": "normal"},
                "albumin": {"value": 4.2, "unit": "g/dL", "reference_range": "3.5-5.0", "status": "normal"},
                "total_protein": {"value": 7.0, "unit": "g/dL", "reference_range": "6.0-8.3", "status": "normal"}
            },
            "result_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "notes": "Liver function tests within normal limits",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_name": "Kidney Function Test (KFT)",
            "test_type": "biochemistry",
            "order_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "status": "completed",
            "priority": "routine",
            "results": {
                "blood_urea": {"value": 32, "unit": "mg/dL", "reference_range": "17-43", "status": "normal"},
                "serum_creatinine": {"value": 1.0, "unit": "mg/dL", "reference_range": "0.7-1.3", "status": "normal"},
                "uric_acid": {"value": 5.8, "unit": "mg/dL", "reference_range": "3.5-7.2", "status": "normal"},
                "bun_creatinine_ratio": {"value": 16, "unit": "", "reference_range": "10-20", "status": "normal"},
                "egfr": {"value": 92, "unit": "mL/min/1.73m²", "reference_range": ">90", "status": "normal"}
            },
            "result_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "notes": "Kidney function normal",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "test_name": "Vitamin D & B12 Panel",
            "test_type": "vitamins",
            "order_date": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
            "status": "completed",
            "priority": "routine",
            "results": {
                "vitamin_d_25oh": {"value": 22, "unit": "ng/mL", "reference_range": "30-100", "status": "deficient"},
                "vitamin_b12": {"value": 320, "unit": "pg/mL", "reference_range": "200-900", "status": "normal"},
                "folate": {"value": 12, "unit": "ng/mL", "reference_range": "3-17", "status": "normal"}
            },
            "result_date": (datetime.now(timezone.utc) - timedelta(days=18)).isoformat(),
            "notes": "Vitamin D deficiency detected. Supplementation recommended.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Clear existing lab tests for the patient and insert new ones
    await db.healthtrack_lab_tests.delete_many({"patient_id": patient_id})
    await db.healthtrack_lab_tests.insert_many(lab_tests)
    print(f"   ✓ Created {len(lab_tests)} lab test records")
    
    # =============================================
    # 2. SEED WEARABLE DEVICES
    # =============================================
    print("⌚ Creating wearable devices...")
    
    devices = [
        {
            "id": str(uuid4()),
            "patient_id": patient_id,
            "device_type": "apple_watch",
            "device_name": "Apple Watch Series 9",
            "device_id": f"AW-{uuid4().hex[:8].upper()}",
            "is_connected": True,
            "connected_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "last_sync": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "patient_id": patient_id,
            "device_type": "fitbit",
            "device_name": "Fitbit Charge 6",
            "device_id": f"FB-{uuid4().hex[:8].upper()}",
            "is_connected": True,
            "connected_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
            "last_sync": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.healthtrack_wearable_devices.delete_many({"patient_id": patient_id})
    await db.healthtrack_wearable_devices.insert_many(devices)
    print(f"   ✓ Created {len(devices)} wearable devices")
    
    # =============================================
    # 3. SEED WEARABLE HEALTH DATA (30 days)
    # =============================================
    print("📈 Creating wearable health data (this may take a moment)...")
    
    wearable_data = []
    now = datetime.now(timezone.utc)
    
    for day in range(30):  # 30 days of data
        for hour in range(24):  # Hourly data
            timestamp = now - timedelta(days=day, hours=hour)
            
            # Simulate realistic patterns
            is_sleeping = 0 <= hour <= 6 or hour >= 23
            is_active = 8 <= hour <= 20
            is_exercise = hour in [7, 18] and day % 2 == 0  # Morning/evening exercise every other day
            
            # Base values with some variation by day (simulate trends)
            day_factor = 1 + (random.uniform(-0.1, 0.1))
            stress_base = 25 if day < 15 else 35  # Higher stress in recent weeks
            
            data_point = {
                "id": str(uuid4()),
                "patient_id": patient_id,
                "device_type": "apple_watch",
                "recorded_at": timestamp.isoformat(),
                "heart_rate": int((55 + random.randint(0, 10)) * day_factor) if is_sleeping else \
                              int((130 + random.randint(0, 30)) * day_factor) if is_exercise else \
                              int((70 + random.randint(0, 15)) * day_factor) if is_active else \
                              int((65 + random.randint(0, 10)) * day_factor),
                "steps": 0 if is_sleeping else \
                         random.randint(800, 1500) if is_exercise else \
                         random.randint(200, 600) if is_active else \
                         random.randint(0, 100),
                "calories_burned": random.randint(40, 60) if is_sleeping else \
                                   random.randint(250, 400) if is_exercise else \
                                   random.randint(80, 150) if is_active else \
                                   random.randint(50, 80),
                "blood_oxygen": round(random.uniform(96, 99), 1),
                "stress_level": random.randint(10, 25) if is_sleeping else \
                                random.randint(40, 70) if is_exercise else \
                                random.randint(stress_base, stress_base + 25),
                "active_minutes": 0 if is_sleeping else \
                                  random.randint(30, 55) if is_exercise else \
                                  random.randint(5, 25) if is_active else 0
            }
            
            # Add sleep data at end of sleep cycle
            if is_sleeping and hour == 6:
                sleep_quality_options = ["poor", "fair", "good", "excellent"]
                data_point["sleep_hours"] = round(random.uniform(5.5, 8), 1)
                data_point["sleep_quality"] = random.choices(
                    sleep_quality_options,
                    weights=[0.1, 0.25, 0.45, 0.2]
                )[0]
                data_point["deep_sleep_hours"] = round(data_point["sleep_hours"] * random.uniform(0.15, 0.25), 1)
                data_point["rem_sleep_hours"] = round(data_point["sleep_hours"] * random.uniform(0.2, 0.25), 1)
            
            wearable_data.append(data_point)
    
    # Clear existing and insert new data
    await db.healthtrack_wearable_data.delete_many({"patient_id": patient_id})
    
    # Insert in batches
    batch_size = 200
    for i in range(0, len(wearable_data), batch_size):
        batch = wearable_data[i:i + batch_size]
        await db.healthtrack_wearable_data.insert_many(batch)
    
    print(f"   ✓ Created {len(wearable_data)} wearable data points")
    
    # =============================================
    # 4. CREATE SAMPLE AI ANALYSIS
    # =============================================
    print("🤖 Creating sample AI analysis...")
    
    sample_analysis = {
        "id": str(uuid4()),
        "patient_id": patient_id,
        "analysis_type": "comprehensive",
        "summary": "Overall health status shows pre-diabetic tendencies and elevated cholesterol requiring attention. Vitamin D deficiency detected. Cardiovascular metrics from wearable devices indicate moderate fitness level with room for improvement.",
        "allopathic_recommendations": [
            "Consider Metformin therapy if lifestyle modifications don't improve HbA1c within 3 months",
            "Statin therapy may be recommended if LDL remains above 130 mg/dL",
            "Vitamin D3 supplementation: 60,000 IU weekly for 8 weeks, then maintenance dose",
            "Regular monitoring of blood sugar levels - fasting and post-prandial",
            "Annual cardiovascular risk assessment recommended"
        ],
        "ayurvedic_recommendations": [
            "Karela (Bitter Gourd) juice: 30ml on empty stomach for blood sugar control",
            "Triphala churna: 1 tsp with warm water before bed for digestion and detox",
            "Ashwagandha: 500mg twice daily for stress management and metabolic support",
            "Guggul: For cholesterol management - consult Ayurvedic practitioner for dosage",
            "Morning sunlight exposure (15-20 mins) for natural Vitamin D synthesis",
            "Fenugreek seeds soaked overnight - consume with water in morning"
        ],
        "lifestyle_tips": [
            "Aim for 10,000 steps daily - current average is 7,500",
            "Improve sleep quality - target 7-8 hours with consistent schedule",
            "Reduce refined carbohydrates and increase fiber intake",
            "Include 30 minutes of moderate exercise 5 days a week",
            "Practice stress-reduction techniques like yoga or meditation",
            "Stay hydrated - aim for 8-10 glasses of water daily"
        ],
        "warning_signs": [
            "Seek immediate care if experiencing chest pain or shortness of breath",
            "Monitor for symptoms of hyperglycemia: excessive thirst, frequent urination",
            "Watch for fatigue, muscle weakness (Vitamin D deficiency symptoms)",
            "Report any unusual heart palpitations or irregular heartbeat"
        ],
        "disclaimer": "⚠️ IMPORTANT MEDICAL DISCLAIMER: This AI-generated analysis is for informational purposes only and should NOT be considered as medical advice. Always consult with a qualified healthcare professional before making any health-related decisions or starting any treatment. The recommendations provided are general in nature and may not be suitable for your specific condition.",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.healthtrack_ai_analyses.delete_many({"patient_id": patient_id})
    await db.healthtrack_ai_analyses.insert_one(sample_analysis)
    print("   ✓ Created sample AI analysis")
    
    print("\n✅ AI Analytics Demo Data Seeding Complete!")
    print(f"   - Lab Tests: {len(lab_tests)}")
    print(f"   - Wearable Devices: {len(devices)}")
    print(f"   - Health Data Points: {len(wearable_data)}")
    print(f"   - Sample AI Analysis: 1")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_ai_analytics_data())
