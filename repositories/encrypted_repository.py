"""
Encrypted Database Repository for HealthTrack Pro
Provides automatic encryption/decryption for sensitive health data
Production-ready with comprehensive error handling
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorCollection
from utils.encryption import (
    HealthDataEncryption,
    encrypt_sensitive_data,
    decrypt_sensitive_data,
    SENSITIVE_HEALTH_FIELDS
)

logger = logging.getLogger(__name__)

# Configuration
ENCRYPTION_ENABLED = os.environ.get("ENCRYPTION_ENABLED", "true").lower() == "true"


class EncryptedRepository:
    """
    Base repository class with automatic encryption/decryption
    Wraps MongoDB operations with transparent field-level encryption
    """
    
    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        sensitive_fields: Optional[List[str]] = None,
        encryption_enabled: bool = ENCRYPTION_ENABLED
    ):
        self.collection = collection
        self.sensitive_fields = sensitive_fields or SENSITIVE_HEALTH_FIELDS
        self.encryption_enabled = encryption_enabled
        self.encryptor = HealthDataEncryption() if encryption_enabled else None
        
    async def insert_one(self, document: Dict[str, Any]) -> str:
        """
        Insert a single document with encryption applied to sensitive fields
        Returns the document ID
        """
        try:
            doc_to_insert = document.copy()
            
            if self.encryption_enabled and self.encryptor:
                doc_to_insert = encrypt_sensitive_data(doc_to_insert, self.sensitive_fields)
                logger.debug(f"Encrypted document before insert")
            
            result = await self.collection.insert_one(doc_to_insert)
            return str(result.inserted_id) if result.inserted_id else document.get("id", "")
            
        except Exception as e:
            logger.error(f"Error inserting encrypted document: {e}")
            raise
    
    async def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Insert multiple documents with encryption
        Returns list of inserted IDs
        """
        try:
            docs_to_insert = []
            for doc in documents:
                doc_copy = doc.copy()
                if self.encryption_enabled and self.encryptor:
                    doc_copy = encrypt_sensitive_data(doc_copy, self.sensitive_fields)
                docs_to_insert.append(doc_copy)
            
            result = await self.collection.insert_many(docs_to_insert)
            return [str(id) for id in result.inserted_ids]
            
        except Exception as e:
            logger.error(f"Error inserting multiple encrypted documents: {e}")
            raise
    
    async def find_one(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        decrypt: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find a single document and optionally decrypt sensitive fields
        """
        try:
            if projection is None:
                projection = {"_id": 0}
            elif "_id" not in projection:
                projection["_id"] = 0
                
            document = await self.collection.find_one(query, projection)
            
            if document and decrypt and self.encryption_enabled:
                document = decrypt_sensitive_data(document)
                
            return document
            
        except Exception as e:
            logger.error(f"Error finding document: {e}")
            raise
    
    async def find_many(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[List[tuple]] = None,
        decrypt: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents and optionally decrypt sensitive fields
        """
        try:
            if projection is None:
                projection = {"_id": 0}
            elif "_id" not in projection:
                projection["_id"] = 0
            
            cursor = self.collection.find(query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            
            cursor = cursor.skip(skip).limit(limit)
            documents = await cursor.to_list(length=limit)
            
            if decrypt and self.encryption_enabled:
                documents = [decrypt_sensitive_data(doc) for doc in documents]
                
            return documents
            
        except Exception as e:
            logger.error(f"Error finding documents: {e}")
            raise
    
    async def update_one(
        self,
        query: Dict[str, Any],
        update_data: Dict[str, Any],
        upsert: bool = False
    ) -> int:
        """
        Update a single document with encryption on sensitive fields
        Returns count of modified documents
        """
        try:
            # Handle $set updates
            if "$set" in update_data:
                set_data = update_data["$set"].copy()
                if self.encryption_enabled and self.encryptor:
                    set_data = encrypt_sensitive_data(set_data, self.sensitive_fields)
                update_data = {"$set": set_data}
            elif not any(key.startswith("$") for key in update_data.keys()):
                # Plain update - wrap in $set
                if self.encryption_enabled and self.encryptor:
                    update_data = encrypt_sensitive_data(update_data, self.sensitive_fields)
                update_data = {"$set": update_data}
            
            result = await self.collection.update_one(query, update_data, upsert=upsert)
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    async def update_many(
        self,
        query: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> int:
        """
        Update multiple documents with encryption
        Returns count of modified documents
        """
        try:
            if "$set" in update_data:
                set_data = update_data["$set"].copy()
                if self.encryption_enabled and self.encryptor:
                    set_data = encrypt_sensitive_data(set_data, self.sensitive_fields)
                update_data = {"$set": set_data}
            
            result = await self.collection.update_many(query, update_data)
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error updating documents: {e}")
            raise
    
    async def delete_one(self, query: Dict[str, Any]) -> int:
        """Delete a single document"""
        try:
            result = await self.collection.delete_one(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    async def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents"""
        try:
            result = await self.collection.delete_many(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise
    
    async def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query"""
        try:
            if query is None:
                query = {}
            return await self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            raise
    
    async def aggregate(
        self,
        pipeline: List[Dict[str, Any]],
        decrypt: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Run aggregation pipeline and optionally decrypt results
        """
        try:
            cursor = self.collection.aggregate(pipeline)
            documents = await cursor.to_list(length=1000)
            
            if decrypt and self.encryption_enabled:
                documents = [decrypt_sensitive_data(doc) for doc in documents]
                
            return documents
            
        except Exception as e:
            logger.error(f"Error in aggregation: {e}")
            raise


class PatientRepository(EncryptedRepository):
    """
    Specialized repository for patient data with healthcare-specific encryption
    """
    
    PATIENT_SENSITIVE_FIELDS = [
        "first_name", "last_name", "email", "phone", "date_of_birth",
        "national_id", "abha_number", "emirates_id", "passport_number",
        "insurance_id", "address", "street", "city", "emergency_contact",
        "medical_history", "allergies", "chronic_conditions", "blood_group"
    ]
    
    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection, self.PATIENT_SENSITIVE_FIELDS)
    
    async def create_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new patient with encryption"""
        # Add timestamps
        patient_data["created_at"] = datetime.now(timezone.utc).isoformat()
        patient_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await self.insert_one(patient_data)
        return patient_data
    
    async def get_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient by ID with decryption"""
        return await self.find_one({"id": patient_id})
    
    async def search_patients(
        self,
        organization_id: str,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search patients within an organization
        Note: Search on encrypted fields requires exact match or separate search index
        """
        query = {"organization_id": organization_id}
        
        # For encrypted fields, we can't do regex search
        # In production, you'd use a separate search index or searchable encryption
        if search_term:
            query["patient_number"] = {"$regex": search_term, "$options": "i"}
        
        return await self.find_many(query, skip=skip, limit=limit)
    
    async def update_patient(
        self,
        patient_id: str,
        update_data: Dict[str, Any]
    ) -> int:
        """Update patient with encryption"""
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": patient_id}, update_data)


class MedicalRecordRepository(EncryptedRepository):
    """
    Repository for medical records with full encryption
    """
    
    MEDICAL_SENSITIVE_FIELDS = [
        "diagnosis", "symptoms", "treatment_plan", "medications",
        "prescriptions", "lab_results", "clinical_notes", "vital_signs",
        "allergies", "procedures", "imaging_results"
    ]
    
    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection, self.MEDICAL_SENSITIVE_FIELDS)


class PrescriptionRepository(EncryptedRepository):
    """
    Repository for prescriptions with encryption
    """
    
    PRESCRIPTION_SENSITIVE_FIELDS = [
        "medications", "dosage", "instructions", "diagnosis",
        "patient_name", "doctor_notes"
    ]
    
    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection, self.PRESCRIPTION_SENSITIVE_FIELDS)


class LabResultRepository(EncryptedRepository):
    """
    Repository for lab results with encryption
    """
    
    LAB_SENSITIVE_FIELDS = [
        "results", "test_values", "interpretation", "notes",
        "abnormal_flags", "reference_ranges"
    ]
    
    def __init__(self, collection: AsyncIOMotorCollection):
        super().__init__(collection, self.LAB_SENSITIVE_FIELDS)


# Factory function to create encrypted repositories
async def get_encrypted_patient_repo(db) -> PatientRepository:
    """Factory function for dependency injection"""
    return PatientRepository(db.healthtrack_patients)


async def get_encrypted_medical_repo(db) -> MedicalRecordRepository:
    """Factory function for dependency injection"""
    return MedicalRecordRepository(db.healthtrack_medical_records)


async def get_encrypted_prescription_repo(db) -> PrescriptionRepository:
    """Factory function for dependency injection"""
    return PrescriptionRepository(db.healthtrack_prescriptions)


async def get_encrypted_lab_repo(db) -> LabResultRepository:
    """Factory function for dependency injection"""
    return LabResultRepository(db.healthtrack_lab_results)


# Export all
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
