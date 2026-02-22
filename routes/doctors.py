"""
Doctor Directory Management System
Comprehensive API for managing doctors (Allopathic & Ayurvedic)
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from uuid import uuid4
import dependencies

router = APIRouter(prefix="/doctors", tags=["Doctor Directory"])

# Sample doctor data from open sources (anonymized/synthetic for demo)
SAMPLE_DOCTORS = [
    {
        "id": "doc_001",
        "name": "Dr. Priya Sharma",
        "type": "allopathic",
        "qualification": "MBBS, MD (Internal Medicine)",
        "registration_number": "DMC-2010-12345",
        "specialty": "General Medicine",
        "sub_specialties": ["Diabetes Management", "Hypertension"],
        "experience_years": 15,
        "languages": ["English", "Hindi"],
        "location": {
            "city": "Delhi",
            "state": "Delhi",
            "country": "India"
        },
        "consultation_fee": 500,
        "rating": 4.8,
        "total_ratings": 234,
        "verified": True,
        "available": True,
        "next_available_slot": "10:30 AM Today",
        "consultation_modes": ["video", "audio", "in_person"],
        "bio": "Experienced physician specializing in internal medicine with focus on chronic disease management.",
        "education": [
            {"degree": "MBBS", "institution": "AIIMS Delhi", "year": 2005},
            {"degree": "MD Internal Medicine", "institution": "AIIMS Delhi", "year": 2010}
        ]
    },
    {
        "id": "doc_002",
        "name": "Vaidya Ramesh Kumar",
        "type": "ayurvedic",
        "qualification": "BAMS, MD (Ayurveda - Panchakarma)",
        "registration_number": "CCIM-2008-67890",
        "specialty": "Panchakarma",
        "sub_specialties": ["Detoxification", "Stress Management", "Rejuvenation"],
        "experience_years": 20,
        "languages": ["English", "Hindi", "Sanskrit"],
        "location": {
            "city": "Jaipur",
            "state": "Rajasthan",
            "country": "India"
        },
        "consultation_fee": 400,
        "rating": 4.9,
        "total_ratings": 189,
        "verified": True,
        "available": True,
        "next_available_slot": "11:00 AM Today",
        "consultation_modes": ["video", "in_person"],
        "bio": "Expert in traditional Panchakarma therapies with 20 years of experience in holistic healing.",
        "education": [
            {"degree": "BAMS", "institution": "Gujarat Ayurved University", "year": 2000},
            {"degree": "MD Panchakarma", "institution": "BHU Varanasi", "year": 2005}
        ]
    },
    {
        "id": "doc_003",
        "name": "Dr. Arun Patel",
        "type": "allopathic",
        "qualification": "MBBS, DM (Cardiology)",
        "registration_number": "MMC-2006-54321",
        "specialty": "Cardiology",
        "sub_specialties": ["Interventional Cardiology", "Heart Failure", "Preventive Cardiology"],
        "experience_years": 18,
        "languages": ["English", "Hindi", "Gujarati"],
        "location": {
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India"
        },
        "consultation_fee": 800,
        "rating": 4.7,
        "total_ratings": 312,
        "verified": True,
        "available": False,
        "next_available_slot": "9:00 AM Tomorrow",
        "consultation_modes": ["video", "in_person"],
        "bio": "Leading cardiologist with expertise in complex cardiac interventions and preventive care.",
        "education": [
            {"degree": "MBBS", "institution": "Grant Medical College Mumbai", "year": 2002},
            {"degree": "MD Medicine", "institution": "KEM Hospital Mumbai", "year": 2006},
            {"degree": "DM Cardiology", "institution": "AIIMS Delhi", "year": 2009}
        ]
    },
    {
        "id": "doc_004",
        "name": "Vaidya Lakshmi Devi",
        "type": "ayurvedic",
        "qualification": "BAMS, PhD (Rasayana)",
        "registration_number": "CCIM-2003-11111",
        "specialty": "Rasayana Therapy",
        "sub_specialties": ["Anti-aging", "Immune Boosting", "Chronic Fatigue"],
        "experience_years": 25,
        "languages": ["English", "Hindi", "Telugu"],
        "location": {
            "city": "Hyderabad",
            "state": "Telangana",
            "country": "India"
        },
        "consultation_fee": 350,
        "rating": 4.9,
        "total_ratings": 156,
        "verified": True,
        "available": True,
        "next_available_slot": "2:00 PM Today",
        "consultation_modes": ["video", "audio", "in_person"],
        "bio": "Renowned expert in Rasayana (rejuvenation) therapy with research publications in international journals.",
        "education": [
            {"degree": "BAMS", "institution": "Dr. NTR University", "year": 1995},
            {"degree": "MD Rasayana", "institution": "RGUHS Bangalore", "year": 2000},
            {"degree": "PhD Rasayana", "institution": "BHU Varanasi", "year": 2005}
        ]
    },
    {
        "id": "doc_005",
        "name": "Dr. Sarah Khan",
        "type": "allopathic",
        "qualification": "MBBS, MD (Dermatology)",
        "registration_number": "KMC-2012-98765",
        "specialty": "Dermatology",
        "sub_specialties": ["Cosmetic Dermatology", "Hair Disorders", "Skin Allergies"],
        "experience_years": 12,
        "languages": ["English", "Hindi", "Urdu"],
        "location": {
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India"
        },
        "consultation_fee": 600,
        "rating": 4.6,
        "total_ratings": 278,
        "verified": True,
        "available": True,
        "next_available_slot": "3:30 PM Today",
        "consultation_modes": ["video", "in_person"],
        "bio": "Expert dermatologist specializing in skin conditions and cosmetic procedures.",
        "education": [
            {"degree": "MBBS", "institution": "St. Johns Medical College", "year": 2008},
            {"degree": "MD Dermatology", "institution": "NIMHANS Bangalore", "year": 2012}
        ]
    },
    {
        "id": "doc_006",
        "name": "Vaidya Sunil Sharma",
        "type": "ayurvedic",
        "qualification": "BAMS, MD (Kayachikitsa)",
        "registration_number": "CCIM-2010-22222",
        "specialty": "Kayachikitsa",
        "sub_specialties": ["Digestive Disorders", "Metabolic Conditions", "Lifestyle Diseases"],
        "experience_years": 16,
        "languages": ["English", "Hindi", "Tamil"],
        "location": {
            "city": "Chennai",
            "state": "Tamil Nadu",
            "country": "India"
        },
        "consultation_fee": 450,
        "rating": 4.8,
        "total_ratings": 201,
        "verified": True,
        "available": True,
        "next_available_slot": "4:00 PM Today",
        "consultation_modes": ["video", "audio", "in_person"],
        "bio": "Specialist in Kayachikitsa (internal medicine in Ayurveda) treating chronic lifestyle diseases.",
        "education": [
            {"degree": "BAMS", "institution": "Tamil Nadu Dr. MGR Medical University", "year": 2004},
            {"degree": "MD Kayachikitsa", "institution": "National Institute of Ayurveda Jaipur", "year": 2009}
        ]
    },
    {
        "id": "doc_007",
        "name": "Dr. Rajesh Verma",
        "type": "allopathic",
        "qualification": "MBBS, MS (Orthopedics)",
        "registration_number": "UPMC-2007-33333",
        "specialty": "Orthopedics",
        "sub_specialties": ["Joint Replacement", "Sports Medicine", "Spine Surgery"],
        "experience_years": 17,
        "languages": ["English", "Hindi"],
        "location": {
            "city": "Lucknow",
            "state": "Uttar Pradesh",
            "country": "India"
        },
        "consultation_fee": 700,
        "rating": 4.7,
        "total_ratings": 198,
        "verified": True,
        "available": True,
        "next_available_slot": "10:00 AM Tomorrow",
        "consultation_modes": ["video", "in_person"],
        "bio": "Expert orthopedic surgeon specializing in joint replacements and sports injuries.",
        "education": [
            {"degree": "MBBS", "institution": "KGMU Lucknow", "year": 2003},
            {"degree": "MS Orthopedics", "institution": "KGMU Lucknow", "year": 2007}
        ]
    },
    {
        "id": "doc_008",
        "name": "Vaidya Meera Nair",
        "type": "ayurvedic",
        "qualification": "BAMS, MD (Prasuti Tantra)",
        "registration_number": "CCIM-2011-44444",
        "specialty": "Women's Health",
        "sub_specialties": ["PCOS", "Infertility", "Menopause Management"],
        "experience_years": 14,
        "languages": ["English", "Hindi", "Malayalam"],
        "location": {
            "city": "Kochi",
            "state": "Kerala",
            "country": "India"
        },
        "consultation_fee": 400,
        "rating": 4.8,
        "total_ratings": 167,
        "verified": True,
        "available": True,
        "next_available_slot": "11:30 AM Today",
        "consultation_modes": ["video", "audio", "in_person"],
        "bio": "Ayurvedic gynecologist specializing in women's health issues using traditional Kerala treatments.",
        "education": [
            {"degree": "BAMS", "institution": "Kerala University", "year": 2006},
            {"degree": "MD Prasuti Tantra", "institution": "Govt. Ayurveda College Trivandrum", "year": 2011}
        ]
    }
]

# Specialties
ALLOPATHIC_SPECIALTIES = [
    "General Medicine", "Cardiology", "Dermatology", "Neurology", "Orthopedics",
    "Pediatrics", "Gynecology", "Psychiatry", "Ophthalmology", "ENT",
    "Gastroenterology", "Pulmonology", "Nephrology", "Oncology", "Endocrinology"
]

AYURVEDIC_SPECIALTIES = [
    "Panchakarma", "Rasayana Therapy", "Kayachikitsa", "Shalya Tantra",
    "Shalakya Tantra", "Prasuti Tantra", "Kaumarabhritya", "Agada Tantra",
    "Yoga Therapy", "Marma Therapy"
]

class DoctorSearch(BaseModel):
    query: Optional[str] = None
    doctor_type: Optional[str] = None  # allopathic, ayurvedic
    specialty: Optional[str] = None
    city: Optional[str] = None
    min_rating: Optional[float] = None
    max_fee: Optional[int] = None
    available_now: Optional[bool] = None
    consultation_mode: Optional[str] = None  # video, audio, in_person

class DoctorRating(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = None
    consultation_id: Optional[str] = None

class DoctorRegistration(BaseModel):
    name: str
    type: str = Field(..., pattern="^(allopathic|ayurvedic)$")
    qualification: str
    registration_number: str
    specialty: str
    experience_years: int
    languages: List[str]
    city: str
    state: str
    consultation_fee: int
    bio: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    # Extended branding fields for prescriptions
    clinic_name: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    clinic_logo: Optional[str] = None
    signature: Optional[str] = None
    header_text: Optional[str] = None
    footer_text: Optional[str] = None
    consultation_modes: Optional[List[str]] = ["video"]

@router.get("/")
async def list_doctors(
    doctor_type: Optional[str] = None,
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    min_rating: Optional[float] = None,
    available: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = Query(default="rating", enum=["rating", "experience", "fee", "name"]),
    limit: int = Query(default=20, le=100),
    offset: int = 0
):
    """List all doctors with optional filters"""
    db = await dependencies.get_database()
    
    # Try to get from database first
    query = {"status": {"$ne": "deleted"}}
    
    if doctor_type:
        # Support both field names
        query["$or"] = [{"type": doctor_type}, {"practice_type": doctor_type}]
    if specialty:
        query["$or"] = query.get("$or", []) + [
            {"specialty": specialty},
            {"specialization": specialty}
        ]
    if city:
        query["location.city"] = {"$regex": city, "$options": "i"}
    if min_rating:
        query["rating"] = {"$gte": min_rating}
    if available is not None:
        query["available"] = available
    if search:
        search_query = [
            {"name": {"$regex": search, "$options": "i"}},
            {"specialty": {"$regex": search, "$options": "i"}},
            {"specialization": {"$regex": search, "$options": "i"}},
            {"qualification": {"$regex": search, "$options": "i"}}
        ]
        if "$or" in query:
            query["$and"] = [{"$or": query.pop("$or")}, {"$or": search_query}]
        else:
            query["$or"] = search_query
    
    # Get doctors from database
    db_doctors = await db.doctors.find(query, {"_id": 0}).skip(offset).limit(limit).to_list(limit)
    
    # Normalize doctor fields from DB
    for doc in db_doctors:
        if "practice_type" in doc and "type" not in doc:
            doc["type"] = doc["practice_type"]
        if "specialization" in doc and "specialty" not in doc:
            doc["specialty"] = doc["specialization"]
    
    # If no doctors in DB or very few, merge with sample data
    if len(db_doctors) < 3:
        doctors = SAMPLE_DOCTORS.copy()
        
        # Apply filters to sample data
        if doctor_type:
            doctors = [d for d in doctors if d.get("type") == doctor_type]
        if specialty:
            doctors = [d for d in doctors if d.get("specialty", "").lower() == specialty.lower()]
        if city:
            doctors = [d for d in doctors if city.lower() in d.get("location", {}).get("city", "").lower()]
        if min_rating:
            doctors = [d for d in doctors if d.get("rating", 0) >= min_rating]
        if available is not None:
            doctors = [d for d in doctors if d.get("available") == available]
        if search:
            search_lower = search.lower()
            doctors = [d for d in doctors if search_lower in d.get("name", "").lower() or search_lower in d.get("specialty", "").lower()]
        
        # Merge DB doctors with sample doctors (avoid duplicates)
        db_doctor_ids = {d.get("id") for d in db_doctors}
        for sample_doc in doctors:
            if sample_doc["id"] not in db_doctor_ids:
                db_doctors.append(sample_doc)
        
        # Sort
        if sort_by == "rating":
            db_doctors.sort(key=lambda x: x.get("rating", 0), reverse=True)
        elif sort_by == "experience":
            db_doctors.sort(key=lambda x: x.get("experience_years", 0), reverse=True)
        elif sort_by == "fee":
            db_doctors.sort(key=lambda x: x.get("consultation_fee", 0))
        elif sort_by == "name":
            db_doctors.sort(key=lambda x: x.get("name", ""))
        
        result_doctors = db_doctors[offset:offset+limit]
        allopathic_count = len([d for d in db_doctors if d.get("type") == "allopathic"])
        ayurvedic_count = len([d for d in db_doctors if d.get("type") == "ayurvedic"])
        total = len(db_doctors)
    else:
        result_doctors = db_doctors
        total = await db.doctors.count_documents(query)
        allopathic_count = await db.doctors.count_documents({**query, "$or": [{"type": "allopathic"}, {"practice_type": "allopathic"}]})
        ayurvedic_count = await db.doctors.count_documents({**query, "$or": [{"type": "ayurvedic"}, {"practice_type": "ayurvedic"}]})
    
    return {
        "total": total,
        "allopathic_count": allopathic_count,
        "ayurvedic_count": ayurvedic_count,
        "offset": offset,
        "limit": limit,
        "doctors": result_doctors
    }

@router.get("/specialties")
async def get_specialties():
    """Get all available specialties"""
    return {
        "allopathic": ALLOPATHIC_SPECIALTIES,
        "ayurvedic": AYURVEDIC_SPECIALTIES
    }

@router.get("/{doctor_id}")
async def get_doctor(doctor_id: str):
    """Get doctor details by ID"""
    db = await dependencies.get_database()
    
    # Try database first
    doctor = await db.doctors.find_one({"id": doctor_id}, {"_id": 0})
    
    if not doctor:
        # Check sample data
        doctor = next((d for d in SAMPLE_DOCTORS if d["id"] == doctor_id), None)
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Get reviews
    reviews = await db.doctor_reviews.find(
        {"doctor_id": doctor_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    doctor["reviews"] = reviews
    
    return doctor

@router.get("/{doctor_id}/reviews")
async def get_doctor_reviews(
    doctor_id: str,
    limit: int = Query(default=20, le=50),
    offset: int = 0
):
    """Get reviews for a doctor"""
    db = await dependencies.get_database()
    
    reviews = await db.doctor_reviews.find(
        {"doctor_id": doctor_id, "status": "approved"},
        {"_id": 0}
    ).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    
    total = await db.doctor_reviews.count_documents({"doctor_id": doctor_id, "status": "approved"})
    
    # Calculate rating distribution
    pipeline = [
        {"$match": {"doctor_id": doctor_id, "status": "approved"}},
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}}
    ]
    distribution = await db.doctor_reviews.aggregate(pipeline).to_list(10)
    rating_dist = {str(i): 0 for i in range(1, 6)}
    for d in distribution:
        rating_dist[str(d["_id"])] = d["count"]
    
    return {
        "doctor_id": doctor_id,
        "total_reviews": total,
        "rating_distribution": rating_dist,
        "reviews": reviews
    }

@router.post("/{doctor_id}/rate")
async def rate_doctor(doctor_id: str, rating_data: DoctorRating):
    """Rate a doctor (requires authentication in production)"""
    db = await dependencies.get_database()
    
    # Verify doctor exists
    doctor = await db.doctors.find_one({"id": doctor_id})
    if not doctor:
        # Check sample data
        doctor = next((d for d in SAMPLE_DOCTORS if d["id"] == doctor_id), None)
        if doctor:
            # Add to database
            await db.doctors.insert_one({**doctor, "status": "active"})
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Create review
    review = {
        "id": str(uuid4()),
        "doctor_id": doctor_id,
        "rating": rating_data.rating,
        "review": rating_data.review,
        "consultation_id": rating_data.consultation_id,
        "user_name": "Verified Patient",  # In production, get from auth
        "status": "approved",  # In production, moderate first
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.doctor_reviews.insert_one(review)
    
    # Update doctor's average rating
    pipeline = [
        {"$match": {"doctor_id": doctor_id, "status": "approved"}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    result = await db.doctor_reviews.aggregate(pipeline).to_list(1)
    
    if result:
        new_rating = round(result[0]["avg_rating"], 1)
        new_count = result[0]["count"]
        await db.doctors.update_one(
            {"id": doctor_id},
            {"$set": {"rating": new_rating, "total_ratings": new_count}}
        )
    
    return {
        "message": "Rating submitted successfully",
        "review_id": review["id"]
    }

@router.post("/register")
async def register_doctor(doctor_data: DoctorRegistration):
    """Register a new doctor (self-registration) - pending admin approval"""
    db = await dependencies.get_database()
    
    # Check if registration number already exists
    existing = await db.doctors.find_one({"registration_number": doctor_data.registration_number})
    if existing:
        raise HTTPException(status_code=400, detail="Doctor with this registration number already exists")
    
    doctor = {
        "id": f"doc_{str(uuid4())[:8]}",
        "name": doctor_data.name,
        "type": doctor_data.type,
        "qualification": doctor_data.qualification,
        "registration_number": doctor_data.registration_number,
        "specialty": doctor_data.specialty,
        "sub_specialties": [],
        "experience_years": doctor_data.experience_years,
        "languages": doctor_data.languages,
        "location": {
            "city": doctor_data.city,
            "state": doctor_data.state,
            "country": "India"
        },
        "consultation_fee": doctor_data.consultation_fee,
        "rating": 0,
        "total_ratings": 0,
        "verified": False,  # Needs verification
        "verification_status": "pending",
        "available": True,
        "next_available_slot": None,
        "consultation_modes": doctor_data.consultation_modes or ["video"],
        "bio": doctor_data.bio,
        "phone": doctor_data.phone,
        "email": doctor_data.email,
        # Branding fields for prescriptions
        "clinic_name": doctor_data.clinic_name,
        "address": doctor_data.address,
        "pincode": doctor_data.pincode,
        "clinic_logo": doctor_data.clinic_logo,
        "signature": doctor_data.signature,
        "header_text": doctor_data.header_text,
        "footer_text": doctor_data.footer_text,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.doctors.insert_one(doctor)
    doctor.pop("_id", None)
    
    return {
        "message": "Doctor registration submitted. Verification pending.",
        "doctor_id": doctor["id"],
        "verification_status": "pending",
        "doctor": doctor
    }

@router.put("/{doctor_id}/verify")
async def verify_doctor(doctor_id: str, verified: bool = True, notes: Optional[str] = None):
    """Verify a doctor (admin only in production)"""
    db = await dependencies.get_database()
    
    result = await db.doctors.update_one(
        {"id": doctor_id},
        {"$set": {
            "verified": verified,
            "verification_status": "verified" if verified else "rejected",
            "verification_notes": notes,
            "verified_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    return {"message": f"Doctor {'verified' if verified else 'rejected'}", "doctor_id": doctor_id}

@router.get("/stats/overview")
async def get_doctor_stats():
    """Get overall doctor directory statistics"""
    db = await dependencies.get_database()
    
    total_doctors = await db.doctors.count_documents({"status": "active"})
    allopathic_count = await db.doctors.count_documents({"status": "active", "type": "allopathic"})
    ayurvedic_count = await db.doctors.count_documents({"status": "active", "type": "ayurvedic"})
    verified_count = await db.doctors.count_documents({"status": "active", "verified": True})
    pending_verification = await db.doctors.count_documents({"verification_status": "pending"})
    
    # If no doctors in DB, use sample data counts
    if total_doctors == 0:
        total_doctors = len(SAMPLE_DOCTORS)
        allopathic_count = len([d for d in SAMPLE_DOCTORS if d["type"] == "allopathic"])
        ayurvedic_count = len([d for d in SAMPLE_DOCTORS if d["type"] == "ayurvedic"])
        verified_count = len([d for d in SAMPLE_DOCTORS if d["verified"]])
    
    return {
        "total_doctors": total_doctors,
        "allopathic_doctors": allopathic_count,
        "ayurvedic_doctors": ayurvedic_count,
        "verified_doctors": verified_count,
        "pending_verification": pending_verification,
        "data_source": "database" if total_doctors > len(SAMPLE_DOCTORS) else "sample"
    }
