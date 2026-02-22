"""
Doctor Data Seeding Script
Populates the database with realistic doctor data based on:
- NMC (National Medical Commission) for Allopathic doctors
- AYUSH/CCIM registry patterns for Ayurvedic doctors
- Real Indian medical council registration patterns
"""

import asyncio
import random
from datetime import datetime, timezone
from uuid import uuid4
import motor.motor_asyncio
import os

# Configuration
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/?authSource=admin")
DB_NAME = os.environ.get("DB_NAME", "healthtrack_pro")

# Indian cities and states
CITIES = [
    {"city": "Mumbai", "state": "Maharashtra"},
    {"city": "Delhi", "state": "Delhi"},
    {"city": "Bangalore", "state": "Karnataka"},
    {"city": "Chennai", "state": "Tamil Nadu"},
    {"city": "Kolkata", "state": "West Bengal"},
    {"city": "Hyderabad", "state": "Telangana"},
    {"city": "Pune", "state": "Maharashtra"},
    {"city": "Ahmedabad", "state": "Gujarat"},
    {"city": "Jaipur", "state": "Rajasthan"},
    {"city": "Lucknow", "state": "Uttar Pradesh"},
    {"city": "Kochi", "state": "Kerala"},
    {"city": "Chandigarh", "state": "Punjab"},
    {"city": "Bhopal", "state": "Madhya Pradesh"},
    {"city": "Patna", "state": "Bihar"},
    {"city": "Guwahati", "state": "Assam"},
    {"city": "Thiruvananthapuram", "state": "Kerala"},
    {"city": "Indore", "state": "Madhya Pradesh"},
    {"city": "Nagpur", "state": "Maharashtra"},
    {"city": "Coimbatore", "state": "Tamil Nadu"},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh"},
]

# State Medical Council prefixes (realistic patterns from NMC)
STATE_COUNCIL_PREFIXES = {
    "Maharashtra": "MMC",
    "Delhi": "DMC",
    "Karnataka": "KMC",
    "Tamil Nadu": "TNMC",
    "West Bengal": "WBMC",
    "Telangana": "TSMC",
    "Gujarat": "GMC",
    "Rajasthan": "RMC",
    "Uttar Pradesh": "UPMC",
    "Kerala": "KSMC",
    "Punjab": "PMC",
    "Madhya Pradesh": "MPMC",
    "Bihar": "BMC",
    "Assam": "AMC",
    "Andhra Pradesh": "APMC",
}

# Allopathic specialties with qualifications
ALLOPATHIC_SPECIALTIES = {
    "General Medicine": {
        "qualifications": ["MBBS", "MBBS, MD (Internal Medicine)", "MBBS, DNB (Medicine)"],
        "institutions": ["AIIMS Delhi", "JIPMER", "CMC Vellore", "PGIMER Chandigarh", "KEM Mumbai"]
    },
    "Cardiology": {
        "qualifications": ["MBBS, MD, DM (Cardiology)", "MBBS, DNB (Cardiology)"],
        "institutions": ["AIIMS Delhi", "GB Pant Hospital", "Medanta", "Narayana Hrudayalaya"]
    },
    "Dermatology": {
        "qualifications": ["MBBS, MD (Dermatology)", "MBBS, DVD", "MBBS, DNB (Dermatology)"],
        "institutions": ["AIIMS Delhi", "Safdarjung Hospital", "LTMG Hospital", "JIPMER"]
    },
    "Neurology": {
        "qualifications": ["MBBS, MD, DM (Neurology)", "MBBS, DNB (Neurology)"],
        "institutions": ["NIMHANS Bangalore", "AIIMS Delhi", "SCTIMST Trivandrum"]
    },
    "Orthopedics": {
        "qualifications": ["MBBS, MS (Orthopedics)", "MBBS, DNB (Orthopedics)"],
        "institutions": ["AIIMS Delhi", "CMC Vellore", "PGIMER Chandigarh", "KEM Mumbai"]
    },
    "Pediatrics": {
        "qualifications": ["MBBS, MD (Pediatrics)", "MBBS, DNB (Pediatrics)"],
        "institutions": ["AIIMS Delhi", "Kanchi Kamakoti CHILDS Trust", "Rainbow Hospital", "CMC Vellore"]
    },
    "Gynecology": {
        "qualifications": ["MBBS, MS (Obstetrics & Gynecology)", "MBBS, DNB (OB-GYN)", "MBBS, DGO"],
        "institutions": ["AIIMS Delhi", "Safdarjung Hospital", "CMC Vellore", "LHMC Delhi"]
    },
    "Psychiatry": {
        "qualifications": ["MBBS, MD (Psychiatry)", "MBBS, DNB (Psychiatry)"],
        "institutions": ["NIMHANS Bangalore", "AIIMS Delhi", "CIP Ranchi", "LGBRIMH Tezpur"]
    },
    "Ophthalmology": {
        "qualifications": ["MBBS, MS (Ophthalmology)", "MBBS, DNB (Ophthalmology)", "MBBS, DO"],
        "institutions": ["AIIMS Delhi", "Sankara Nethralaya", "LV Prasad Eye Institute", "PGIMER"]
    },
    "ENT": {
        "qualifications": ["MBBS, MS (ENT)", "MBBS, DNB (ENT)"],
        "institutions": ["AIIMS Delhi", "Safdarjung Hospital", "CMC Vellore", "PGIMER"]
    },
    "Gastroenterology": {
        "qualifications": ["MBBS, MD, DM (Gastroenterology)", "MBBS, DNB (Gastroenterology)"],
        "institutions": ["AIIMS Delhi", "AIG Hyderabad", "SGPGI Lucknow", "CMC Vellore"]
    },
    "Pulmonology": {
        "qualifications": ["MBBS, MD (Pulmonary Medicine)", "MBBS, DNB (Pulmonology)"],
        "institutions": ["AIIMS Delhi", "VPCI Delhi", "PGIMER Chandigarh", "CMC Vellore"]
    },
    "Nephrology": {
        "qualifications": ["MBBS, MD, DM (Nephrology)", "MBBS, DNB (Nephrology)"],
        "institutions": ["AIIMS Delhi", "CMC Vellore", "PGIMER", "SCTIMST"]
    },
    "Oncology": {
        "qualifications": ["MBBS, MD, DM (Medical Oncology)", "MBBS, DNB (Oncology)"],
        "institutions": ["Tata Memorial Hospital", "AIIMS Delhi", "Rajiv Gandhi Cancer Institute", "CMC Vellore"]
    },
    "Endocrinology": {
        "qualifications": ["MBBS, MD, DM (Endocrinology)", "MBBS, DNB (Endocrinology)"],
        "institutions": ["AIIMS Delhi", "PGIMER", "CMC Vellore", "SGPGI Lucknow"]
    },
}

# Ayurvedic specialties (CCIM recognized)
AYURVEDIC_SPECIALTIES = {
    "Panchakarma": {
        "qualifications": ["BAMS", "BAMS, MD (Ayurveda - Panchakarma)", "BAMS, PhD (Panchakarma)"],
        "institutions": ["Gujarat Ayurved University", "BHU Varanasi", "NIA Jaipur", "AVS Kottakkal"]
    },
    "Rasayana Therapy": {
        "qualifications": ["BAMS", "BAMS, MD (Ayurveda - Rasayana)", "BAMS, PhD (Rasayana)"],
        "institutions": ["RGUHS Bangalore", "Gujarat Ayurved University", "BHU Varanasi", "IPGT&RA Jamnagar"]
    },
    "Kayachikitsa": {
        "qualifications": ["BAMS", "BAMS, MD (Kayachikitsa)", "BAMS, PhD (Kayachikitsa)"],
        "institutions": ["NIA Jaipur", "BHU Varanasi", "Kerala University", "Gujarat Ayurved University"]
    },
    "Shalya Tantra": {
        "qualifications": ["BAMS", "BAMS, MS (Shalya Tantra)"],
        "institutions": ["BHU Varanasi", "Gujarat Ayurved University", "NIA Jaipur"]
    },
    "Shalakya Tantra": {
        "qualifications": ["BAMS", "BAMS, MS (Shalakya Tantra)"],
        "institutions": ["BHU Varanasi", "Gujarat Ayurved University", "IPGT&RA Jamnagar"]
    },
    "Prasuti Tantra": {
        "qualifications": ["BAMS", "BAMS, MD (Prasuti Tantra)", "BAMS, MS (Prasuti Tantra)"],
        "institutions": ["BHU Varanasi", "Kerala University", "Gujarat Ayurved University"]
    },
    "Kaumarabhritya": {
        "qualifications": ["BAMS", "BAMS, MD (Kaumarabhritya)"],
        "institutions": ["NIA Jaipur", "BHU Varanasi", "Gujarat Ayurved University"]
    },
    "Agada Tantra": {
        "qualifications": ["BAMS", "BAMS, MD (Agada Tantra)"],
        "institutions": ["BHU Varanasi", "Gujarat Ayurved University", "SDM Udupi"]
    },
    "Yoga Therapy": {
        "qualifications": ["BAMS, CYI", "BAMS, MD (Yoga & Rehabilitation)", "BNYS"],
        "institutions": ["SVYASA Bangalore", "Kaivalyadhama Lonavala", "Bihar School of Yoga"]
    },
    "Marma Therapy": {
        "qualifications": ["BAMS", "BAMS, Marma Specialist Certificate"],
        "institutions": ["AVS Kottakkal", "Kerala Ayurveda Academy", "IPGT&RA Jamnagar"]
    },
}

# Indian names database
FIRST_NAMES_MALE = [
    "Arun", "Vikram", "Rajesh", "Sanjay", "Deepak", "Sunil", "Ramesh", "Pradeep", "Manoj", "Ashok",
    "Karthik", "Venkatesh", "Prakash", "Mohan", "Ganesh", "Suresh", "Dinesh", "Harish", "Girish", "Satish",
    "Arvind", "Vijay", "Ravi", "Anand", "Ajay", "Amit", "Rahul", "Nikhil", "Sachin", "Varun"
]

FIRST_NAMES_FEMALE = [
    "Priya", "Anjali", "Sunita", "Rekha", "Kavitha", "Lakshmi", "Meena", "Anita", "Pooja", "Neha",
    "Deepa", "Shobha", "Seema", "Radha", "Sarala", "Usha", "Vani", "Padma", "Geeta", "Maya",
    "Shruthi", "Divya", "Swati", "Renu", "Archana", "Pallavi", "Sneha", "Ritika", "Nandini", "Aarti"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Kumar", "Reddy", "Nair", "Iyer", "Menon", "Rao",
    "Gupta", "Agarwal", "Joshi", "Pillai", "Krishnan", "Murthy", "Hegde", "Kulkarni", "Deshmukh", "Patil",
    "Choudhary", "Mishra", "Tripathi", "Pandey", "Bhat", "Kaur", "Devi", "Khan", "Chatterjee", "Banerjee"
]

AYURVEDIC_TITLES = ["Vaidya", "Dr.", "Acharya"]

def generate_registration_number(state: str, year: int, is_ayurvedic: bool = False) -> str:
    """Generate realistic registration number based on medical council patterns"""
    if is_ayurvedic:
        return f"CCIM-{year}-{random.randint(10000, 99999)}"
    prefix = STATE_COUNCIL_PREFIXES.get(state, "NMC")
    return f"{prefix}-{year}-{random.randint(10000, 99999)}"

def generate_allopathic_doctor() -> dict:
    """Generate a realistic allopathic doctor profile"""
    is_female = random.random() < 0.35
    first_name = random.choice(FIRST_NAMES_FEMALE if is_female else FIRST_NAMES_MALE)
    last_name = random.choice(LAST_NAMES)
    
    location = random.choice(CITIES)
    specialty = random.choice(list(ALLOPATHIC_SPECIALTIES.keys()))
    spec_data = ALLOPATHIC_SPECIALTIES[specialty]
    qualification = random.choice(spec_data["qualifications"])
    institution = random.choice(spec_data["institutions"])
    
    experience_years = random.randint(5, 30)
    reg_year = 2024 - experience_years - random.randint(0, 3)
    
    # Languages based on location
    languages = ["English", "Hindi"]
    if location["state"] == "Karnataka":
        languages.append("Kannada")
    elif location["state"] == "Tamil Nadu":
        languages.append("Tamil")
    elif location["state"] == "Kerala":
        languages.append("Malayalam")
    elif location["state"] == "West Bengal":
        languages.append("Bengali")
    elif location["state"] == "Gujarat":
        languages.append("Gujarati")
    elif location["state"] == "Maharashtra":
        languages.append("Marathi")
    elif location["state"] == "Telangana":
        languages.append("Telugu")
    
    # Consultation fee based on experience and specialty
    base_fee = 400 if specialty == "General Medicine" else 600
    fee = base_fee + (experience_years * 20) + random.randint(-100, 200)
    fee = max(300, min(2000, fee))  # Cap between 300-2000
    
    # Rating based on experience (more experienced tend to have higher ratings)
    base_rating = 4.0 + (experience_years / 50)
    rating = round(min(5.0, base_rating + random.uniform(-0.3, 0.5)), 1)
    
    return {
        "id": f"doc_allo_{str(uuid4())[:8]}",
        "name": f"Dr. {first_name} {last_name}",
        "type": "allopathic",
        "gender": "female" if is_female else "male",
        "qualification": qualification,
        "registration_number": generate_registration_number(location["state"], reg_year),
        "specialty": specialty,
        "sub_specialties": [],
        "experience_years": experience_years,
        "languages": languages,
        "location": {
            "city": location["city"],
            "state": location["state"],
            "country": "India"
        },
        "consultation_fee": fee,
        "rating": rating,
        "total_ratings": random.randint(50, 500),
        "verified": True,
        "verification_status": "verified",
        "available": random.random() > 0.2,
        "next_available_slot": random.choice([
            "10:00 AM Today", "11:30 AM Today", "2:00 PM Today", 
            "4:30 PM Today", "9:00 AM Tomorrow", "10:30 AM Tomorrow"
        ]) if random.random() > 0.3 else "Contact for availability",
        "consultation_modes": random.sample(["video", "audio", "in_person"], k=random.randint(1, 3)),
        "bio": f"Experienced {specialty.lower()} specialist with {experience_years} years of clinical practice. Trained at {institution}.",
        "education": [
            {"degree": "MBBS", "institution": institution, "year": reg_year}
        ],
        "status": "active",
        "source": "NMC_Registry",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

def generate_ayurvedic_doctor() -> dict:
    """Generate a realistic ayurvedic doctor profile"""
    is_female = random.random() < 0.30
    first_name = random.choice(FIRST_NAMES_FEMALE if is_female else FIRST_NAMES_MALE)
    last_name = random.choice(LAST_NAMES)
    
    title = random.choice(AYURVEDIC_TITLES)
    
    location = random.choice(CITIES)
    specialty = random.choice(list(AYURVEDIC_SPECIALTIES.keys()))
    spec_data = AYURVEDIC_SPECIALTIES[specialty]
    qualification = random.choice(spec_data["qualifications"])
    institution = random.choice(spec_data["institutions"])
    
    experience_years = random.randint(5, 35)
    reg_year = 2024 - experience_years - random.randint(0, 3)
    
    # Languages
    languages = ["English", "Hindi"]
    if location["state"] == "Kerala":
        languages.extend(["Malayalam", "Sanskrit"])
    elif location["state"] == "Karnataka":
        languages.extend(["Kannada", "Sanskrit"])
    elif location["state"] == "Gujarat":
        languages.extend(["Gujarati", "Sanskrit"])
    else:
        languages.append("Sanskrit")
    
    # Consultation fee (Ayurvedic typically lower)
    base_fee = 300
    fee = base_fee + (experience_years * 15) + random.randint(-50, 150)
    fee = max(200, min(1500, fee))
    
    # Rating
    base_rating = 4.2 + (experience_years / 60)
    rating = round(min(5.0, base_rating + random.uniform(-0.2, 0.4)), 1)
    
    return {
        "id": f"doc_ayur_{str(uuid4())[:8]}",
        "name": f"{title} {first_name} {last_name}",
        "type": "ayurvedic",
        "gender": "female" if is_female else "male",
        "qualification": qualification,
        "registration_number": generate_registration_number(location["state"], reg_year, is_ayurvedic=True),
        "specialty": specialty,
        "sub_specialties": [],
        "experience_years": experience_years,
        "languages": languages,
        "location": {
            "city": location["city"],
            "state": location["state"],
            "country": "India"
        },
        "consultation_fee": fee,
        "rating": rating,
        "total_ratings": random.randint(30, 300),
        "verified": True,
        "verification_status": "verified",
        "available": random.random() > 0.15,
        "next_available_slot": random.choice([
            "10:00 AM Today", "11:30 AM Today", "2:00 PM Today", 
            "4:30 PM Today", "9:00 AM Tomorrow", "10:30 AM Tomorrow"
        ]) if random.random() > 0.25 else "Contact for availability",
        "consultation_modes": random.sample(["video", "audio", "in_person"], k=random.randint(1, 3)),
        "bio": f"Traditional {specialty.lower()} practitioner with {experience_years} years of experience in holistic healing. Trained at {institution}.",
        "education": [
            {"degree": "BAMS", "institution": institution, "year": reg_year}
        ],
        "status": "active",
        "source": "CCIM_Registry",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

async def seed_doctors(allopathic_count: int = 50, ayurvedic_count: int = 50):
    """Seed the database with doctor data"""
    print(f"Connecting to MongoDB at {MONGO_URL}...")
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Check existing count
    existing_count = await db.doctors.count_documents({})
    print(f"Existing doctors in database: {existing_count}")
    
    # Generate allopathic doctors
    print(f"Generating {allopathic_count} allopathic doctors...")
    allopathic_doctors = [generate_allopathic_doctor() for _ in range(allopathic_count)]
    
    # Generate ayurvedic doctors
    print(f"Generating {ayurvedic_count} ayurvedic doctors...")
    ayurvedic_doctors = [generate_ayurvedic_doctor() for _ in range(ayurvedic_count)]
    
    all_doctors = allopathic_doctors + ayurvedic_doctors
    
    # Clear existing seeded data (keep manually added)
    result = await db.doctors.delete_many({"source": {"$in": ["NMC_Registry", "CCIM_Registry"]}})
    print(f"Cleared {result.deleted_count} previously seeded doctors")
    
    # Insert new data
    if all_doctors:
        result = await db.doctors.insert_many(all_doctors)
        print(f"Inserted {len(result.inserted_ids)} doctors")
    
    # Create indexes
    print("Creating/updating indexes...")
    await db.doctors.create_index([("type", 1)])
    await db.doctors.create_index([("specialty", 1)])
    await db.doctors.create_index([("location.city", 1)])
    await db.doctors.create_index([("location.state", 1)])
    await db.doctors.create_index([("rating", -1)])
    await db.doctors.create_index([("verified", 1)])
    await db.doctors.create_index([("name", "text"), ("specialty", "text"), ("qualification", "text")])
    
    # Summary
    final_allopathic = await db.doctors.count_documents({"type": "allopathic"})
    final_ayurvedic = await db.doctors.count_documents({"type": "ayurvedic"})
    final_total = await db.doctors.count_documents({})
    
    print("\n=== Seeding Complete ===")
    print(f"Total Doctors: {final_total}")
    print(f"  - Allopathic: {final_allopathic}")
    print(f"  - Ayurvedic: {final_ayurvedic}")
    print(f"  - Verified: {await db.doctors.count_documents({'verified': True})}")
    
    # Sample of cities
    pipeline = [
        {"$group": {"_id": "$location.city", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    cities = await db.doctors.aggregate(pipeline).to_list(10)
    print("\nTop cities by doctor count:")
    for c in cities:
        print(f"  - {c['_id']}: {c['count']}")
    
    client.close()
    return {"total": final_total, "allopathic": final_allopathic, "ayurvedic": final_ayurvedic}

if __name__ == "__main__":
    asyncio.run(seed_doctors(allopathic_count=50, ayurvedic_count=50))
