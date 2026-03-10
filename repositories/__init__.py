"""
Repository module initialization
"""

from repositories.encrypted_repository import (
    EncryptedRepository,
    PatientRepository,
    MedicalRecordRepository,
    PrescriptionRepository,
    LabResultRepository,
    get_encrypted_patient_repo,
    get_encrypted_medical_repo,
    get_encrypted_prescription_repo,
    get_encrypted_lab_repo,
    ENCRYPTION_ENABLED
)

__all__ = [
    'EncryptedRepository',
    'PatientRepository',
    'MedicalRecordRepository',
    'PrescriptionRepository',
    'LabResultRepository',
    'get_encrypted_patient_repo',
    'get_encrypted_medical_repo',
    'get_encrypted_prescription_repo',
    'get_encrypted_lab_repo',
    'ENCRYPTION_ENABLED'
]
