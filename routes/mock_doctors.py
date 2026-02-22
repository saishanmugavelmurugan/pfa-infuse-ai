"""Mock doctor database for development.
In production, this should be replaced with real database or API."""

from typing import List, Dict
import random

# Mock doctor data with realistic Indian names and specialties
MOCK_DOCTORS = [
    # Cardiologists
    {"id": "doc-001", "name": "Dr. Rajesh Kumar", "specialty": "Cardiologist", "rating": 4.9, "experience_years": 25, "qualifications": "MBBS, MD (Cardiology), DM (Cardiology)", "hospital": "Apollo Hospital", "city": "Delhi", "consultation_fee": 1500, "available": True, "languages": ["English", "Hindi"], "verified": True},
    {"id": "doc-002", "name": "Dr. Priya Sharma", "specialty": "Cardiologist", "rating": 4.8, "experience_years": 18, "qualifications": "MBBS, MD, DM (Cardiology)", "hospital": "Fortis Hospital", "city": "Mumbai", "consultation_fee": 1200, "available": True, "languages": ["English", "Hindi", "Marathi"], "verified": True},
    
    # Endocrinologists
    {"id": "doc-003", "name": "Dr. Anil Patel", "specialty": "Endocrinologist", "rating": 4.9, "experience_years": 20, "qualifications": "MBBS, MD (Medicine), DM (Endocrinology)", "hospital": "Max Hospital", "city": "Delhi", "consultation_fee": 1300, "available": True, "languages": ["English", "Hindi", "Gujarati"], "verified": True},
    {"id": "doc-004", "name": "Dr. Meera Reddy", "specialty": "Endocrinologist", "rating": 4.7, "experience_years": 15, "qualifications": "MBBS, MD, DM (Endocrinology)", "hospital": "Yashoda Hospital", "city": "Hyderabad", "consultation_fee": 1000, "available": True, "languages": ["English", "Telugu", "Hindi"], "verified": True},
    
    # General Physicians
    {"id": "doc-005", "name": "Dr. Vikram Singh", "specialty": "General Physician", "rating": 4.8, "experience_years": 12, "qualifications": "MBBS, MD (Medicine)", "hospital": "Medanta Hospital", "city": "Gurgaon", "consultation_fee": 800, "available": True, "languages": ["English", "Hindi", "Punjabi"], "verified": True},
    {"id": "doc-006", "name": "Dr. Sunita Desai", "specialty": "General Physician", "rating": 4.6, "experience_years": 10, "qualifications": "MBBS, MD", "hospital": "Lilavati Hospital", "city": "Mumbai", "consultation_fee": 600, "available": True, "languages": ["English", "Hindi", "Marathi"], "verified": True},
    
    # Nephrologists
    {"id": "doc-007", "name": "Dr. Ramesh Iyer", "specialty": "Nephrologist", "rating": 4.9, "experience_years": 22, "qualifications": "MBBS, MD, DM (Nephrology)", "hospital": "AIIMS", "city": "Delhi", "consultation_fee": 1400, "available": True, "languages": ["English", "Hindi", "Tamil"], "verified": True},
    {"id": "doc-008", "name": "Dr. Kavita Nair", "specialty": "Nephrologist", "rating": 4.7, "experience_years": 16, "qualifications": "MBBS, MD, DM (Nephrology)", "hospital": "Manipal Hospital", "city": "Bangalore", "consultation_fee": 1100, "available": True, "languages": ["English", "Kannada", "Hindi"], "verified": True},
    
    # Gastroenterologists
    {"id": "doc-009", "name": "Dr. Suresh Menon", "specialty": "Gastroenterologist", "rating": 4.8, "experience_years": 19, "qualifications": "MBBS, MD, DM (Gastroenterology)", "hospital": "CMC Vellore", "city": "Vellore", "consultation_fee": 1200, "available": True, "languages": ["English", "Tamil", "Malayalam"], "verified": True},
    {"id": "doc-010", "name": "Dr. Anjali Gupta", "specialty": "Gastroenterologist", "rating": 4.6, "experience_years": 14, "qualifications": "MBBS, MD, DM", "hospital": "Sir Ganga Ram Hospital", "city": "Delhi", "consultation_fee": 1000, "available": True, "languages": ["English", "Hindi"], "verified": True},
    
    # Pulmonologists
    {"id": "doc-011", "name": "Dr. Ashok Verma", "specialty": "Pulmonologist", "rating": 4.9, "experience_years": 21, "qualifications": "MBBS, MD (Medicine), DM (Pulmonology)", "hospital": "BLK Hospital", "city": "Delhi", "consultation_fee": 1300, "available": True, "languages": ["English", "Hindi"], "verified": True},
    {"id": "doc-012", "name": "Dr. Pooja Rao", "specialty": "Pulmonologist", "rating": 4.7, "experience_years": 13, "qualifications": "MBBS, MD, DM (Pulmonology)", "hospital": "Narayana Health", "city": "Bangalore", "consultation_fee": 900, "available": True, "languages": ["English", "Kannada", "Hindi"], "verified": True},
    
    # Hematologists
    {"id": "doc-013", "name": "Dr. Sandeep Malhotra", "specialty": "Hematologist", "rating": 4.8, "experience_years": 17, "qualifications": "MBBS, MD, DM (Hematology)", "hospital": "Tata Memorial Hospital", "city": "Mumbai", "consultation_fee": 1400, "available": True, "languages": ["English", "Hindi"], "verified": True},
    {"id": "doc-014", "name": "Dr. Lakshmi Krishnan", "specialty": "Hematologist", "rating": 4.6, "experience_years": 12, "qualifications": "MBBS, MD, DM", "hospital": "Apollo Cancer Centre", "city": "Chennai", "consultation_fee": 1100, "available": True, "languages": ["English", "Tamil", "Hindi"], "verified": True},
    
    # Orthopedists
    {"id": "doc-015", "name": "Dr. Manoj Aggarwal", "specialty": "Orthopedist", "rating": 4.9, "experience_years": 23, "qualifications": "MBBS, MS (Orthopedics)", "hospital": "Max Hospital", "city": "Delhi", "consultation_fee": 1500, "available": True, "languages": ["English", "Hindi"], "verified": True},
]

# Ayurveda Doctors
AYURVEDA_DOCTORS = [
    {"id": "ayur-001", "name": "Dr. Vaidya Rajesh Kotecha", "specialty": "Ayurveda", "rating": 4.8, "experience_years": 20, "qualifications": "BAMS, MD (Ayurveda)", "hospital": "Arya Vaidya Sala", "city": "Kottakkal", "consultation_fee": 800, "available": True, "languages": ["English", "Hindi", "Malayalam"], "verified": True, "expertise": ["Panchakarma", "Rasayana Therapy", "Dosha Analysis"]},
    {"id": "ayur-002", "name": "Dr. Priya Ayurvedacharya", "specialty": "Ayurveda", "rating": 4.7, "experience_years": 15, "qualifications": "BAMS, MD", "hospital": "Jiva Ayurveda", "city": "Delhi", "consultation_fee": 600, "available": True, "languages": ["English", "Hindi"], "verified": True, "expertise": ["Lifestyle Disorders", "Immunity Boost", "Stress Management"]},
    {"id": "ayur-003", "name": "Dr. Shankar Bhat", "specialty": "Ayurveda", "rating": 4.9, "experience_years": 25, "qualifications": "BAMS, PhD (Ayurveda)", "hospital": "Kerala Ayurveda", "city": "Bangalore", "consultation_fee": 1000, "available": True, "languages": ["English", "Kannada", "Malayalam", "Hindi"], "verified": True, "expertise": ["Chronic Diseases", "Digestive Health", "Skin Care"]},
    {"id": "ayur-004", "name": "Dr. Meera Vaidya", "specialty": "Ayurveda", "rating": 4.6, "experience_years": 12, "qualifications": "BAMS, MD (Kayachikitsa)", "hospital": "Patanjali Wellness", "city": "Haridwar", "consultation_fee": 500, "available": True, "languages": ["English", "Hindi"], "verified": True, "expertise": ["Women's Health", "Weight Management", "Detox Therapy"]},
    {"id": "ayur-005", "name": "Dr. Arun Vasudevan", "specialty": "Ayurveda", "rating": 4.8, "experience_years": 18, "qualifications": "BAMS, MD", "hospital": "Somatheeram Ayurveda", "city": "Trivandrum", "consultation_fee": 700, "available": True, "languages": ["English", "Malayalam", "Hindi"], "verified": True, "expertise": ["Pain Management", "Arthritis", "Neurological Disorders"]},
]

def get_doctors_by_specialty(specialty: str, limit: int = 5) -> List[Dict]:
    """Get doctors by specialty from mock database."""
    # Normalize specialty
    specialty_map = {
        "cardiology": "Cardiologist",
        "endocrinology": "Endocrinologist",
        "general medicine": "General Physician",
        "internal medicine": "General Physician",
        "nephrology": "Nephrologist",
        "gastroenterology": "Gastroenterologist",
        "pulmonology": "Pulmonologist",
        "hematology": "Hematologist",
        "orthopedics": "Orthopedist",
    }
    
    normalized = specialty.lower().strip()
    for key, value in specialty_map.items():
        if key in normalized:
            specialty = value
            break
    
    # Filter doctors by specialty
    filtered = [d for d in MOCK_DOCTORS if d["specialty"] == specialty]
    
    # If no specific match, return general physicians
    if not filtered:
        filtered = [d for d in MOCK_DOCTORS if d["specialty"] == "General Physician"]
    
    # Sort by rating
    filtered.sort(key=lambda x: -x["rating"])
    
    return filtered[:limit]

def get_ayurveda_doctors(limit: int = 3) -> List[Dict]:
    """Get Ayurveda doctors from mock database."""
    return AYURVEDA_DOCTORS[:limit]

def get_doctor_by_id(doctor_id: str) -> Dict:
    """Get doctor by ID."""
    all_doctors = MOCK_DOCTORS + AYURVEDA_DOCTORS
    for doctor in all_doctors:
        if doctor["id"] == doctor_id:
            return doctor
    return None
