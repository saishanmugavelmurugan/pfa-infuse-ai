"""
Global Health Schemes Management API
Supports region-specific health schemes with pre-populated data for major countries
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import os

router = APIRouter(prefix="/health-schemes", tags=["Health Schemes"])

# Database connection
async def get_db():
    import dependencies
    return dependencies.get_db()

# Pydantic Models
class HealthSchemeBase(BaseModel):
    name: str
    country_code: str
    country_name: str
    scheme_type: str  # government, private, hybrid
    coverage_type: str  # universal, means-tested, employer-based
    description: str
    eligibility_criteria: Optional[str] = None
    coverage_details: Optional[Dict] = None
    enrollment_process: Optional[str] = None
    benefits: Optional[List[str]] = None
    limitations: Optional[List[str]] = None
    official_website: Optional[str] = None
    contact_info: Optional[Dict] = None

class HealthSchemeCreate(HealthSchemeBase):
    pass

class UserHealthSchemeSubmission(BaseModel):
    country_code: str
    country_name: str
    scheme_name: str
    description: str
    coverage_details: Optional[str] = None
    personal_experience: Optional[str] = None
    rating: Optional[int] = None  # 1-5
    submitter_id: Optional[str] = None

class SchemeComparisonRequest(BaseModel):
    scheme_ids: List[str]
    comparison_aspects: Optional[List[str]] = None  # coverage, cost, eligibility, etc.

# Pre-populated Global Health Schemes Database
GLOBAL_HEALTH_SCHEMES = {
    "IN": [
        {
            "id": "in-pmjay",
            "name": "Ayushman Bharat - PMJAY",
            "country_code": "IN",
            "country_name": "India",
            "scheme_type": "government",
            "coverage_type": "means-tested",
            "description": "Pradhan Mantri Jan Arogya Yojana provides health coverage of ₹5 lakhs per family per year for secondary and tertiary care hospitalization.",
            "eligibility_criteria": "Bottom 40% of Indian population based on SECC database, including rural poor and urban workers",
            "coverage_details": {
                "annual_limit": 500000,
                "currency": "INR",
                "family_coverage": True,
                "hospitalization": True,
                "outpatient": False,
                "pre_existing_conditions": True,
                "packages_covered": 1500
            },
            "enrollment_process": "Automatic for eligible families based on SECC data. Others can apply at Ayushman Bharat centers.",
            "benefits": [
                "Cashless treatment at empanelled hospitals",
                "No cap on family size",
                "Pre and post hospitalization expenses covered",
                "Transport allowance included",
                "No age limit"
            ],
            "limitations": [
                "Only secondary and tertiary hospitalization covered",
                "OPD not covered",
                "Limited to empanelled hospitals",
                "Certain procedures excluded"
            ],
            "official_website": "https://pmjay.gov.in",
            "contact_info": {"helpline": "14555", "email": "support@pmjay.gov.in"}
        },
        {
            "id": "in-cghs",
            "name": "Central Government Health Scheme (CGHS)",
            "country_code": "IN",
            "country_name": "India",
            "scheme_type": "government",
            "coverage_type": "employer-based",
            "description": "Comprehensive healthcare for central government employees, pensioners and their dependents.",
            "eligibility_criteria": "Central government employees, pensioners, MPs, judges, and freedom fighters",
            "coverage_details": {
                "annual_limit": "Unlimited for most treatments",
                "currency": "INR",
                "family_coverage": True,
                "hospitalization": True,
                "outpatient": True,
                "pre_existing_conditions": True
            },
            "benefits": [
                "OPD and IPD coverage",
                "Cashless at empanelled hospitals",
                "Covers dependents",
                "Medicines from CGHS dispensaries"
            ],
            "official_website": "https://cghs.gov.in"
        }
    ],
    "US": [
        {
            "id": "us-medicare",
            "name": "Medicare",
            "country_code": "US",
            "country_name": "United States",
            "scheme_type": "government",
            "coverage_type": "age-based",
            "description": "Federal health insurance program for people 65+, certain younger people with disabilities, and people with End-Stage Renal Disease.",
            "eligibility_criteria": "Age 65+, or under 65 with certain disabilities, or any age with ESRD",
            "coverage_details": {
                "part_a": "Hospital insurance - covers inpatient hospital stays, skilled nursing, hospice, home health",
                "part_b": "Medical insurance - covers doctor visits, outpatient care, preventive services",
                "part_c": "Medicare Advantage - private insurance alternative",
                "part_d": "Prescription drug coverage",
                "currency": "USD"
            },
            "enrollment_process": "Automatic at 65 if receiving Social Security, otherwise apply during Initial Enrollment Period",
            "benefits": [
                "Hospital stays (Part A)",
                "Doctor visits (Part B)",
                "Preventive care",
                "Prescription drugs (Part D)",
                "Home health care"
            ],
            "limitations": [
                "Does not cover long-term care",
                "Limited dental, vision, hearing",
                "Cost-sharing required (premiums, deductibles, copays)",
                "Not available to non-citizens without 5+ years residency"
            ],
            "official_website": "https://www.medicare.gov",
            "contact_info": {"helpline": "1-800-MEDICARE", "phone": "1-800-633-4227"}
        },
        {
            "id": "us-medicaid",
            "name": "Medicaid",
            "country_code": "US",
            "country_name": "United States",
            "scheme_type": "government",
            "coverage_type": "means-tested",
            "description": "Joint federal and state program providing health coverage to eligible low-income adults, children, pregnant women, elderly adults, and people with disabilities.",
            "eligibility_criteria": "Low-income individuals and families, varies by state. Income typically below 138% FPL in expansion states.",
            "coverage_details": {
                "hospitalization": True,
                "outpatient": True,
                "prescription_drugs": True,
                "mental_health": True,
                "currency": "USD"
            },
            "benefits": [
                "Comprehensive coverage",
                "Little to no cost to beneficiaries",
                "Includes dental and vision for children",
                "Long-term care coverage"
            ],
            "official_website": "https://www.medicaid.gov"
        }
    ],
    "GB": [
        {
            "id": "gb-nhs",
            "name": "National Health Service (NHS)",
            "country_code": "GB",
            "country_name": "United Kingdom",
            "scheme_type": "government",
            "coverage_type": "universal",
            "description": "Publicly funded healthcare system providing free healthcare for all UK residents at the point of use.",
            "eligibility_criteria": "All UK residents (ordinarily resident in the UK)",
            "coverage_details": {
                "hospitalization": True,
                "outpatient": True,
                "prescription_drugs": True,
                "mental_health": True,
                "dental": "Partial (charges apply)",
                "optical": "Partial (charges apply)",
                "currency": "GBP",
                "annual_limit": "Unlimited"
            },
            "enrollment_process": "Register with a GP (General Practitioner) near your residence",
            "benefits": [
                "Free at point of use for most services",
                "Universal coverage",
                "No insurance premiums",
                "Comprehensive care including mental health",
                "Emergency care for all"
            ],
            "limitations": [
                "Waiting times for non-urgent care",
                "Prescription charges in England (free in Scotland, Wales, NI)",
                "Limited dental and optical coverage",
                "Some treatments require referral"
            ],
            "official_website": "https://www.nhs.uk",
            "contact_info": {"emergency": "999", "non_emergency": "111"}
        }
    ],
    "CA": [
        {
            "id": "ca-msp",
            "name": "Medicare (Provincial Health Insurance)",
            "country_code": "CA",
            "country_name": "Canada",
            "scheme_type": "government",
            "coverage_type": "universal",
            "description": "Publicly funded healthcare providing medically necessary hospital and physician services to all Canadian residents.",
            "eligibility_criteria": "Canadian citizens and permanent residents after waiting period (usually 3 months)",
            "coverage_details": {
                "hospitalization": True,
                "physician_services": True,
                "diagnostic_tests": True,
                "prescription_drugs": "Varies by province",
                "dental": False,
                "vision": "Limited",
                "currency": "CAD"
            },
            "benefits": [
                "Free hospital and doctor visits",
                "No user fees for insured services",
                "Portable across provinces",
                "Covers medically necessary services"
            ],
            "limitations": [
                "Prescription drugs not universally covered",
                "Dental not covered (except hospital dental)",
                "Vision care limited",
                "Some services require supplementary insurance"
            ],
            "official_website": "https://www.canada.ca/en/health-canada/services/health-care-system/reports-publications/health-care-system/canada.html"
        }
    ],
    "AE": [
        {
            "id": "ae-dha",
            "name": "Dubai Health Authority Insurance",
            "country_code": "AE",
            "country_name": "United Arab Emirates",
            "scheme_type": "hybrid",
            "coverage_type": "mandatory",
            "description": "Mandatory health insurance for all Dubai residents and visitors. Employers must provide coverage for employees.",
            "eligibility_criteria": "All residents and employees in Dubai",
            "coverage_details": {
                "basic_plan": "Essential Benefits Plan (EBP) with AED 150,000 annual limit",
                "hospitalization": True,
                "outpatient": True,
                "maternity": True,
                "currency": "AED"
            },
            "benefits": [
                "Mandatory coverage for all",
                "Basic plan covers essential services",
                "Emergency care included",
                "Maternity coverage"
            ],
            "official_website": "https://www.dha.gov.ae"
        }
    ],
    "SG": [
        {
            "id": "sg-medishield",
            "name": "MediShield Life",
            "country_code": "SG",
            "country_name": "Singapore",
            "scheme_type": "government",
            "coverage_type": "universal",
            "description": "Basic health insurance plan providing lifetime protection for all Singapore Citizens and Permanent Residents against large hospital bills.",
            "eligibility_criteria": "All Singapore Citizens and Permanent Residents (automatic enrollment)",
            "coverage_details": {
                "hospitalization": True,
                "outpatient": "Selected treatments",
                "annual_limit": 100000,
                "lifetime_limit": "None",
                "currency": "SGD"
            },
            "benefits": [
                "Automatic enrollment",
                "Lifetime coverage",
                "No pre-existing condition exclusions",
                "Covers hospitalization in public hospitals"
            ],
            "limitations": [
                "Co-payment required",
                "Coverage limits apply",
                "Private hospital coverage limited"
            ],
            "official_website": "https://www.moh.gov.sg/cost-financing/healthcare-schemes-subsidies/medishield-life"
        },
        {
            "id": "sg-medisave",
            "name": "MediSave",
            "country_code": "SG",
            "country_name": "Singapore",
            "scheme_type": "government",
            "coverage_type": "universal",
            "description": "National medical savings scheme helping Singaporeans save for healthcare expenses, especially in old age.",
            "eligibility_criteria": "All working Singapore Citizens and Permanent Residents",
            "coverage_details": {
                "contribution_rate": "8-10.5% of wages",
                "withdrawable_for": "Hospitalization, day surgery, outpatient treatments",
                "currency": "SGD"
            },
            "benefits": [
                "Personal medical savings",
                "Can be used for family members",
                "Earns interest",
                "Tax-deductible contributions"
            ],
            "official_website": "https://www.cpf.gov.sg/member/healthcare-financing/medisave"
        }
    ],
    "AU": [
        {
            "id": "au-medicare",
            "name": "Medicare Australia",
            "country_code": "AU",
            "country_name": "Australia",
            "scheme_type": "government",
            "coverage_type": "universal",
            "description": "Australia's universal health insurance scheme providing free or subsidised health services to Australian citizens and permanent residents.",
            "eligibility_criteria": "Australian citizens, permanent residents, and some visa holders",
            "coverage_details": {
                "hospitalization": "Free public hospital care",
                "outpatient": "Subsidised",
                "prescription_drugs": "Subsidised through PBS",
                "currency": "AUD"
            },
            "benefits": [
                "Free public hospital treatment",
                "Subsidised doctor visits (bulk billing)",
                "Pharmaceutical Benefits Scheme",
                "Some allied health services"
            ],
            "official_website": "https://www.servicesaustralia.gov.au/medicare"
        }
    ],
    "DE": [
        {
            "id": "de-gkv",
            "name": "Statutory Health Insurance (GKV)",
            "country_code": "DE",
            "country_name": "Germany",
            "scheme_type": "government",
            "coverage_type": "mandatory",
            "description": "Germany's statutory health insurance system covering approximately 90% of the population through non-profit sickness funds.",
            "eligibility_criteria": "Employees earning below income threshold (mandatory), others can opt in",
            "coverage_details": {
                "contribution_rate": "14.6% of gross salary (shared employer/employee)",
                "hospitalization": True,
                "outpatient": True,
                "prescription_drugs": True,
                "dental": "Basic coverage",
                "currency": "EUR"
            },
            "benefits": [
                "Comprehensive coverage",
                "Free choice of doctors",
                "No waiting periods",
                "Family members covered free"
            ],
            "official_website": "https://www.bundesgesundheitsministerium.de"
        }
    ],
    "FR": [
        {
            "id": "fr-securite-sociale",
            "name": "Sécurité Sociale (French Social Security)",
            "country_code": "FR",
            "country_name": "France",
            "scheme_type": "government",
            "coverage_type": "universal",
            "description": "France's universal health coverage system providing high reimbursement rates for medical expenses.",
            "eligibility_criteria": "All legal residents of France",
            "coverage_details": {
                "reimbursement_rate": "70% for most services, 100% for serious conditions",
                "hospitalization": True,
                "outpatient": True,
                "prescription_drugs": True,
                "currency": "EUR"
            },
            "benefits": [
                "High reimbursement rates",
                "Free choice of providers",
                "100% coverage for chronic conditions",
                "Complementary insurance widely available"
            ],
            "official_website": "https://www.ameli.fr"
        }
    ],
    "JP": [
        {
            "id": "jp-nhi",
            "name": "National Health Insurance (Kokumin Kenko Hoken)",
            "country_code": "JP",
            "country_name": "Japan",
            "scheme_type": "government",
            "coverage_type": "universal",
            "description": "Japan's mandatory health insurance covering self-employed, unemployed, and retirees not covered by employer insurance.",
            "eligibility_criteria": "All residents not covered by employer-based insurance",
            "coverage_details": {
                "copay_rate": "30% for most, 10-20% for elderly",
                "hospitalization": True,
                "outpatient": True,
                "prescription_drugs": True,
                "currency": "JPY"
            },
            "benefits": [
                "Low out-of-pocket costs",
                "High-quality care",
                "No waiting lists",
                "Coverage for most treatments"
            ],
            "official_website": "https://www.mhlw.go.jp"
        }
    ]
}

# API Endpoints

@router.get("/regions")
async def get_supported_regions():
    """Get list of all supported regions with their health schemes"""
    regions = []
    for country_code, schemes in GLOBAL_HEALTH_SCHEMES.items():
        if schemes:
            regions.append({
                "country_code": country_code,
                "country_name": schemes[0]["country_name"],
                "schemes_count": len(schemes),
                "scheme_names": [s["name"] for s in schemes]
            })
    
    return {
        "total_regions": len(regions),
        "regions": sorted(regions, key=lambda x: x["country_name"])
    }

@router.get("/by-region/{country_code}")
async def get_schemes_by_region(country_code: str):
    """Get all health schemes for a specific region/country"""
    country_code = country_code.upper()
    
    # First check pre-populated schemes
    schemes = GLOBAL_HEALTH_SCHEMES.get(country_code, [])
    
    # Also check user-submitted schemes from database
    db = await get_db()
    user_schemes = await db.user_health_schemes.find(
        {"country_code": country_code, "status": "approved"},
        {"_id": 0}
    ).to_list(50)
    
    all_schemes = schemes + user_schemes
    
    if not all_schemes:
        return {
            "country_code": country_code,
            "schemes": [],
            "has_schemes": False,
            "message": "No health schemes found for this region. You can submit scheme information."
        }
    
    return {
        "country_code": country_code,
        "country_name": all_schemes[0].get("country_name", country_code),
        "schemes": all_schemes,
        "has_schemes": True,
        "total": len(all_schemes)
    }

@router.get("/scheme/{scheme_id}")
async def get_scheme_details(scheme_id: str):
    """Get detailed information about a specific health scheme"""
    # Search in pre-populated schemes
    for country_schemes in GLOBAL_HEALTH_SCHEMES.values():
        for scheme in country_schemes:
            if scheme["id"] == scheme_id:
                return scheme
    
    # Search in user-submitted schemes
    db = await get_db()
    scheme = await db.user_health_schemes.find_one({"id": scheme_id}, {"_id": 0})
    if scheme:
        return scheme
    
    raise HTTPException(status_code=404, detail="Health scheme not found")

@router.post("/submit")
async def submit_health_scheme(submission: UserHealthSchemeSubmission):
    """Allow users to submit information about their country's health scheme"""
    db = await get_db()
    
    scheme_record = {
        "id": f"user-{str(uuid4())[:8]}",
        "name": submission.scheme_name,
        "country_code": submission.country_code.upper(),
        "country_name": submission.country_name,
        "scheme_type": "user-submitted",
        "coverage_type": "unknown",
        "description": submission.description,
        "coverage_details_text": submission.coverage_details,
        "personal_experience": submission.personal_experience,
        "rating": submission.rating,
        "submitted_by": submission.submitter_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",  # pending_review, approved, rejected
        "verified": False
    }
    
    await db.user_health_schemes.insert_one({**scheme_record})
    
    return {
        "success": True,
        "message": "Thank you for submitting health scheme information. It will be reviewed by our team.",
        "submission_id": scheme_record["id"]
    }

@router.get("/user-submissions")
async def get_user_submissions(status: Optional[str] = None):
    """Get user-submitted health schemes (for admin review)"""
    db = await get_db()
    
    query = {}
    if status:
        query["status"] = status
    
    submissions = await db.user_health_schemes.find(query, {"_id": 0}).to_list(100)
    
    return {
        "total": len(submissions),
        "submissions": submissions
    }

@router.put("/user-submissions/{submission_id}/review")
async def review_submission(submission_id: str, approved: bool, reviewer_notes: Optional[str] = None):
    """Approve or reject a user submission (admin only)"""
    db = await get_db()
    
    update_data = {
        "status": "approved" if approved else "rejected",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_notes": reviewer_notes
    }
    
    result = await db.user_health_schemes.update_one(
        {"id": submission_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {"success": True, "status": update_data["status"]}

@router.get("/compare")
async def compare_schemes(scheme_ids: str):
    """Compare multiple health schemes side by side"""
    ids = [s.strip() for s in scheme_ids.split(",")]
    
    schemes_to_compare = []
    for scheme_id in ids:
        # Search in pre-populated schemes
        found = False
        for country_schemes in GLOBAL_HEALTH_SCHEMES.values():
            for scheme in country_schemes:
                if scheme["id"] == scheme_id:
                    schemes_to_compare.append(scheme)
                    found = True
                    break
            if found:
                break
        
        if not found:
            # Search in user-submitted schemes
            db = await get_db()
            scheme = await db.user_health_schemes.find_one({"id": scheme_id, "status": "approved"}, {"_id": 0})
            if scheme:
                schemes_to_compare.append(scheme)
    
    if len(schemes_to_compare) < 2:
        raise HTTPException(status_code=400, detail="At least 2 valid schemes required for comparison")
    
    # Build comparison matrix
    comparison = {
        "schemes": schemes_to_compare,
        "comparison_matrix": {
            "coverage_type": [s.get("coverage_type", "N/A") for s in schemes_to_compare],
            "scheme_type": [s.get("scheme_type", "N/A") for s in schemes_to_compare],
            "hospitalization": [s.get("coverage_details", {}).get("hospitalization", "N/A") for s in schemes_to_compare],
            "outpatient": [s.get("coverage_details", {}).get("outpatient", "N/A") for s in schemes_to_compare],
            "prescription_drugs": [s.get("coverage_details", {}).get("prescription_drugs", "N/A") for s in schemes_to_compare],
        }
    }
    
    return comparison

@router.get("/statistics")
async def get_scheme_statistics():
    """Get global health scheme statistics for admin dashboard"""
    db = await get_db()
    
    # Count pre-populated schemes
    total_prepopulated = sum(len(schemes) for schemes in GLOBAL_HEALTH_SCHEMES.values())
    countries_covered = len(GLOBAL_HEALTH_SCHEMES)
    
    # Count user submissions
    user_submissions = await db.user_health_schemes.count_documents({})
    approved_submissions = await db.user_health_schemes.count_documents({"status": "approved"})
    pending_submissions = await db.user_health_schemes.count_documents({"status": "pending_review"})
    
    return {
        "total_schemes": total_prepopulated + approved_submissions,
        "prepopulated_schemes": total_prepopulated,
        "countries_with_schemes": countries_covered,
        "user_submissions": {
            "total": user_submissions,
            "approved": approved_submissions,
            "pending": pending_submissions
        },
        "scheme_types": {
            "government": sum(1 for schemes in GLOBAL_HEALTH_SCHEMES.values() for s in schemes if s.get("scheme_type") == "government"),
            "hybrid": sum(1 for schemes in GLOBAL_HEALTH_SCHEMES.values() for s in schemes if s.get("scheme_type") == "hybrid"),
            "private": sum(1 for schemes in GLOBAL_HEALTH_SCHEMES.values() for s in schemes if s.get("scheme_type") == "private")
        }
    }
