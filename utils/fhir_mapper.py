"""
HL7 FHIR R4 Data Mappings for DHA/NABIDH Compliance
Implements complete resource mappings for UAE healthcare interoperability
"""

from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid

# FHIR R4 Resource Types used for NABIDH
class FHIRResourceType(str, Enum):
    PATIENT = "Patient"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    ENCOUNTER = "Encounter"
    CONDITION = "Condition"
    OBSERVATION = "Observation"
    MEDICATION_REQUEST = "MedicationRequest"
    MEDICATION_STATEMENT = "MedicationStatement"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    PROCEDURE = "Procedure"
    IMMUNIZATION = "Immunization"
    DOCUMENT_REFERENCE = "DocumentReference"
    APPOINTMENT = "Appointment"
    CARE_PLAN = "CarePlan"
    BUNDLE = "Bundle"


class FHIRMapper:
    """
    Maps internal HealthTrack Pro data models to FHIR R4 resources
    Compliant with NABIDH UAE specifications
    """
    
    FHIR_VERSION = "4.0.1"
    NABIDH_SYSTEM = "https://nabidh.ae/fhir"
    
    @staticmethod
    def create_meta(resource_type: str, profile_url: Optional[str] = None) -> Dict:
        """Create FHIR meta element"""
        meta = {
            "versionId": "1",
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
        if profile_url:
            meta["profile"] = [profile_url]
        return meta
    
    @staticmethod
    def create_identifier(system: str, value: str, use: str = "official") -> Dict:
        """Create FHIR identifier element"""
        return {
            "use": use,
            "system": system,
            "value": value
        }
    
    @staticmethod
    def create_human_name(family: str, given: List[str], use: str = "official") -> Dict:
        """Create FHIR HumanName element"""
        return {
            "use": use,
            "family": family,
            "given": given
        }
    
    @staticmethod
    def create_contact_point(system: str, value: str, use: str = "mobile") -> Dict:
        """Create FHIR ContactPoint element"""
        return {
            "system": system,  # phone, email, fax, etc.
            "value": value,
            "use": use
        }
    
    @staticmethod
    def create_address(
        line: List[str],
        city: str,
        state: str,
        postal_code: str,
        country: str = "AE",
        use: str = "home"
    ) -> Dict:
        """Create FHIR Address element"""
        return {
            "use": use,
            "type": "physical",
            "line": line,
            "city": city,
            "state": state,
            "postalCode": postal_code,
            "country": country
        }
    
    @classmethod
    def map_patient(cls, patient_data: Dict) -> Dict:
        """
        Map internal patient data to FHIR R4 Patient resource
        NABIDH compliant
        """
        patient_id = patient_data.get("id", str(uuid.uuid4()))
        
        resource = {
            "resourceType": "Patient",
            "id": patient_id,
            "meta": cls.create_meta("Patient", f"{cls.NABIDH_SYSTEM}/StructureDefinition/nabidh-patient"),
            "identifier": [
                cls.create_identifier(
                    f"{cls.NABIDH_SYSTEM}/patient-id",
                    patient_data.get("patient_number", patient_id)
                )
            ],
            "active": patient_data.get("status", "active") == "active",
            "name": [
                cls.create_human_name(
                    family=patient_data.get("last_name", ""),
                    given=[patient_data.get("first_name", "")]
                )
            ],
            "telecom": [],
            "gender": cls._map_gender(patient_data.get("gender", "")),
        }
        
        # Add phone
        if patient_data.get("phone"):
            resource["telecom"].append(
                cls.create_contact_point("phone", patient_data["phone"], "mobile")
            )
        
        # Add email
        if patient_data.get("email"):
            resource["telecom"].append(
                cls.create_contact_point("email", patient_data["email"], "home")
            )
        
        # Add birthDate
        if patient_data.get("date_of_birth"):
            dob = patient_data["date_of_birth"]
            if isinstance(dob, str):
                resource["birthDate"] = dob[:10]  # YYYY-MM-DD format
            elif isinstance(dob, (datetime, date)):
                resource["birthDate"] = dob.strftime("%Y-%m-%d")
        
        # Add address
        address = patient_data.get("address", {})
        if isinstance(address, dict) and address:
            resource["address"] = [
                cls.create_address(
                    line=[address.get("street", "")],
                    city=address.get("city", ""),
                    state=address.get("state", ""),
                    postal_code=address.get("zip_code", ""),
                    country=address.get("country", "AE")
                )
            ]
        
        # Add Emirates ID if available
        if patient_data.get("emirates_id"):
            resource["identifier"].append(
                cls.create_identifier(
                    "https://nabidh.ae/emirates-id",
                    patient_data["emirates_id"]
                )
            )
        
        # Add ABHA number if available (for Indian patients)
        if patient_data.get("abha_number"):
            resource["identifier"].append(
                cls.create_identifier(
                    "https://abdm.gov.in/abha",
                    patient_data["abha_number"]
                )
            )
        
        return resource
    
    @classmethod
    def map_practitioner(cls, doctor_data: Dict) -> Dict:
        """
        Map internal doctor data to FHIR R4 Practitioner resource
        """
        doctor_id = doctor_data.get("id", str(uuid.uuid4()))
        
        resource = {
            "resourceType": "Practitioner",
            "id": doctor_id,
            "meta": cls.create_meta("Practitioner"),
            "identifier": [
                cls.create_identifier(
                    f"{cls.NABIDH_SYSTEM}/practitioner-id",
                    doctor_data.get("registration_number", doctor_id)
                )
            ],
            "active": doctor_data.get("verification_status") == "verified",
            "name": [
                cls.create_human_name(
                    family=doctor_data.get("last_name", doctor_data.get("name", "").split()[-1] if doctor_data.get("name") else ""),
                    given=[doctor_data.get("first_name", doctor_data.get("name", "").split()[0] if doctor_data.get("name") else "")]
                )
            ],
            "telecom": [],
            "qualification": []
        }
        
        # Add contact info
        if doctor_data.get("phone"):
            resource["telecom"].append(
                cls.create_contact_point("phone", doctor_data["phone"])
            )
        if doctor_data.get("email"):
            resource["telecom"].append(
                cls.create_contact_point("email", doctor_data["email"])
            )
        
        # Add qualifications
        if doctor_data.get("qualification"):
            resource["qualification"].append({
                "code": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0360",
                        "code": doctor_data.get("qualification"),
                        "display": doctor_data.get("qualification")
                    }]
                }
            })
        
        # Add specialty
        if doctor_data.get("specialty"):
            resource["qualification"].append({
                "code": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "display": doctor_data["specialty"]
                    }]
                }
            })
        
        return resource
    
    @classmethod
    def map_encounter(cls, appointment_data: Dict) -> Dict:
        """
        Map internal appointment data to FHIR R4 Encounter resource
        """
        encounter_id = appointment_data.get("id", str(uuid.uuid4()))
        
        # Map status
        status_map = {
            "scheduled": "planned",
            "confirmed": "planned",
            "in_progress": "in-progress",
            "completed": "finished",
            "cancelled": "cancelled",
            "no_show": "cancelled"
        }
        
        resource = {
            "resourceType": "Encounter",
            "id": encounter_id,
            "meta": cls.create_meta("Encounter"),
            "identifier": [
                cls.create_identifier(
                    f"{cls.NABIDH_SYSTEM}/encounter-id",
                    encounter_id
                )
            ],
            "status": status_map.get(appointment_data.get("status", "scheduled"), "planned"),
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": cls._map_consultation_type(appointment_data.get("consultation_type", "AMB")),
                "display": appointment_data.get("consultation_type", "ambulatory")
            },
            "subject": {
                "reference": f"Patient/{appointment_data.get('patient_id', '')}"
            },
            "participant": []
        }
        
        # Add practitioner
        if appointment_data.get("doctor_id"):
            resource["participant"].append({
                "type": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                        "code": "PPRF",
                        "display": "primary performer"
                    }]
                }],
                "individual": {
                    "reference": f"Practitioner/{appointment_data['doctor_id']}"
                }
            })
        
        # Add period
        if appointment_data.get("appointment_date"):
            resource["period"] = {
                "start": appointment_data["appointment_date"]
            }
            if appointment_data.get("end_time"):
                resource["period"]["end"] = appointment_data["end_time"]
        
        # Add reason
        if appointment_data.get("reason"):
            resource["reasonCode"] = [{
                "text": appointment_data["reason"]
            }]
        
        return resource
    
    @classmethod
    def map_observation(cls, vitals_data: Dict, patient_id: str) -> List[Dict]:
        """
        Map internal vitals data to FHIR R4 Observation resources
        Returns a list of observations (one per vital sign)
        """
        observations = []
        
        vital_mappings = {
            "heart_rate": {
                "code": "8867-4",
                "display": "Heart rate",
                "unit": "beats/minute",
                "ucum": "/min"
            },
            "blood_pressure_systolic": {
                "code": "8480-6",
                "display": "Systolic blood pressure",
                "unit": "mmHg",
                "ucum": "mm[Hg]"
            },
            "blood_pressure_diastolic": {
                "code": "8462-4",
                "display": "Diastolic blood pressure",
                "unit": "mmHg",
                "ucum": "mm[Hg]"
            },
            "temperature": {
                "code": "8310-5",
                "display": "Body temperature",
                "unit": "°C",
                "ucum": "Cel"
            },
            "spo2": {
                "code": "2708-6",
                "display": "Oxygen saturation",
                "unit": "%",
                "ucum": "%"
            },
            "respiratory_rate": {
                "code": "9279-1",
                "display": "Respiratory rate",
                "unit": "breaths/minute",
                "ucum": "/min"
            },
            "weight": {
                "code": "29463-7",
                "display": "Body weight",
                "unit": "kg",
                "ucum": "kg"
            },
            "height": {
                "code": "8302-2",
                "display": "Body height",
                "unit": "cm",
                "ucum": "cm"
            },
            "bmi": {
                "code": "39156-5",
                "display": "Body mass index",
                "unit": "kg/m²",
                "ucum": "kg/m2"
            }
        }
        
        recorded_at = vitals_data.get("recorded_at", datetime.now(timezone.utc).isoformat())
        
        for vital_key, vital_info in vital_mappings.items():
            if vital_key in vitals_data and vitals_data[vital_key] is not None:
                obs_id = str(uuid.uuid4())
                observation = {
                    "resourceType": "Observation",
                    "id": obs_id,
                    "meta": cls.create_meta("Observation"),
                    "status": "final",
                    "category": [{
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": vital_info["code"],
                            "display": vital_info["display"]
                        }]
                    },
                    "subject": {
                        "reference": f"Patient/{patient_id}"
                    },
                    "effectiveDateTime": recorded_at,
                    "valueQuantity": {
                        "value": vitals_data[vital_key],
                        "unit": vital_info["unit"],
                        "system": "http://unitsofmeasure.org",
                        "code": vital_info["ucum"]
                    }
                }
                observations.append(observation)
        
        return observations
    
    @classmethod
    def map_medication_request(cls, prescription_data: Dict) -> Dict:
        """
        Map internal prescription data to FHIR R4 MedicationRequest resource
        """
        prescription_id = prescription_data.get("id", str(uuid.uuid4()))
        
        resource = {
            "resourceType": "MedicationRequest",
            "id": prescription_id,
            "meta": cls.create_meta("MedicationRequest"),
            "identifier": [
                cls.create_identifier(
                    f"{cls.NABIDH_SYSTEM}/prescription-id",
                    prescription_id
                )
            ],
            "status": cls._map_prescription_status(prescription_data.get("status", "active")),
            "intent": "order",
            "subject": {
                "reference": f"Patient/{prescription_data.get('patient_id', '')}"
            },
            "authoredOn": prescription_data.get("prescription_date", datetime.now(timezone.utc).isoformat()),
            "requester": {
                "reference": f"Practitioner/{prescription_data.get('doctor_id', '')}"
            },
            "dosageInstruction": []
        }
        
        # Add medication
        medication = prescription_data.get("medication", {})
        if medication:
            resource["medicationCodeableConcept"] = {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "display": medication.get("name", "")
                }],
                "text": medication.get("name", "")
            }
        
        # Add dosage instructions
        if prescription_data.get("dosage"):
            resource["dosageInstruction"].append({
                "text": prescription_data["dosage"],
                "timing": {
                    "code": {
                        "text": prescription_data.get("frequency", "")
                    }
                },
                "route": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "26643006",
                        "display": "Oral route"
                    }]
                }
            })
        
        # Add duration
        if prescription_data.get("duration"):
            resource["dispenseRequest"] = {
                "validityPeriod": {
                    "start": prescription_data.get("prescription_date"),
                    "end": prescription_data.get("end_date")
                },
                "numberOfRepeatsAllowed": prescription_data.get("refills_allowed", 0)
            }
        
        return resource
    
    @classmethod
    def map_allergy_intolerance(cls, allergy_data: Dict, patient_id: str) -> Dict:
        """
        Map allergy data to FHIR R4 AllergyIntolerance resource
        """
        allergy_id = str(uuid.uuid4())
        
        return {
            "resourceType": "AllergyIntolerance",
            "id": allergy_id,
            "meta": cls.create_meta("AllergyIntolerance"),
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": "active"
                }]
            },
            "verificationStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "confirmed"
                }]
            },
            "type": allergy_data.get("type", "allergy"),
            "category": [allergy_data.get("category", "medication")],
            "criticality": allergy_data.get("severity", "low"),
            "code": {
                "text": allergy_data.get("allergen", "")
            },
            "patient": {
                "reference": f"Patient/{patient_id}"
            },
            "reaction": [{
                "manifestation": [{
                    "text": allergy_data.get("reaction", "")
                }]
            }] if allergy_data.get("reaction") else []
        }
    
    @classmethod
    def map_diagnostic_report(cls, lab_result_data: Dict) -> Dict:
        """
        Map lab result data to FHIR R4 DiagnosticReport resource
        """
        report_id = lab_result_data.get("id", str(uuid.uuid4()))
        
        resource = {
            "resourceType": "DiagnosticReport",
            "id": report_id,
            "meta": cls.create_meta("DiagnosticReport"),
            "identifier": [
                cls.create_identifier(
                    f"{cls.NABIDH_SYSTEM}/lab-report-id",
                    report_id
                )
            ],
            "status": lab_result_data.get("status", "final"),
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                    "code": "LAB",
                    "display": "Laboratory"
                }]
            }],
            "code": {
                "text": lab_result_data.get("test_name", "")
            },
            "subject": {
                "reference": f"Patient/{lab_result_data.get('patient_id', '')}"
            },
            "effectiveDateTime": lab_result_data.get("result_date", datetime.now(timezone.utc).isoformat()),
            "issued": lab_result_data.get("issued_date", datetime.now(timezone.utc).isoformat()),
            "result": []
        }
        
        # Add results as observation references
        results = lab_result_data.get("results", [])
        for result in results:
            resource["result"].append({
                "reference": f"Observation/{result.get('id', str(uuid.uuid4()))}"
            })
        
        # Add conclusion
        if lab_result_data.get("conclusion"):
            resource["conclusion"] = lab_result_data["conclusion"]
        
        return resource
    
    @classmethod
    def create_bundle(cls, resources: List[Dict], bundle_type: str = "collection") -> Dict:
        """
        Create a FHIR Bundle containing multiple resources
        Used for batch operations and document exchanges
        """
        return {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "meta": cls.create_meta("Bundle"),
            "type": bundle_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(resources),
            "entry": [
                {
                    "fullUrl": f"urn:uuid:{resource.get('id', str(uuid.uuid4()))}",
                    "resource": resource
                }
                for resource in resources
            ]
        }
    
    # Helper methods
    @staticmethod
    def _map_gender(gender: str) -> str:
        """Map internal gender values to FHIR gender codes"""
        gender_map = {
            "male": "male",
            "female": "female",
            "other": "other",
            "m": "male",
            "f": "female",
            "": "unknown"
        }
        return gender_map.get(gender.lower() if gender else "", "unknown")
    
    @staticmethod
    def _map_consultation_type(consultation_type: str) -> str:
        """Map consultation type to FHIR encounter class codes"""
        type_map = {
            "video": "VR",  # Virtual
            "audio": "VR",
            "in_person": "AMB",  # Ambulatory
            "in-person": "AMB",
            "emergency": "EMER",
            "home_visit": "HH"  # Home health
        }
        return type_map.get(consultation_type.lower() if consultation_type else "", "AMB")
    
    @staticmethod
    def _map_prescription_status(status: str) -> str:
        """Map prescription status to FHIR MedicationRequest status"""
        status_map = {
            "active": "active",
            "completed": "completed",
            "cancelled": "cancelled",
            "stopped": "stopped",
            "draft": "draft"
        }
        return status_map.get(status.lower() if status else "", "active")


# Export
__all__ = [
    'FHIRMapper',
    'FHIRResourceType'
]
