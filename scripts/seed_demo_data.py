#!/usr/bin/env python3
"""
Demo Data Seeder for HealthTrack Pro & SecureSphere
Creates comprehensive demo accounts and sample data for production testing
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import random

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def seed_demo_data():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    print("\n" + "="*60)
    print("    DEMO DATA SEEDER - HealthTrack Pro & SecureSphere")
    print("="*60)
    
    # ==================== USERS ====================
    print("\n[1/8] Creating Demo Users...")
    
    users = [
        # Super Admin
        {
            "id": str(uuid4()),
            "email": "admin@infuse.demo",
            "password_hash": hash_password("admin1234"),
            "name": "Super Admin",
            "role": "super_admin",
            "status": "active",
            "is_active": True,
            "permissions": ["all"],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # Doctors
        {
            "id": str(uuid4()),
            "email": "doctor.priya@infuse.demo",
            "password_hash": hash_password("demo1234"),
            "name": "Dr. Priya Sharma",
            "role": "doctor",
            "status": "active",
            "is_active": True,
            "specialty": "General Physician",
            "license_number": "MCI-123456",
            "hospital": "Infuse Medical Center",
            "phone": "+91-9876543210",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "email": "doctor.raj@infuse.demo",
            "password_hash": hash_password("demo1234"),
            "name": "Dr. Raj Patel",
            "role": "doctor",
            "status": "active",
            "is_active": True,
            "specialty": "Cardiologist",
            "license_number": "MCI-789012",
            "hospital": "Heart Care Hospital",
            "phone": "+91-9876543211",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # Patients
        {
            "id": str(uuid4()),
            "email": "patient.rahul@infuse.demo",
            "password_hash": hash_password("demo1234"),
            "name": "Rahul Kumar",
            "role": "patient",
            "status": "active",
            "is_active": True,
            "phone": "+91-9876543212",
            "dob": "1990-05-15",
            "blood_group": "O+",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "email": "patient.meera@infuse.demo",
            "password_hash": hash_password("demo1234"),
            "name": "Meera Gupta",
            "role": "patient",
            "status": "active",
            "is_active": True,
            "phone": "+91-9876543213",
            "dob": "1985-08-22",
            "blood_group": "A+",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # US Patient for Health Schemes
        {
            "id": str(uuid4()),
            "email": "patient.john@infuse.demo",
            "password_hash": hash_password("demo1234"),
            "name": "John Smith",
            "role": "patient",
            "status": "active",
            "is_active": True,
            "phone": "+1-555-123-4567",
            "country": "US",
            "dob": "1975-03-10",
            "blood_group": "B+",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for user in users:
        await db.users.update_one(
            {"email": user["email"]},
            {"$set": user},
            upsert=True
        )
    print(f"   Created {len(users)} demo users")
    
    # Get user IDs
    doctor_priya = await db.users.find_one({"email": "doctor.priya@infuse.demo"})
    doctor_raj = await db.users.find_one({"email": "doctor.raj@infuse.demo"})
    patient_rahul = await db.users.find_one({"email": "patient.rahul@infuse.demo"})
    patient_meera = await db.users.find_one({"email": "patient.meera@infuse.demo"})
    
    # ==================== PATIENTS (Healthcare Records) ====================
    print("\n[2/8] Creating Patient Records...")
    
    patients = [
        {
            "id": str(uuid4()),
            "user_id": patient_rahul["id"],
            "first_name": "Rahul",
            "last_name": "Kumar",
            "email": patient_rahul["email"],
            "phone": patient_rahul["phone"],
            "date_of_birth": "1990-05-15",
            "gender": "male",
            "blood_type": "O+",
            "patient_number": "PT-2024-001",
            "address": "123 MG Road, Bangalore",
            "emergency_contact": "+91-9876543299",
            "allergies": ["Penicillin"],
            "chronic_conditions": ["Hypertension"],
            "abha_id": "91-1234-5678-9012",
            "abdm_linked": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "user_id": patient_meera["id"],
            "first_name": "Meera",
            "last_name": "Gupta",
            "email": patient_meera["email"],
            "phone": patient_meera["phone"],
            "date_of_birth": "1985-08-22",
            "gender": "female",
            "blood_type": "A+",
            "patient_number": "PT-2024-002",
            "address": "456 Park Street, Mumbai",
            "emergency_contact": "+91-9876543298",
            "allergies": [],
            "chronic_conditions": ["Diabetes Type 2"],
            "abha_id": "91-5678-9012-3456",
            "abdm_linked": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for patient in patients:
        await db.patients.update_one(
            {"email": patient["email"]},
            {"$set": patient},
            upsert=True
        )
    print(f"   Created {len(patients)} patient records")
    
    # ==================== APPOINTMENTS ====================
    print("\n[3/8] Creating Appointments...")
    
    appointments = []
    statuses = ["scheduled", "completed", "completed", "completed"]
    
    for i in range(10):
        apt_date = datetime.now(timezone.utc) + timedelta(days=random.randint(-30, 30))
        appointments.append({
            "id": str(uuid4()),
            "patient_id": random.choice([patients[0]["id"], patients[1]["id"]]),
            "doctor_id": random.choice([doctor_priya["id"], doctor_raj["id"]]),
            "date": apt_date.strftime("%Y-%m-%d"),
            "time": f"{random.randint(9, 17):02d}:00",
            "status": random.choice(statuses),
            "type": random.choice(["consultation", "follow-up", "check-up"]),
            "notes": "Regular health checkup",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    for apt in appointments:
        await db.appointments.insert_one(apt)
    print(f"   Created {len(appointments)} appointments")
    
    # ==================== PRESCRIPTIONS ====================
    print("\n[4/8] Creating Prescriptions...")
    
    prescriptions = [
        {
            "id": str(uuid4()),
            "patient_id": patients[0]["id"],
            "doctor_id": doctor_priya["id"],
            "medications": [
                {"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily", "duration": "30 days"},
                {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily", "duration": "30 days"}
            ],
            "diagnosis": "Hypertension management",
            "instructions": "Take with food. Monitor blood pressure regularly.",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "patient_id": patients[1]["id"],
            "doctor_id": doctor_raj["id"],
            "medications": [
                {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily", "duration": "30 days"},
                {"name": "Glimepiride", "dosage": "1mg", "frequency": "Once daily", "duration": "30 days"}
            ],
            "diagnosis": "Diabetes Type 2 management",
            "instructions": "Monitor blood sugar levels. Maintain healthy diet.",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for rx in prescriptions:
        await db.prescriptions.insert_one(rx)
    print(f"   Created {len(prescriptions)} prescriptions")
    
    # ==================== LAB TESTS ====================
    print("\n[5/8] Creating Lab Tests...")
    
    lab_tests = [
        {
            "id": str(uuid4()),
            "patient_id": patients[0]["id"],
            "doctor_id": doctor_priya["id"],
            "test_name": "Complete Blood Count (CBC)",
            "test_type": "blood",
            "status": "completed",
            "results": {
                "hemoglobin": {"value": 14.2, "unit": "g/dL", "normal_range": "13.5-17.5"},
                "wbc": {"value": 7500, "unit": "cells/mcL", "normal_range": "4500-11000"},
                "platelets": {"value": 250000, "unit": "cells/mcL", "normal_range": "150000-400000"}
            },
            "ordered_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "completed_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        },
        {
            "id": str(uuid4()),
            "patient_id": patients[1]["id"],
            "doctor_id": doctor_raj["id"],
            "test_name": "Lipid Profile",
            "test_type": "blood",
            "status": "completed",
            "results": {
                "total_cholesterol": {"value": 195, "unit": "mg/dL", "normal_range": "<200"},
                "hdl": {"value": 55, "unit": "mg/dL", "normal_range": ">40"},
                "ldl": {"value": 120, "unit": "mg/dL", "normal_range": "<100"},
                "triglycerides": {"value": 140, "unit": "mg/dL", "normal_range": "<150"}
            },
            "ordered_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            "completed_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        }
    ]
    
    for test in lab_tests:
        await db.lab_tests.insert_one(test)
    print(f"   Created {len(lab_tests)} lab tests")
    
    # ==================== SECURESPHERE DEMO DATA ====================
    print("\n[6/8] Creating SecureSphere Demo Data...")
    
    # URL Scans
    url_scans = [
        {
            "id": str(uuid4()),
            "url": "http://fake-bank-login.xyz/verify",
            "result": {
                "threat_level": "high",
                "risk_score": 85,
                "category": "phishing",
                "safe_to_visit": False
            },
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        },
        {
            "id": str(uuid4()),
            "url": "https://www.google.com",
            "result": {
                "threat_level": "low",
                "risk_score": 5,
                "category": "safe",
                "safe_to_visit": True
            },
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        }
    ]
    
    for scan in url_scans:
        await db.url_scans.insert_one(scan)
    
    # SMS Analyses
    sms_analyses = [
        {
            "id": str(uuid4()),
            "sender": "PRIZE",
            "result": {
                "threat_level": "critical",
                "risk_score": 95,
                "fraud_type": "lottery_scam",
                "is_fraud": True,
                "is_spam": True
            },
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        },
        {
            "id": str(uuid4()),
            "sender": "HDFC-BK",
            "result": {
                "threat_level": "low",
                "risk_score": 15,
                "fraud_type": "legitimate",
                "is_fraud": False,
                "is_spam": False
            },
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        }
    ]
    
    for analysis in sms_analyses:
        await db.sms_analyses.insert_one(analysis)
    
    # Devices
    devices = [
        {
            "device_id": str(uuid4()),
            "user_id": patient_rahul["id"],
            "device_name": "Rahul's iPhone",
            "platform": "ios",
            "os_version": "17.2",
            "status": "active",
            "trust_level": "trusted",
            "latest_threat_score": 25,
            "security_posture": "secure",
            "registered_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "device_id": str(uuid4()),
            "user_id": patient_meera["id"],
            "device_name": "Meera's Android",
            "platform": "android",
            "os_version": "14",
            "status": "active",
            "trust_level": "trusted",
            "latest_threat_score": 35,
            "security_posture": "secure",
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for device in devices:
        await db.devices.insert_one(device)
    
    print(f"   Created {len(url_scans)} URL scans, {len(sms_analyses)} SMS analyses, {len(devices)} devices")
    
    # ==================== SUBSCRIPTION PLANS ====================
    print("\n[7/8] Creating Subscription Plans...")
    
    plans = [
        {
            "id": "plan-free",
            "name": "Free",
            "price": 0,
            "currency": "INR",
            "features": ["5 URL scans/day", "10 SMS analyses/day", "Basic threat reports"],
            "active": True
        },
        {
            "id": "plan-basic",
            "name": "Basic",
            "price": 199,
            "currency": "INR",
            "features": ["Unlimited URL scans", "Unlimited SMS analyses", "Real-time alerts", "Priority support"],
            "active": True
        },
        {
            "id": "plan-pro",
            "name": "Professional",
            "price": 499,
            "currency": "INR",
            "features": ["Everything in Basic", "Device management", "API access", "Custom reports", "Dedicated support"],
            "active": True
        },
        {
            "id": "plan-enterprise",
            "name": "Enterprise",
            "price": 2999,
            "currency": "INR",
            "features": ["Everything in Pro", "Telecom integration", "Automotive security", "White-label option", "SLA guarantee"],
            "active": True
        }
    ]
    
    for plan in plans:
        await db.subscription_plans.update_one(
            {"id": plan["id"]},
            {"$set": plan},
            upsert=True
        )
    print(f"   Created {len(plans)} subscription plans")
    
    # ==================== HEALTH SCHEMES ====================
    print("\n[8/8] Verifying Health Schemes...")
    
    schemes_count = await db.health_schemes.count_documents({})
    if schemes_count == 0:
        print("   Health schemes already seeded by API")
    else:
        print(f"   Found {schemes_count} health schemes")
    
    # Close connection
    client.close()
    
    print("\n" + "="*60)
    print("    DEMO DATA SEEDING COMPLETE!")
    print("="*60)
    print("\nDemo Accounts:")
    print("-" * 40)
    print("| Role          | Email                      | Password  |")
    print("-" * 40)
    print("| Super Admin   | admin@infuse.demo          | admin1234 |")
    print("| Doctor        | doctor.priya@infuse.demo   | demo1234  |")
    print("| Doctor        | doctor.raj@infuse.demo     | demo1234  |")
    print("| Patient (IN)  | patient.rahul@infuse.demo  | demo1234  |")
    print("| Patient (IN)  | patient.meera@infuse.demo  | demo1234  |")
    print("| Patient (US)  | patient.john@infuse.demo   | demo1234  |")
    print("-" * 40)
    print("\nURLs:")
    print("- HealthTrack Pro: /login/health")
    print("- SecureSphere: /securesphere")
    print("- Health Schemes: /health-schemes")
    print("- Super Admin: /admin/super")
    print()

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
