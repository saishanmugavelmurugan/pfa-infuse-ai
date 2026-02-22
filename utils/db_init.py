"""
Database Initialization Script for HealthTrack Pro
Creates indexes for optimal performance at scale (1M+ records)
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def create_indexes():
    """Create all necessary database indexes for scalability"""

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/?authSource=admin")
    db_name = os.environ.get("DB_NAME", "healthtrack_pro")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("Creating database indexes for scalability...")
    
    # Users collection indexes
    print("  - Creating users indexes...")
    await db.users.create_index("email", unique=True, sparse=True)
    await db.users.create_index("phone", sparse=True)
    await db.users.create_index("organization_id")
    await db.users.create_index("role")
    await db.users.create_index([("email", 1), ("organization_id", 1)])
    
    # Patients collection indexes
    print("  - Creating patients indexes...")
    await db.patients.create_index("patient_id", unique=True, sparse=True)
    await db.patients.create_index("organization_id")
    await db.patients.create_index("phone", sparse=True)
    await db.patients.create_index("abha_id", sparse=True)
    await db.patients.create_index([("name", "text"), ("phone", "text")])
    await db.patients.create_index([("organization_id", 1), ("created_at", -1)])
    
    # Doctors collection indexes
    print("  - Creating doctors indexes...")
    await db.doctors.create_index("id", unique=True)
    await db.doctors.create_index("registration_number", unique=True, sparse=True)
    await db.doctors.create_index("type")  # allopathic/ayurvedic
    await db.doctors.create_index("specialty")
    await db.doctors.create_index("location.city")
    await db.doctors.create_index("location.state")
    await db.doctors.create_index("rating")
    await db.doctors.create_index("verified")
    await db.doctors.create_index("available")
    await db.doctors.create_index([("name", "text"), ("specialty", "text"), ("qualification", "text")])
    await db.doctors.create_index([("type", 1), ("specialty", 1), ("rating", -1)])
    await db.doctors.create_index([("location.city", 1), ("type", 1)])
    
    # Doctor reviews indexes
    print("  - Creating doctor_reviews indexes...")
    await db.doctor_reviews.create_index("doctor_id")
    await db.doctor_reviews.create_index("status")
    await db.doctor_reviews.create_index([("doctor_id", 1), ("status", 1), ("created_at", -1)])
    
    # Appointments collection indexes
    print("  - Creating appointments indexes...")
    await db.appointments.create_index("appointment_id", unique=True, sparse=True)
    await db.appointments.create_index("organization_id")
    await db.appointments.create_index("patient_id")
    await db.appointments.create_index("doctor_id")
    await db.appointments.create_index("date")
    await db.appointments.create_index("status")
    await db.appointments.create_index([("organization_id", 1), ("date", 1)])
    await db.appointments.create_index([("doctor_id", 1), ("date", 1), ("status", 1)])
    await db.appointments.create_index([("patient_id", 1), ("date", -1)])
    
    # Lab reports indexes
    print("  - Creating lab_reports indexes...")
    await db.lab_reports.create_index("report_id", unique=True, sparse=True)
    await db.lab_reports.create_index("patient_id")
    await db.lab_reports.create_index("organization_id")
    await db.lab_reports.create_index("date")
    await db.lab_reports.create_index([("patient_id", 1), ("date", -1)])
    
    # Vitals indexes
    print("  - Creating vitals indexes...")
    await db.vitals.create_index("patient_id")
    await db.vitals.create_index("organization_id")
    await db.vitals.create_index("recorded_at")
    await db.vitals.create_index([("patient_id", 1), ("recorded_at", -1)])
    
    # Prescriptions indexes
    print("  - Creating prescriptions indexes...")
    await db.prescriptions.create_index("prescription_id", unique=True, sparse=True)
    await db.prescriptions.create_index("patient_id")
    await db.prescriptions.create_index("doctor_id")
    await db.prescriptions.create_index("organization_id")
    await db.prescriptions.create_index([("patient_id", 1), ("created_at", -1)])
    
    # Video consents indexes
    print("  - Creating video_consents indexes...")
    await db.video_consents.create_index("id", unique=True)
    await db.video_consents.create_index("patient_id")
    await db.video_consents.create_index("organization_id")
    await db.video_consents.create_index("consent_type")
    await db.video_consents.create_index("status")
    await db.video_consents.create_index([("organization_id", 1), ("created_at", -1)])
    await db.video_consents.create_index([("patient_id", 1), ("consent_type", 1)])
    
    # Consent videos storage
    print("  - Creating consent_videos indexes...")
    await db.consent_videos.create_index("consent_id", unique=True)
    await db.consent_videos.create_index("organization_id")
    
    # Doctor access grants (OTP feature)
    print("  - Creating doctor_access_grants indexes...")
    await db.doctor_access_grants.create_index("patient_id")
    await db.doctor_access_grants.create_index("doctor_id")
    await db.doctor_access_grants.create_index("access_token")
    await db.doctor_access_grants.create_index("status")
    await db.doctor_access_grants.create_index("expires_at")
    await db.doctor_access_grants.create_index([("patient_id", 1), ("doctor_id", 1), ("status", 1)])
    
    # Doctor access logs
    print("  - Creating doctor_access_logs indexes...")
    await db.doctor_access_logs.create_index("patient_id")
    await db.doctor_access_logs.create_index("doctor_id")
    await db.doctor_access_logs.create_index("accessed_at")
    await db.doctor_access_logs.create_index([("patient_id", 1), ("accessed_at", -1)])
    
    # Wearable data indexes
    print("  - Creating wearable_data indexes...")
    await db.wearable_data.create_index("patient_id")
    await db.wearable_data.create_index("device_type")
    await db.wearable_data.create_index("synced_at")
    await db.wearable_data.create_index([("patient_id", 1), ("synced_at", -1)])
    
    # Health records indexes
    print("  - Creating health_records indexes...")
    await db.health_records.create_index("patient_id")
    await db.health_records.create_index("organization_id")
    await db.health_records.create_index("record_type")
    await db.health_records.create_index([("patient_id", 1), ("created_at", -1)])
    
    # Organizations (multi-tenant)
    print("  - Creating organizations indexes...")
    await db.organizations.create_index("id", unique=True)
    await db.organizations.create_index("name")
    await db.organizations.create_index("status")
    
    # Audit logs
    print("  - Creating audit_logs indexes...")
    await db.audit_logs.create_index("organization_id")
    await db.audit_logs.create_index("user_id")
    await db.audit_logs.create_index("action")
    await db.audit_logs.create_index("timestamp")
    await db.audit_logs.create_index([("organization_id", 1), ("timestamp", -1)])
    
    # Notifications
    print("  - Creating notifications indexes...")
    await db.notifications.create_index("user_id")
    await db.notifications.create_index("read")
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    
    # Feature flags
    print("  - Creating feature_flags indexes...")
    await db.feature_flags.create_index("organization_id")
    await db.feature_flags.create_index("flag_name")
    await db.feature_flags.create_index([("organization_id", 1), ("flag_name", 1)], unique=True)
    
    print("\n✅ All database indexes created successfully!")
    print("   Your database is now optimized for 1M+ records")
    
    # Print index summary
    collections = await db.list_collection_names()
    print(f"\n📊 Index Summary ({len(collections)} collections):")
    for coll_name in sorted(collections):
        indexes = await db[coll_name].index_information()
        print(f"   - {coll_name}: {len(indexes)} indexes")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())
