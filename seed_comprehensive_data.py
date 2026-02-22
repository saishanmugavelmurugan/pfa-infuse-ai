"""
Comprehensive Seed Data for HealthTrack Pro & SecureSphere Demo
Creates fully functional demo environment with:
- 2+ demo accounts per user type
- Complete dummy data for all features
- Multi-tenant data isolation
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
from motor.motor_asyncio import AsyncIOMotorClient

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/?authSource=admin")
DB_NAME = os.environ.get("DB_NAME", "infuse_db")

def hash_password(password: str) -> str:
    """Hash password for storage"""
    return hashlib.sha256(password.encode()).hexdigest()

async def seed_database():
    """Seed comprehensive demo data"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🚀 Starting comprehensive data seeding...")
    
    # ==================== USERS ====================
    print("\n👤 Creating demo users...")
    
    demo_users = [
        # HealthTrack Pro - Doctors
        {
            "id": str(uuid4()),
            "email": "doctor.priya@infuse.demo",
            "password": hash_password("demo1234"),
            "name": "Dr. Priya Sharma",
            "role": "doctor",
            "specialty": "General Medicine",
            "license_number": "MCI-123456",
            "phone": "+919876543210",
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "email": "doctor.amit@infuse.demo",
            "password": hash_password("demo1234"),
            "name": "Dr. Amit Patel",
            "role": "doctor",
            "specialty": "Cardiology",
            "license_number": "MCI-789012",
            "phone": "+919876543211",
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # HealthTrack Pro - Patients
        {
            "id": str(uuid4()),
            "email": "patient.rahul@infuse.demo",
            "password": hash_password("demo1234"),
            "name": "Rahul Kumar",
            "role": "patient",
            "phone": "+919876543212",
            "date_of_birth": "1990-05-15",
            "blood_group": "O+",
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "email": "patient.anita@infuse.demo",
            "password": hash_password("demo1234"),
            "name": "Anita Singh",
            "role": "patient",
            "phone": "+919876543213",
            "date_of_birth": "1985-08-22",
            "blood_group": "A+",
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # SecureSphere - Admin
        {
            "id": str(uuid4()),
            "email": "admin@infuse.demo",
            "password": hash_password("admin1234"),
            "name": "Admin User",
            "role": "admin",
            "phone": "+919876543214",
            "verified": True,
            "permissions": ["all"],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # SecureSphere - Enterprise Users
        {
            "id": str(uuid4()),
            "email": "enterprise@infuse.demo",
            "password": hash_password("demo1234"),
            "name": "Enterprise Manager",
            "role": "enterprise",
            "organization": "TechCorp India",
            "phone": "+919876543215",
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "email": "security.analyst@infuse.demo",
            "password": hash_password("demo1234"),
            "name": "Security Analyst",
            "role": "analyst",
            "organization": "TechCorp India",
            "phone": "+919876543216",
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # SecureSphere - Telco Users
        {
            "id": str(uuid4()),
            "email": "telco.admin@infuse.demo",
            "password": hash_password("demo1234"),
            "name": "Telco Network Admin",
            "role": "telco_admin",
            "organization": "Bharti Telecom",
            "phone": "+919876543217",
            "verified": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Clear and insert users
    await db.users.delete_many({"email": {"$regex": "@infuse.demo$"}})
    await db.users.insert_many(demo_users)
    print(f"   ✅ Created {len(demo_users)} demo users")
    
    # Get user IDs for reference
    doctor_user = await db.users.find_one({"email": "doctor.priya@infuse.demo"}, {"_id": 0})
    patient_user = await db.users.find_one({"email": "patient.rahul@infuse.demo"}, {"_id": 0})
    admin_user = await db.users.find_one({"email": "admin@infuse.demo"}, {"_id": 0})
    
    # ==================== PATIENTS (HealthTrack Pro) ====================
    print("\n🏥 Creating patient records...")
    
    demo_patients = [
        {
            "id": str(uuid4()),
            "user_id": patient_user["id"],
            "name": "Rahul Kumar",
            "email": "patient.rahul@infuse.demo",
            "phone": "+919876543212",
            "date_of_birth": "1990-05-15",
            "gender": "male",
            "blood_group": "O+",
            "height": 175,
            "weight": 72,
            "allergies": ["Penicillin"],
            "chronic_conditions": ["Hypertension"],
            "emergency_contact": {"name": "Priya Kumar", "phone": "+919876543220", "relation": "Spouse"},
            "insurance": {"provider": "Star Health", "policy_number": "SH123456789"},
            "address": {"city": "Mumbai", "state": "Maharashtra", "pincode": "400001"},
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "user_id": None,
            "name": "Anita Singh",
            "email": "patient.anita@infuse.demo",
            "phone": "+919876543213",
            "date_of_birth": "1985-08-22",
            "gender": "female",
            "blood_group": "A+",
            "height": 162,
            "weight": 58,
            "allergies": [],
            "chronic_conditions": ["Diabetes Type 2"],
            "emergency_contact": {"name": "Vikram Singh", "phone": "+919876543221", "relation": "Husband"},
            "insurance": {"provider": "ICICI Lombard", "policy_number": "IL987654321"},
            "address": {"city": "Delhi", "state": "Delhi", "pincode": "110001"},
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "user_id": None,
            "name": "Suresh Reddy",
            "email": "suresh.reddy@example.com",
            "phone": "+919876543222",
            "date_of_birth": "1975-12-10",
            "gender": "male",
            "blood_group": "B+",
            "height": 170,
            "weight": 80,
            "allergies": ["Sulfa drugs"],
            "chronic_conditions": ["Asthma"],
            "emergency_contact": {"name": "Lakshmi Reddy", "phone": "+919876543223", "relation": "Wife"},
            "address": {"city": "Hyderabad", "state": "Telangana", "pincode": "500001"},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.patients.delete_many({})
    await db.patients.insert_many(demo_patients)
    print(f"   ✅ Created {len(demo_patients)} patient records")
    
    patient_ids = [p["id"] for p in demo_patients]
    
    # ==================== HEALTH RECORDS ====================
    print("\n📋 Creating health records...")
    
    health_records = []
    for i, patient in enumerate(demo_patients):
        for j in range(3):  # 3 records per patient
            record_date = datetime.now(timezone.utc) - timedelta(days=30*j)
            health_records.append({
                "id": str(uuid4()),
                "patient_id": patient["id"],
                "doctor_id": doctor_user["id"],
                "type": ["checkup", "follow_up", "emergency"][j % 3],
                "diagnosis": ["Seasonal flu", "Blood pressure review", "Routine checkup"][j % 3],
                "symptoms": ["Fever", "Headache", "Fatigue"][:j+1],
                "notes": f"Patient visit #{j+1} for {patient['name']}",
                "vitals": {
                    "blood_pressure": f"{120 + j*5}/{80 + j*2}",
                    "heart_rate": 72 + j*3,
                    "temperature": 98.6 + j*0.2,
                    "weight": patient.get("weight", 70),
                    "spo2": 98 - j
                },
                "created_at": record_date.isoformat()
            })
    
    await db.health_records.delete_many({})
    await db.health_records.insert_many(health_records)
    print(f"   ✅ Created {len(health_records)} health records")
    
    # ==================== APPOINTMENTS ====================
    print("\n📅 Creating appointments...")
    
    appointments = []
    for i, patient in enumerate(demo_patients):
        # Past appointment
        appointments.append({
            "id": str(uuid4()),
            "patient_id": patient["id"],
            "patient_name": patient["name"],
            "doctor_id": doctor_user["id"],
            "doctor_name": doctor_user["name"],
            "date": (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d"),
            "time": "10:00 AM",
            "type": "follow_up",
            "status": "completed",
            "notes": "Follow-up visit completed",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        })
        # Upcoming appointment
        appointments.append({
            "id": str(uuid4()),
            "patient_id": patient["id"],
            "patient_name": patient["name"],
            "doctor_id": doctor_user["id"],
            "doctor_name": doctor_user["name"],
            "date": (datetime.now(timezone.utc) + timedelta(days=3+i)).strftime("%Y-%m-%d"),
            "time": f"{9+i}:00 AM",
            "type": "checkup",
            "status": "scheduled",
            "notes": "Regular checkup",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.appointments.delete_many({})
    await db.appointments.insert_many(appointments)
    print(f"   ✅ Created {len(appointments)} appointments")
    
    # ==================== PRESCRIPTIONS ====================
    print("\n💊 Creating prescriptions...")
    
    prescriptions = []
    medications = [
        {"name": "Paracetamol", "dosage": "500mg", "frequency": "3 times daily", "duration": "5 days"},
        {"name": "Metformin", "dosage": "500mg", "frequency": "2 times daily", "duration": "30 days"},
        {"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily", "duration": "30 days"},
        {"name": "Azithromycin", "dosage": "500mg", "frequency": "Once daily", "duration": "3 days"}
    ]
    
    for i, patient in enumerate(demo_patients):
        prescriptions.append({
            "id": str(uuid4()),
            "patient_id": patient["id"],
            "patient_name": patient["name"],
            "doctor_id": doctor_user["id"],
            "doctor_name": doctor_user["name"],
            "medications": medications[i:i+2] if i < len(medications)-1 else [medications[0]],
            "diagnosis": patient.get("chronic_conditions", ["General illness"])[0] if patient.get("chronic_conditions") else "General illness",
            "notes": "Take medications as prescribed. Follow up if symptoms persist.",
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d"),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.prescriptions.delete_many({})
    await db.prescriptions.insert_many(prescriptions)
    print(f"   ✅ Created {len(prescriptions)} prescriptions")
    
    # ==================== LAB REPORTS ====================
    print("\n🔬 Creating lab reports...")
    
    lab_reports = []
    for i, patient in enumerate(demo_patients):
        lab_reports.append({
            "id": str(uuid4()),
            "patient_id": patient["id"],
            "patient_name": patient["name"],
            "doctor_id": doctor_user["id"],
            "test_type": "Complete Blood Count",
            "test_date": (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d"),
            "results": {
                "hemoglobin": {"value": 14.5, "unit": "g/dL", "normal_range": "12-16"},
                "rbc_count": {"value": 4.8, "unit": "million/uL", "normal_range": "4.5-5.5"},
                "wbc_count": {"value": 7500, "unit": "/uL", "normal_range": "4000-11000"},
                "platelet_count": {"value": 250000, "unit": "/uL", "normal_range": "150000-400000"}
            },
            "status": "completed",
            "ai_analysis": {
                "summary": "All parameters within normal range. No abnormalities detected.",
                "recommendations": ["Maintain healthy diet", "Regular exercise recommended"],
                "risk_factors": []
            },
            "lab_name": "Apollo Diagnostics",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.lab_reports.delete_many({})
    await db.lab_reports.insert_many(lab_reports)
    print(f"   ✅ Created {len(lab_reports)} lab reports")
    
    # ==================== SECURESPHERE - NETWORK DEVICES ====================
    print("\n🖥️ Creating network devices...")
    
    network_devices = [
        {"id": str(uuid4()), "name": "Core-Router-01", "device_type": "router", "ip_address": "192.168.1.1", "status": "active", "os": "RouterOS 7.x", "threats": 0, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "Main-Firewall", "device_type": "firewall", "ip_address": "192.168.1.2", "status": "active", "os": "pfSense 2.7", "threats": 0, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "App-Server-01", "device_type": "server", "ip_address": "192.168.1.100", "status": "active", "os": "Ubuntu 22.04 LTS", "threats": 0, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "App-Server-02", "device_type": "server", "ip_address": "192.168.1.101", "status": "active", "os": "Ubuntu 22.04 LTS", "threats": 1, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "DB-Server-Primary", "device_type": "server", "ip_address": "192.168.1.110", "status": "active", "os": "CentOS 8", "threats": 0, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "Workstation-Dev-01", "device_type": "workstation", "ip_address": "192.168.1.50", "status": "active", "os": "Windows 11 Pro", "threats": 0, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "IoT-Camera-Lobby", "device_type": "cctv", "ip_address": "192.168.1.200", "status": "active", "os": "Embedded Linux", "threats": 2, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "Smart-AC-Controller", "device_type": "white_goods", "ip_address": "192.168.1.201", "status": "warning", "os": "IoT OS", "threats": 1, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "Vehicle-ECU-Fleet01", "device_type": "automotive", "ip_address": "10.0.0.50", "status": "active", "os": "Automotive Linux", "threats": 0, "last_seen": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "name": "Mobile-Gateway-5G", "device_type": "mobile", "ip_address": "10.0.1.1", "status": "active", "os": "5G Core", "threats": 0, "last_seen": datetime.now(timezone.utc).isoformat()}
    ]
    
    await db.network_devices.delete_many({})
    await db.network_devices.insert_many(network_devices)
    print(f"   ✅ Created {len(network_devices)} network devices")
    
    # ==================== SECURESPHERE - SECURITY THREATS ====================
    print("\n⚠️ Creating security threats...")
    
    threats = [
        {"id": str(uuid4()), "threat_type": "intrusion", "severity": "critical", "title": "Brute Force Attack Detected", "source_ip": "185.220.101.45", "target_ip": "192.168.1.100", "status": "investigating", "description": "Multiple failed SSH login attempts from suspicious IP", "detected_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "threat_type": "malware", "severity": "high", "title": "Suspicious Binary Detected", "source_ip": None, "target_ip": "192.168.1.50", "status": "mitigated", "description": "Potential ransomware signature detected in download folder", "detected_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()},
        {"id": str(uuid4()), "threat_type": "ddos", "severity": "medium", "title": "Traffic Anomaly", "source_ip": "multiple", "target_ip": "192.168.1.1", "status": "resolved", "description": "Unusual spike in incoming traffic patterns", "detected_at": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()},
        {"id": str(uuid4()), "threat_type": "phishing", "severity": "high", "title": "Phishing Link Clicked", "source_ip": None, "target_ip": "192.168.1.50", "status": "detected", "description": "User clicked on suspicious email link", "detected_at": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()},
        {"id": str(uuid4()), "threat_type": "unauthorized_access", "severity": "critical", "title": "IoT Camera Access Attempt", "source_ip": "103.45.67.89", "target_ip": "192.168.1.200", "status": "investigating", "description": "Unauthorized access attempt on CCTV system", "detected_at": datetime.now(timezone.utc).isoformat()}
    ]
    
    await db.security_threats.delete_many({})
    await db.security_threats.insert_many(threats)
    print(f"   ✅ Created {len(threats)} security threats")
    
    # ==================== SECURESPHERE - ORGANIZATIONS ====================
    print("\n🏢 Creating organizations...")
    
    organizations = [
        {
            "id": "demo-enterprise-org",
            "name": "TechCorp India Pvt Ltd",
            "tier": "enterprise",
            "industry": "Technology",
            "size": "500-1000",
            "admin_email": "enterprise@infuse.demo",
            "settings": {"auto_enforcement": True, "alert_channels": ["email", "sms", "in_app"]},
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "demo-telco-org",
            "name": "Bharti Telecom Services",
            "tier": "telco_operator",
            "industry": "Telecommunications",
            "size": "10000+",
            "admin_email": "telco.admin@infuse.demo",
            "settings": {"auto_enforcement": True, "vran_enabled": True},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.organizations.delete_many({})
    await db.organizations.insert_many(organizations)
    print(f"   ✅ Created {len(organizations)} organizations")
    
    # ==================== SECURESPHERE - vRAN SESSIONS ====================
    print("\n📡 Creating vRAN sessions...")
    
    vran_sessions = [
        {"id": str(uuid4()), "user_id": admin_user["id"], "segment": "telco", "identifier": "+919876543210", "connection_type": "mobile_number", "status": "active", "threat_score": 15, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "user_id": admin_user["id"], "segment": "enterprise", "identifier": "192.168.1.0/24", "connection_type": "apn", "status": "active", "threat_score": 5, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "user_id": admin_user["id"], "segment": "automotive", "identifier": "VIN123456789", "connection_type": "mobile_number", "status": "active", "threat_score": 0, "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid4()), "user_id": admin_user["id"], "segment": "cctv", "identifier": "192.168.1.200", "connection_type": "apn", "status": "monitoring", "threat_score": 45, "created_at": datetime.now(timezone.utc).isoformat()}
    ]
    
    await db.vran_sessions.delete_many({})
    await db.vran_sessions.insert_many(vran_sessions)
    print(f"   ✅ Created {len(vran_sessions)} vRAN sessions")
    
    # ==================== SUMMARY ====================
    print("\n" + "="*60)
    print("🎉 COMPREHENSIVE DATA SEEDING COMPLETE!")
    print("="*60)
    print("\n📋 DEMO ACCOUNTS CREATED:")
    print("\n🏥 HEALTHTRACK PRO:")
    print("   Doctor 1: doctor.priya@infuse.demo / demo1234")
    print("   Doctor 2: doctor.amit@infuse.demo / demo1234")
    print("   Patient 1: patient.rahul@infuse.demo / demo1234")
    print("   Patient 2: patient.anita@infuse.demo / demo1234")
    print("\n🛡️ SECURESPHERE:")
    print("   Admin: admin@infuse.demo / admin1234")
    print("   Enterprise: enterprise@infuse.demo / demo1234")
    print("   Analyst: security.analyst@infuse.demo / demo1234")
    print("   Telco Admin: telco.admin@infuse.demo / demo1234")
    print("\n📊 DATA SEEDED:")
    print(f"   - {len(demo_users)} Users")
    print(f"   - {len(demo_patients)} Patients")
    print(f"   - {len(health_records)} Health Records")
    print(f"   - {len(appointments)} Appointments")
    print(f"   - {len(prescriptions)} Prescriptions")
    print(f"   - {len(lab_reports)} Lab Reports")
    print(f"   - {len(network_devices)} Network Devices")
    print(f"   - {len(threats)} Security Threats")
    print(f"   - {len(organizations)} Organizations")
    print(f"   - {len(vran_sessions)} vRAN Sessions")
    
    client.close()
    return True

if __name__ == "__main__":
    asyncio.run(seed_database())
