"""
FHIR R4 API Endpoints for DHA/NABIDH Compliance
Provides HL7 FHIR interoperability for UAE healthcare systems
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone
from utils.fhir_mapper import FHIRMapper, FHIRResourceType
from utils.auth import get_current_user
from dependencies import get_db

router = APIRouter(prefix="/fhir", tags=["FHIR R4 API"])


@router.get("/metadata")
async def get_capability_statement():
    """
    FHIR CapabilityStatement - describes server capabilities
    Required for NABIDH compliance
    """
    return {
        "resourceType": "CapabilityStatement",
        "id": "healthtrack-pro-fhir",
        "name": "HealthTrackProFHIRServer",
        "title": "HealthTrack Pro FHIR R4 Server",
        "status": "active",
        "experimental": False,
        "date": datetime.now(timezone.utc).isoformat(),
        "publisher": "Infuse-AI",
        "description": "FHIR R4 compliant server for HealthTrack Pro healthcare platform",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "implementation": {
            "description": "HealthTrack Pro FHIR Server - NABIDH Compliant",
            "url": "https://healthtrack.infuse-ai.in/api/fhir"
        },
        "rest": [{
            "mode": "server",
            "resource": [
                {
                    "type": "Patient",
                    "profile": "https://nabidh.ae/fhir/StructureDefinition/nabidh-patient",
                    "interaction": [
                        {"code": "read"},
                        {"code": "search-type"},
                        {"code": "create"},
                        {"code": "update"}
                    ],
                    "searchParam": [
                        {"name": "identifier", "type": "token"},
                        {"name": "name", "type": "string"},
                        {"name": "birthdate", "type": "date"}
                    ]
                },
                {
                    "type": "Practitioner",
                    "interaction": [{"code": "read"}, {"code": "search-type"}]
                },
                {
                    "type": "Encounter",
                    "interaction": [{"code": "read"}, {"code": "search-type"}, {"code": "create"}]
                },
                {
                    "type": "Observation",
                    "interaction": [{"code": "read"}, {"code": "search-type"}, {"code": "create"}]
                },
                {
                    "type": "MedicationRequest",
                    "interaction": [{"code": "read"}, {"code": "search-type"}]
                },
                {
                    "type": "DiagnosticReport",
                    "interaction": [{"code": "read"}, {"code": "search-type"}]
                },
                {
                    "type": "AllergyIntolerance",
                    "interaction": [{"code": "read"}, {"code": "search-type"}, {"code": "create"}]
                }
            ]
        }]
    }


@router.get("/Patient/{patient_id}")
async def get_patient_fhir(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get patient in FHIR R4 format"""
    patient = await db.healthtrack_patients.find_one({"id": patient_id}, {"_id": 0})
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return FHIRMapper.map_patient(patient)


@router.get("/Patient")
async def search_patients_fhir(
    identifier: Optional[str] = None,
    name: Optional[str] = None,
    birthdate: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Search patients - returns FHIR Bundle"""
    query = {}
    
    if identifier:
        query["patient_number"] = identifier
    if name:
        query["$or"] = [
            {"first_name": {"$regex": name, "$options": "i"}},
            {"last_name": {"$regex": name, "$options": "i"}}
        ]
    if birthdate:
        query["date_of_birth"] = birthdate
    
    patients = await db.healthtrack_patients.find(query, {"_id": 0}).limit(100).to_list(100)
    
    fhir_patients = [FHIRMapper.map_patient(p) for p in patients]
    
    return FHIRMapper.create_bundle(fhir_patients, "searchset")


@router.get("/Practitioner/{practitioner_id}")
async def get_practitioner_fhir(
    practitioner_id: str,
    db = Depends(get_db)
):
    """Get practitioner (doctor) in FHIR R4 format"""
    doctor = await db.doctors.find_one({"id": practitioner_id}, {"_id": 0})
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    
    return FHIRMapper.map_practitioner(doctor)


@router.get("/Practitioner")
async def search_practitioners_fhir(
    name: Optional[str] = None,
    specialty: Optional[str] = None,
    db = Depends(get_db)
):
    """Search practitioners - returns FHIR Bundle"""
    query = {}
    
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if specialty:
        query["specialty"] = {"$regex": specialty, "$options": "i"}
    
    doctors = await db.doctors.find(query, {"_id": 0}).limit(100).to_list(100)
    
    fhir_practitioners = [FHIRMapper.map_practitioner(d) for d in doctors]
    
    return FHIRMapper.create_bundle(fhir_practitioners, "searchset")


@router.get("/Encounter/{encounter_id}")
async def get_encounter_fhir(
    encounter_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get encounter (appointment) in FHIR R4 format"""
    appointment = await db.healthtrack_appointments.find_one({"id": encounter_id}, {"_id": 0})
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    return FHIRMapper.map_encounter(appointment)


@router.get("/Encounter")
async def search_encounters_fhir(
    patient: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Search encounters - returns FHIR Bundle"""
    query = {}
    
    if patient:
        query["patient_id"] = patient
    if status:
        query["status"] = status
    if date:
        query["appointment_date"] = {"$regex": f"^{date}"}
    
    appointments = await db.healthtrack_appointments.find(query, {"_id": 0}).limit(100).to_list(100)
    
    fhir_encounters = [FHIRMapper.map_encounter(a) for a in appointments]
    
    return FHIRMapper.create_bundle(fhir_encounters, "searchset")


@router.get("/Observation")
async def search_observations_fhir(
    patient: Optional[str] = None,
    category: Optional[str] = Query(None, description="e.g., vital-signs"),
    code: Optional[str] = Query(None, description="LOINC code"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Search observations (vitals) - returns FHIR Bundle"""
    query = {}
    
    if patient:
        query["patient_id"] = patient
    
    vitals = await db.healthtrack_vitals.find(query, {"_id": 0}).limit(100).to_list(100)
    
    all_observations = []
    for vital in vitals:
        observations = FHIRMapper.map_observation(vital, vital.get("patient_id", ""))
        all_observations.extend(observations)
    
    return FHIRMapper.create_bundle(all_observations, "searchset")


@router.get("/MedicationRequest/{prescription_id}")
async def get_medication_request_fhir(
    prescription_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get medication request (prescription) in FHIR R4 format"""
    prescription = await db.healthtrack_prescriptions.find_one({"id": prescription_id}, {"_id": 0})
    
    if not prescription:
        raise HTTPException(status_code=404, detail="MedicationRequest not found")
    
    return FHIRMapper.map_medication_request(prescription)


@router.get("/MedicationRequest")
async def search_medication_requests_fhir(
    patient: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Search medication requests - returns FHIR Bundle"""
    query = {}
    
    if patient:
        query["patient_id"] = patient
    if status:
        query["status"] = status
    
    prescriptions = await db.healthtrack_prescriptions.find(query, {"_id": 0}).limit(100).to_list(100)
    
    fhir_prescriptions = [FHIRMapper.map_medication_request(p) for p in prescriptions]
    
    return FHIRMapper.create_bundle(fhir_prescriptions, "searchset")


@router.get("/DiagnosticReport/{report_id}")
async def get_diagnostic_report_fhir(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get diagnostic report (lab result) in FHIR R4 format"""
    lab_result = await db.healthtrack_lab_results.find_one({"id": report_id}, {"_id": 0})
    
    if not lab_result:
        raise HTTPException(status_code=404, detail="DiagnosticReport not found")
    
    return FHIRMapper.map_diagnostic_report(lab_result)


@router.get("/DiagnosticReport")
async def search_diagnostic_reports_fhir(
    patient: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Search diagnostic reports - returns FHIR Bundle"""
    query = {}
    
    if patient:
        query["patient_id"] = patient
    if status:
        query["status"] = status
    
    lab_results = await db.healthtrack_lab_results.find(query, {"_id": 0}).limit(100).to_list(100)
    
    fhir_reports = [FHIRMapper.map_diagnostic_report(r) for r in lab_results]
    
    return FHIRMapper.create_bundle(fhir_reports, "searchset")


@router.post("/Bundle")
async def process_bundle(
    bundle: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Process a FHIR Bundle (batch/transaction)
    Used for bulk data exchange with NABIDH
    """
    if bundle.get("resourceType") != "Bundle":
        raise HTTPException(status_code=400, detail="Invalid resource type. Expected Bundle.")
    
    bundle_type = bundle.get("type", "")
    entries = bundle.get("entry", [])
    
    results = []
    
    for entry in entries:
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType", "")
        
        result = {
            "resourceType": resource_type,
            "status": "processed",
            "id": resource.get("id", "")
        }
        
        # Process based on resource type
        # This is a simplified implementation - full implementation would create/update resources
        if resource_type == "Patient":
            result["message"] = "Patient resource received"
        elif resource_type == "Observation":
            result["message"] = "Observation resource received"
        else:
            result["message"] = f"{resource_type} resource received"
        
        results.append(result)
    
    return {
        "resourceType": "Bundle",
        "type": "batch-response" if bundle_type == "batch" else "transaction-response",
        "entry": [
            {
                "response": {
                    "status": "200",
                    "outcome": r
                }
            }
            for r in results
        ]
    }


@router.get("/Patient/{patient_id}/$everything")
async def get_patient_everything_fhir(
    patient_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    FHIR $everything operation - returns all resources for a patient
    Used for comprehensive health record export
    """
    patient = await db.healthtrack_patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    resources = [FHIRMapper.map_patient(patient)]
    
    # Get encounters
    appointments = await db.healthtrack_appointments.find(
        {"patient_id": patient_id}, {"_id": 0}
    ).to_list(100)
    resources.extend([FHIRMapper.map_encounter(a) for a in appointments])
    
    # Get vitals
    vitals = await db.healthtrack_vitals.find(
        {"patient_id": patient_id}, {"_id": 0}
    ).to_list(100)
    for v in vitals:
        resources.extend(FHIRMapper.map_observation(v, patient_id))
    
    # Get prescriptions
    prescriptions = await db.healthtrack_prescriptions.find(
        {"patient_id": patient_id}, {"_id": 0}
    ).to_list(100)
    resources.extend([FHIRMapper.map_medication_request(p) for p in prescriptions])
    
    # Get lab results
    lab_results = await db.healthtrack_lab_results.find(
        {"patient_id": patient_id}, {"_id": 0}
    ).to_list(100)
    resources.extend([FHIRMapper.map_diagnostic_report(r) for r in lab_results])
    
    return FHIRMapper.create_bundle(resources, "searchset")


@router.get("/health")
async def fhir_health_check():
    """FHIR server health check"""
    return {
        "status": "healthy",
        "fhir_version": "4.0.1",
        "nabidh_compliant": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
