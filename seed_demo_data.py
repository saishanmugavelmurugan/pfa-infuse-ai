"""
Seed demo data for HealthTrack Pro
Creates demo doctor, demo patient, and sample data
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta, date
import uuid
import bcrypt
import os

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'healthtrack_pro')

async def seed_demo_data():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🌱 Seeding demo data...")
    
    # 1. Create demo organization
    org_id = str(uuid.uuid4())
    demo_org = {
        "id": org_id,
        "company_name": "Demo Healthcare Clinic",
        "industry": "Healthcare",
        "company_size": "small",
        "country": "India",
        "city": "Mumbai",
        "admin_user_id": "will-be-updated",
        "team_members": [],
        "subscription_tier": "pro",
        "subscription_status": "active",
        "billing_email": "demo@infuse.ai",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Check if org exists
    existing_org = await db.organizations.find_one({"company_name": "Demo Healthcare Clinic"})
    if existing_org:
        org_id = existing_org["id"]
        print("✅ Demo organization already exists")
    else:
        await db.organizations.insert_one(demo_org)
        print("✅ Created demo organization")
    
    # 2. Create demo doctor
    doctor_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw("demo1234".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    demo_doctor = {
        "id": doctor_id,
        "name": "Dr. Priya Sharma",
        "email": "doctor.priya@infuse.demo",
        "password_hash": password_hash,
        "role": "doctor",
        "specialty": "General Physician",
        "experience_years": 10,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing_doctor = await db.users.find_one({"email": "doctor.priya@infuse.demo"})
    if existing_doctor:
        doctor_id = existing_doctor["id"]
        print("✅ Demo doctor already exists")
    else:
        await db.users.insert_one(demo_doctor)
        print("✅ Created demo doctor: doctor.priya@infuse.demo / demo1234")
    
    # 3. Create demo patient
    patient_user_id = str(uuid.uuid4())
    demo_patient_user = {
        "id": patient_user_id,
        "name": "Rahul Verma",
        "email": "patient.rahul@infuse.demo",
        "password_hash": password_hash,
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing_patient_user = await db.users.find_one({"email": "patient.rahul@infuse.demo"})
    if existing_patient_user:
        patient_user_id = existing_patient_user["id"]
        print("✅ Demo patient user already exists")
    else:
        await db.users.insert_one(demo_patient_user)
        print("✅ Created demo patient: patient.rahul@infuse.demo / demo1234")
    
    # Update org with doctor as admin
    await db.organizations.update_one(
        {"id": org_id},
        {"$set": {
            "admin_user_id": doctor_id,
            "team_members": [doctor_id, patient_user_id]
        }}
    )
    
    # 4. Create patient record
    patient_id = str(uuid.uuid4())
    demo_patient_record = {
        "id": patient_id,
        "organization_id": org_id,
        "user_id": patient_user_id,
        "patient_number": "PAT-100001",
        "first_name": "Rahul",
        "last_name": "Verma",
        "email": "patient.rahul@infuse.demo",
        "phone": "+919876543210",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "address": "123 MG Road",
        "city": "Mumbai",
        "state": "Maharashtra",
        "country": "India",
        "postal_code": "400001",
        "emergency_contact": {
            "name": "Priya Verma",
            "relationship": "Spouse",
            "phone": "+919876543211"
        },
        "medical_history": {
            "chronic_conditions": ["Diabetes Type 2"],
            "allergies": ["Penicillin"],
            "blood_group": "O+",
            "smoking_status": "never",
            "alcohol_consumption": "occasional"
        },
        "status": "active",
        "created_by": doctor_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing_patient = await db.healthtrack_patients.find_one({"email": "patient.rahul@infuse.demo"})
    if existing_patient:
        patient_id = existing_patient["id"]
        print("✅ Demo patient record already exists")
    else:
        await db.healthtrack_patients.insert_one(demo_patient_record)
        print("✅ Created patient record for Rahul Verma")
    
    # 5. Create sample appointments (past and future)
    appointments = []
    for i in range(5):
        appt_date = (datetime.now() + timedelta(days=i-2)).date()
        appt_time = "10:30" if i % 2 == 0 else "14:00"
        status = "completed" if i < 2 else "scheduled"
        
        appointment = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": appt_date.isoformat(),
            "appointment_time": appt_time,
            "duration_minutes": 30,
            "appointment_type": "consultation",
            "status": status,
            "reason": f"Follow-up checkup {i+1}",
            "payment_status": "paid" if status == "completed" else "pending",
            "payment_amount": 500.0,
            "doctor_confirmed": True,
            "match_score": 0.9,
            "match_reasons": ["Previous consultation"],
            "created_by": patient_user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        appointments.append(appointment)
    
    existing_appts = await db.healthtrack_appointments.count_documents({"patient_id": patient_id})
    if existing_appts == 0:
        await db.healthtrack_appointments.insert_many(appointments)
        print(f"✅ Created {len(appointments)} sample appointments")
    else:
        print(f"✅ Sample appointments already exist")
    
    # 6. Create medical records
    medical_record = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_id": appointments[0]["id"] if appointments else str(uuid.uuid4()),
        "record_date": datetime.now(timezone.utc).isoformat(),
        "vitals": {
            "blood_pressure_systolic": 128,
            "blood_pressure_diastolic": 82,
            "heart_rate": 75,
            "temperature": 98.6,
            "weight": 70,
            "height": 170,
            "bmi": 24.2,
            "blood_sugar": 110,
            "oxygen_saturation": 98
        },
        "chief_complaint": "Regular diabetes checkup",
        "symptoms": ["None"],
        "diagnosis": "Diabetes Type 2 - controlled",
        "treatment_plan": "Continue current medication, diet control",
        "notes": "Blood sugar levels under control",
        "is_encrypted": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing_records = await db.healthtrack_medical_records.count_documents({"patient_id": patient_id})
    if existing_records == 0:
        await db.healthtrack_medical_records.insert_one(medical_record)
        print("✅ Created sample medical record")
    
    # 7. Create prescription
    prescription = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_id": appointments[0]["id"] if appointments else str(uuid.uuid4()),
        "prescription_number": f"RX-{datetime.now().strftime('%Y%m%d')}-1001",
        "prescription_date": datetime.now(timezone.utc).isoformat(),
        "medications": [
            {
                "drug_name": "Metformin",
                "dosage": "500mg",
                "frequency": "Twice daily",
                "duration": "30 days",
                "quantity": 60,
                "instructions": "Take after meals"
            }
        ],
        "diagnosis": "Diabetes Type 2",
        "status": "active",
        "valid_until": (datetime.now() + timedelta(days=30)).date().isoformat(),
        "estimated_cost": 200.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing_prescriptions = await db.healthtrack_prescriptions.count_documents({"patient_id": patient_id})
    if existing_prescriptions == 0:
        await db.healthtrack_prescriptions.insert_one(prescription)
        print("✅ Created sample prescription")
    
    # 8. Seed common drugs
    common_drugs = [
        {
            "id": str(uuid.uuid4()),
            "drug_name": "Paracetamol",
            "generic_name": "Acetaminophen",
            "brand_names": ["Crocin", "Dolo"],
            "category": "Analgesic",
            "available_forms": ["tablet", "syrup"],
            "common_dosages": ["500mg", "650mg"],
            "price_range": {"min": 5, "max": 50, "currency": "INR"},
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "drug_name": "Metformin",
            "generic_name": "Metformin",
            "brand_names": ["Glycomet", "Diabex"],
            "category": "Antidiabetic",
            "available_forms": ["tablet"],
            "common_dosages": ["500mg", "850mg", "1000mg"],
            "price_range": {"min": 20, "max": 150, "currency": "INR"},
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    existing_drugs = await db.drug_database.count_documents({})
    if existing_drugs == 0:
        await db.drug_database.insert_many(common_drugs)
        print(f"✅ Seeded {len(common_drugs)} common drugs")
    
    print("\n🎉 Demo data seeding complete!")
    print("\n📋 LOGIN CREDENTIALS:")
    print("=" * 50)
    print("Demo Doctor:")
    print("  Email: doctor.priya@infuse.demo")
    print("  Password: demo1234")
    print("\nDemo Patient:")
    print("  Email: patient.rahul@infuse.demo")
    print("  Password: demo1234")
    print("=" * 50)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
