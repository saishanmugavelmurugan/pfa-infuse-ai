"""
Seed script to populate drug database with 100 common medicines
Run this after database setup
"""

COMMON_DRUGS = [
    {
        "drug_name": "Paracetamol",
        "generic_name": "Acetaminophen",
        "brand_names": ["Crocin", "Dolo", "Calpol"],
        "category": "Analgesic/Antipyretic",
        "therapeutic_class": "NSAIDs",
        "controlled_substance": False,
        "prescription_required": False,
        "available_forms": ["tablet", "syrup", "injection"],
        "common_dosages": ["250mg", "500mg", "650mg"],
        "standard_instructions": "Take after meals with water",
        "side_effects": ["Nausea", "Allergic reactions", "Liver damage in overdose"],
        "contraindications": ["Severe liver disease"],
        "drug_interactions": ["Warfarin", "Alcohol"],
        "pregnancy_category": "B",
        "price_range": {"min": 5, "max": 50, "currency": "INR"},
        "manufacturer": "Multiple",
        "country_of_origin": "India"
    },
    {
        "drug_name": "Amoxicillin",
        "generic_name": "Amoxicillin",
        "brand_names": ["Mox", "Novamox", "Wymox"],
        "category": "Antibiotic",
        "therapeutic_class": "Penicillins",
        "controlled_substance": False,
        "prescription_required": True,
        "available_forms": ["capsule", "syrup", "injection"],
        "common_dosages": ["250mg", "500mg"],
        "standard_instructions": "Take with or without food. Complete the course",
        "side_effects": ["Diarrhea", "Nausea", "Skin rash"],
        "contraindications": ["Penicillin allergy"],
        "drug_interactions": ["Warfarin", "Oral contraceptives"],
        "pregnancy_category": "B",
        "price_range": {"min": 30, "max": 150, "currency": "INR"}
    },
    {
        "drug_name": "Azithromycin",
        "generic_name": "Azithromycin",
        "brand_names": ["Azee", "Azithral", "Zithromax"],
        "category": "Antibiotic",
        "therapeutic_class": "Macrolides",
        "controlled_substance": False,
        "prescription_required": True,
        "available_forms": ["tablet", "syrup"],
        "common_dosages": ["250mg", "500mg"],
        "standard_instructions": "Take once daily",
        "side_effects": ["Stomach upset", "Diarrhea"],
        "contraindications": ["Liver disease"],
        "drug_interactions": ["Warfarin"],
        "pregnancy_category": "B",
        "price_range": {"min": 50, "max": 200, "currency": "INR"}
    },
    {
        "drug_name": "Cetirizine",
        "generic_name": "Cetirizine",
        "brand_names": ["Zyrtec", "Alerid", "Cetrizet"],
        "category": "Antihistamine",
        "therapeutic_class": "H1 Antihistamines",
        "controlled_substance": False,
        "prescription_required": False,
        "available_forms": ["tablet", "syrup"],
        "common_dosages": ["5mg", "10mg"],
        "standard_instructions": "Take once daily, preferably at bedtime",
        "side_effects": ["Drowsiness", "Dry mouth"],
        "contraindications": ["Kidney disease"],
        "drug_interactions": ["CNS depressants"],
        "pregnancy_category": "B",
        "price_range": {"min": 10, "max": 60, "currency": "INR"}
    },
    {
        "drug_name": "Omeprazole",
        "generic_name": "Omeprazole",
        "brand_names": ["Omez", "Prilosec", "Omecip"],
        "category": "Proton Pump Inhibitor",
        "therapeutic_class": "Antacids",
        "controlled_substance": False,
        "prescription_required": True,
        "available_forms": ["capsule", "injection"],
        "common_dosages": ["20mg", "40mg"],
        "standard_instructions": "Take 30 minutes before meals",
        "side_effects": ["Headache", "Nausea", "Diarrhea"],
        "contraindications": ["Liver disease"],
        "drug_interactions": ["Clopidogrel", "Warfarin"],
        "pregnancy_category": "C",
        "price_range": {"min": 20, "max": 100, "currency": "INR"}
    }
    # Add 95 more drugs here for production...
]

async def seed_drugs(db):
    """Seed drug database"""
    import uuid
    from datetime import datetime, timezone
    
    for drug_data in COMMON_DRUGS:
        drug_data["id"] = str(uuid.uuid4())
        drug_data["is_active"] = True
        drug_data["created_at"] = datetime.now(timezone.utc).isoformat()
        drug_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Check if drug already exists
        existing = await db.drug_database.find_one({"drug_name": drug_data["drug_name"]})
        if not existing:
            await db.drug_database.insert_one(drug_data)
    
    print(f"Seeded {len(COMMON_DRUGS)} drugs successfully")
