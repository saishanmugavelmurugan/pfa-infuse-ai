"""
Seed Drug Database and Lab Test Catalog
"""

import asyncio
from datetime import datetime, timezone
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "healthtrack_pro")

# Comprehensive Drug Database
DRUGS = [
    {
        "id": "drug-001",
        "name": "Metformin",
        "generic_name": "Metformin Hydrochloride",
        "brand_names": ["Glucophage", "Fortamet", "Glumetza"],
        "drug_class": "Biguanide Antidiabetic",
        "dosage_forms": ["Tablet", "Extended-release tablet"],
        "strengths": ["500mg", "850mg", "1000mg"],
        "indications": ["Type 2 Diabetes", "PCOS", "Prediabetes"],
        "contraindications": ["Severe renal impairment", "Metabolic acidosis"],
        "side_effects": ["Nausea", "Diarrhea", "Vitamin B12 deficiency"],
        "interactions": ["Contrast dyes", "Alcohol"],
        "warnings": ["Risk of lactic acidosis"],
        "pregnancy_category": "B",
        "price_range": {"min": 50, "max": 200, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-002",
        "name": "Atorvastatin",
        "generic_name": "Atorvastatin Calcium",
        "brand_names": ["Lipitor", "Atorva", "Storvas"],
        "drug_class": "Statin",
        "dosage_forms": ["Tablet"],
        "strengths": ["10mg", "20mg", "40mg", "80mg"],
        "indications": ["Hypercholesterolemia", "Cardiovascular prevention"],
        "contraindications": ["Active liver disease", "Pregnancy"],
        "side_effects": ["Muscle pain", "Elevated liver enzymes"],
        "interactions": ["Grapefruit juice", "Cyclosporine"],
        "warnings": ["Monitor liver function"],
        "pregnancy_category": "X",
        "price_range": {"min": 100, "max": 500, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-003",
        "name": "Amlodipine",
        "generic_name": "Amlodipine Besylate",
        "brand_names": ["Norvasc", "Amlong", "Amlokind"],
        "drug_class": "Calcium Channel Blocker",
        "dosage_forms": ["Tablet"],
        "strengths": ["2.5mg", "5mg", "10mg"],
        "indications": ["Hypertension", "Angina"],
        "contraindications": ["Severe hypotension", "Cardiogenic shock"],
        "side_effects": ["Peripheral edema", "Dizziness", "Flushing"],
        "interactions": ["CYP3A4 inhibitors", "Simvastatin"],
        "warnings": ["May worsen angina initially"],
        "pregnancy_category": "C",
        "price_range": {"min": 30, "max": 150, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-004",
        "name": "Omeprazole",
        "generic_name": "Omeprazole",
        "brand_names": ["Prilosec", "Omez", "Losec"],
        "drug_class": "Proton Pump Inhibitor",
        "dosage_forms": ["Capsule", "Tablet"],
        "strengths": ["10mg", "20mg", "40mg"],
        "indications": ["GERD", "Peptic ulcer", "H. pylori"],
        "contraindications": ["Hypersensitivity to PPIs"],
        "side_effects": ["Headache", "Nausea", "Vitamin B12 deficiency"],
        "interactions": ["Clopidogrel", "Methotrexate"],
        "warnings": ["C. difficile risk", "Bone fracture risk"],
        "pregnancy_category": "C",
        "price_range": {"min": 40, "max": 200, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-005",
        "name": "Paracetamol",
        "generic_name": "Acetaminophen",
        "brand_names": ["Crocin", "Tylenol", "Dolo"],
        "drug_class": "Analgesic/Antipyretic",
        "dosage_forms": ["Tablet", "Syrup", "Suppository"],
        "strengths": ["325mg", "500mg", "650mg", "1000mg"],
        "indications": ["Pain", "Fever", "Headache"],
        "contraindications": ["Severe liver disease"],
        "side_effects": ["Rare at therapeutic doses"],
        "interactions": ["Warfarin", "Alcohol"],
        "warnings": ["Hepatotoxicity with overdose"],
        "pregnancy_category": "B",
        "price_range": {"min": 10, "max": 50, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-006",
        "name": "Losartan",
        "generic_name": "Losartan Potassium",
        "brand_names": ["Cozaar", "Losar", "Repace"],
        "drug_class": "ARB",
        "dosage_forms": ["Tablet"],
        "strengths": ["25mg", "50mg", "100mg"],
        "indications": ["Hypertension", "Diabetic nephropathy"],
        "contraindications": ["Pregnancy", "Bilateral renal artery stenosis"],
        "side_effects": ["Dizziness", "Hyperkalemia"],
        "interactions": ["Potassium supplements", "NSAIDs"],
        "warnings": ["Fetal toxicity"],
        "pregnancy_category": "D",
        "price_range": {"min": 80, "max": 300, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-007",
        "name": "Aspirin",
        "generic_name": "Acetylsalicylic acid",
        "brand_names": ["Disprin", "Ecosprin", "Aspro"],
        "drug_class": "NSAID/Antiplatelet",
        "dosage_forms": ["Tablet", "Enteric-coated tablet"],
        "strengths": ["75mg", "150mg", "325mg", "500mg"],
        "indications": ["Pain", "Fever", "Cardiovascular prevention"],
        "contraindications": ["Bleeding disorders", "Peptic ulcer"],
        "side_effects": ["GI bleeding", "Tinnitus"],
        "interactions": ["Warfarin", "Methotrexate"],
        "warnings": ["Reye syndrome in children"],
        "pregnancy_category": "D",
        "price_range": {"min": 5, "max": 100, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-008",
        "name": "Levothyroxine",
        "generic_name": "Levothyroxine Sodium",
        "brand_names": ["Thyronorm", "Synthroid", "Eltroxin"],
        "drug_class": "Thyroid Hormone",
        "dosage_forms": ["Tablet"],
        "strengths": ["25mcg", "50mcg", "75mcg", "100mcg", "125mcg"],
        "indications": ["Hypothyroidism", "Thyroid cancer"],
        "contraindications": ["Untreated adrenal insufficiency"],
        "side_effects": ["Palpitations", "Weight loss", "Insomnia"],
        "interactions": ["Calcium supplements", "Iron supplements"],
        "warnings": ["Take on empty stomach"],
        "pregnancy_category": "A",
        "price_range": {"min": 50, "max": 200, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-009",
        "name": "Azithromycin",
        "generic_name": "Azithromycin",
        "brand_names": ["Zithromax", "Azee", "Azithral"],
        "drug_class": "Macrolide Antibiotic",
        "dosage_forms": ["Tablet", "Suspension"],
        "strengths": ["250mg", "500mg"],
        "indications": ["Respiratory infections", "Skin infections", "STIs"],
        "contraindications": ["QT prolongation", "Liver disease"],
        "side_effects": ["Nausea", "Diarrhea", "Abdominal pain"],
        "interactions": ["Warfarin", "Digoxin"],
        "warnings": ["QT prolongation risk"],
        "pregnancy_category": "B",
        "price_range": {"min": 80, "max": 300, "currency": "INR"},
        "is_active": True
    },
    {
        "id": "drug-010",
        "name": "Pantoprazole",
        "generic_name": "Pantoprazole Sodium",
        "brand_names": ["Pan", "Protonix", "Pantocid"],
        "drug_class": "Proton Pump Inhibitor",
        "dosage_forms": ["Tablet", "Injection"],
        "strengths": ["20mg", "40mg"],
        "indications": ["GERD", "Erosive esophagitis", "Zollinger-Ellison"],
        "contraindications": ["PPI hypersensitivity"],
        "side_effects": ["Headache", "Diarrhea", "Abdominal pain"],
        "interactions": ["Methotrexate", "Rilpivirine"],
        "warnings": ["Long-term use risks"],
        "pregnancy_category": "B",
        "price_range": {"min": 60, "max": 250, "currency": "INR"},
        "is_active": True
    }
]

# Lab Test Catalog
LAB_TESTS = [
    {
        "id": "test-001",
        "test_name": "Complete Blood Count (CBC)",
        "category": "Hematology",
        "description": "Measures red blood cells, white blood cells, hemoglobin, hematocrit, and platelets",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 350,
        "currency": "INR",
        "components": ["RBC", "WBC", "Hemoglobin", "Hematocrit", "Platelets", "MCV", "MCH", "MCHC"],
        "is_active": True
    },
    {
        "id": "test-002",
        "test_name": "Lipid Profile",
        "category": "Biochemistry",
        "description": "Measures cholesterol levels including HDL, LDL, and triglycerides",
        "sample_type": "Blood",
        "fasting_required": True,
        "fasting_hours": 12,
        "turnaround_time": "Same day",
        "price": 600,
        "currency": "INR",
        "components": ["Total Cholesterol", "HDL", "LDL", "Triglycerides", "VLDL"],
        "is_active": True
    },
    {
        "id": "test-003",
        "test_name": "Liver Function Test (LFT)",
        "category": "Biochemistry",
        "description": "Evaluates liver health through various enzyme and protein levels",
        "sample_type": "Blood",
        "fasting_required": True,
        "fasting_hours": 8,
        "turnaround_time": "Same day",
        "price": 800,
        "currency": "INR",
        "components": ["ALT", "AST", "ALP", "Bilirubin", "Albumin", "Total Protein", "GGT"],
        "is_active": True
    },
    {
        "id": "test-004",
        "test_name": "Kidney Function Test (KFT)",
        "category": "Biochemistry",
        "description": "Assesses kidney function through blood markers",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 700,
        "currency": "INR",
        "components": ["Creatinine", "BUN", "Uric Acid", "eGFR", "Electrolytes"],
        "is_active": True
    },
    {
        "id": "test-005",
        "test_name": "Thyroid Profile (T3, T4, TSH)",
        "category": "Endocrinology",
        "description": "Measures thyroid hormone levels",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 900,
        "currency": "INR",
        "components": ["T3", "T4", "TSH"],
        "is_active": True
    },
    {
        "id": "test-006",
        "test_name": "HbA1c (Glycated Hemoglobin)",
        "category": "Diabetes",
        "description": "Measures average blood sugar over 2-3 months",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 500,
        "currency": "INR",
        "components": ["HbA1c percentage"],
        "is_active": True
    },
    {
        "id": "test-007",
        "test_name": "Fasting Blood Sugar (FBS)",
        "category": "Diabetes",
        "description": "Measures blood glucose level after fasting",
        "sample_type": "Blood",
        "fasting_required": True,
        "fasting_hours": 8,
        "turnaround_time": "Same day",
        "price": 100,
        "currency": "INR",
        "components": ["Fasting glucose"],
        "is_active": True
    },
    {
        "id": "test-008",
        "test_name": "Vitamin D (25-OH)",
        "category": "Vitamins",
        "description": "Measures vitamin D level in blood",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "1-2 days",
        "price": 1200,
        "currency": "INR",
        "components": ["25-Hydroxyvitamin D"],
        "is_active": True
    },
    {
        "id": "test-009",
        "test_name": "Vitamin B12",
        "category": "Vitamins",
        "description": "Measures vitamin B12 level",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "1-2 days",
        "price": 800,
        "currency": "INR",
        "components": ["Vitamin B12"],
        "is_active": True
    },
    {
        "id": "test-010",
        "test_name": "Urine Routine & Microscopy",
        "category": "Urology",
        "description": "Complete urine analysis including physical, chemical and microscopic examination",
        "sample_type": "Urine",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 200,
        "currency": "INR",
        "components": ["Physical exam", "Chemical exam", "Microscopy"],
        "is_active": True
    },
    {
        "id": "test-011",
        "test_name": "ESR (Erythrocyte Sedimentation Rate)",
        "category": "Hematology",
        "description": "Non-specific marker for inflammation",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 150,
        "currency": "INR",
        "components": ["ESR"],
        "is_active": True
    },
    {
        "id": "test-012",
        "test_name": "CRP (C-Reactive Protein)",
        "category": "Immunology",
        "description": "Inflammatory marker",
        "sample_type": "Blood",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 450,
        "currency": "INR",
        "components": ["CRP"],
        "is_active": True
    },
    {
        "id": "test-013",
        "test_name": "Iron Studies",
        "category": "Hematology",
        "description": "Comprehensive iron assessment",
        "sample_type": "Blood",
        "fasting_required": True,
        "fasting_hours": 8,
        "turnaround_time": "1-2 days",
        "price": 1000,
        "currency": "INR",
        "components": ["Serum Iron", "TIBC", "Ferritin", "Transferrin Saturation"],
        "is_active": True
    },
    {
        "id": "test-014",
        "test_name": "ECG (Electrocardiogram)",
        "category": "Cardiology",
        "description": "Records electrical activity of heart",
        "sample_type": "None",
        "fasting_required": False,
        "turnaround_time": "Immediate",
        "price": 300,
        "currency": "INR",
        "components": ["12-lead ECG"],
        "is_active": True
    },
    {
        "id": "test-015",
        "test_name": "Chest X-Ray",
        "category": "Radiology",
        "description": "Imaging of chest area",
        "sample_type": "None",
        "fasting_required": False,
        "turnaround_time": "Same day",
        "price": 400,
        "currency": "INR",
        "components": ["PA view", "Lateral view (if needed)"],
        "is_active": True
    }
]

# Drug Interactions Database
DRUG_INTERACTIONS = [
    {
        "drug_1_id": "drug-001",
        "drug_2_id": "drug-002",
        "severity": "moderate",
        "description": "Metformin and Atorvastatin may increase risk of muscle problems",
        "recommendation": "Monitor for muscle pain or weakness"
    },
    {
        "drug_1_id": "drug-003",
        "drug_2_id": "drug-002",
        "severity": "moderate",
        "description": "Amlodipine may increase Atorvastatin levels",
        "recommendation": "Limit Atorvastatin to 20mg when combined with Amlodipine"
    },
    {
        "drug_1_id": "drug-004",
        "drug_2_id": "drug-007",
        "severity": "minor",
        "description": "PPIs may reduce aspirin's antiplatelet effect",
        "recommendation": "Consider alternative acid suppression if needed"
    },
    {
        "drug_1_id": "drug-006",
        "drug_2_id": "drug-007",
        "severity": "moderate",
        "description": "NSAIDs may reduce antihypertensive effect of Losartan",
        "recommendation": "Monitor blood pressure closely"
    },
    {
        "drug_1_id": "drug-008",
        "drug_2_id": "drug-004",
        "severity": "minor",
        "description": "PPIs may reduce Levothyroxine absorption",
        "recommendation": "Take Levothyroxine 4 hours apart from PPIs"
    }
]

async def seed_data():
    """Seed drug database and lab test catalog"""
    print(f"Connecting to MongoDB at {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Seed Drugs
    print("Seeding drug database...")
    await db.drugs.delete_many({"id": {"$regex": "^drug-"}})
    if DRUGS:
        result = await db.drugs.insert_many(DRUGS)
        print(f"  Inserted {len(result.inserted_ids)} drugs")
    
    # Seed Lab Tests
    print("Seeding lab test catalog...")
    await db.lab_tests.delete_many({"id": {"$regex": "^test-"}})
    if LAB_TESTS:
        result = await db.lab_tests.insert_many(LAB_TESTS)
        print(f"  Inserted {len(result.inserted_ids)} lab tests")
    
    # Seed Drug Interactions
    print("Seeding drug interactions...")
    await db.drug_interactions.delete_many({})
    if DRUG_INTERACTIONS:
        result = await db.drug_interactions.insert_many(DRUG_INTERACTIONS)
        print(f"  Inserted {len(result.inserted_ids)} drug interactions")
    
    # Create indexes
    print("Creating indexes...")
    await db.drugs.create_index([("name", "text"), ("generic_name", "text")])
    await db.drugs.create_index([("drug_class", 1)])
    await db.lab_tests.create_index([("test_name", "text")])
    await db.lab_tests.create_index([("category", 1)])
    
    # Summary
    drug_count = await db.drugs.count_documents({})
    test_count = await db.lab_tests.count_documents({})
    interaction_count = await db.drug_interactions.count_documents({})
    
    print("\n=== Seeding Complete ===")
    print(f"Drugs: {drug_count}")
    print(f"Lab Tests: {test_count}")
    print(f"Drug Interactions: {interaction_count}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
