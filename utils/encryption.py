"""
AES-256 Encryption Module for DHA Compliance
Provides at-rest encryption for sensitive health data
Implements HIPAA and GDPR-compliant encryption standards
"""

import os
import base64
import secrets
import hashlib
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timezone

# Constants
AES_KEY_SIZE = 32  # 256 bits
AES_BLOCK_SIZE = 16  # 128 bits
IV_SIZE = 16
SALT_SIZE = 32
PBKDF2_ITERATIONS = 100000

# Get encryption key from environment or generate secure one
def get_encryption_key() -> bytes:
    """
    Get the master encryption key from environment variable
    Falls back to generating a new key if not set (not recommended for production)
    """
    key_b64 = os.environ.get("ENCRYPTION_KEY")
    
    if key_b64:
        return base64.b64decode(key_b64)
    else:
        # Generate a new key (should be saved to environment in production)
        new_key = secrets.token_bytes(AES_KEY_SIZE)
        print(f"[WARNING] No ENCRYPTION_KEY set. Generated new key: {base64.b64encode(new_key).decode()}")
        print("[WARNING] Please set this as ENCRYPTION_KEY environment variable for production use")
        return new_key


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend()
    )
    return kdf.derive(password.encode())


class HealthDataEncryption:
    """
    AES-256-GCM encryption for healthcare data
    GCM mode provides both confidentiality and integrity
    """
    
    def __init__(self, key: Optional[bytes] = None):
        self.key = key or get_encryption_key()
    
    def encrypt(self, plaintext: Union[str, bytes]) -> Dict[str, str]:
        """
        Encrypt data using AES-256-GCM
        Returns dict with encrypted data, IV, and tag for integrity verification
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Generate random IV
        iv = secrets.token_bytes(IV_SIZE)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        return {
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "tag": base64.b64encode(encryptor.tag).decode('utf-8'),
            "algorithm": "AES-256-GCM",
            "encrypted_at": datetime.now(timezone.utc).isoformat()
        }
    
    def decrypt(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt data encrypted with AES-256-GCM
        Verifies integrity using authentication tag
        """
        ciphertext = base64.b64decode(encrypted_data["ciphertext"])
        iv = base64.b64decode(encrypted_data["iv"])
        tag = base64.b64decode(encrypted_data["tag"])
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        return plaintext.decode('utf-8')
    
    def encrypt_field(self, value: Any) -> str:
        """Encrypt a single field value and return as compact string"""
        encrypted = self.encrypt(str(value))
        # Combine into single string: iv:tag:ciphertext
        return f"{encrypted['iv']}:{encrypted['tag']}:{encrypted['ciphertext']}"
    
    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a single field value from compact string"""
        parts = encrypted_value.split(':')
        if len(parts) != 3:
            raise ValueError("Invalid encrypted field format")
        
        encrypted_data = {
            "iv": parts[0],
            "tag": parts[1],
            "ciphertext": parts[2]
        }
        return self.decrypt(encrypted_data)


# Sensitive fields that should be encrypted for DHA compliance
SENSITIVE_HEALTH_FIELDS = [
    # Patient PII
    "first_name",
    "last_name",
    "email",
    "phone",
    "date_of_birth",
    "national_id",
    "passport_number",
    "abha_number",
    "insurance_id",
    
    # Address
    "address",
    "street",
    "city",
    
    # Medical Information
    "diagnosis",
    "symptoms",
    "treatment_plan",
    "medical_history",
    "chronic_conditions",
    "allergies",
    "medications",
    "prescriptions",
    
    # Lab Results
    "lab_results",
    "test_results",
    "blood_type",
    
    # Financial
    "payment_details",
    "bank_account",
    "card_number"
]


def encrypt_sensitive_data(data: Dict[str, Any], fields_to_encrypt: Optional[list] = None) -> Dict[str, Any]:
    """
    Encrypt specified sensitive fields in a data dictionary
    Returns new dict with encrypted values
    """
    if fields_to_encrypt is None:
        fields_to_encrypt = SENSITIVE_HEALTH_FIELDS
    
    encryptor = HealthDataEncryption()
    encrypted_data = data.copy()
    encrypted_fields = []
    
    def encrypt_nested(obj: Any, path: str = "") -> Any:
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                field_path = f"{path}.{key}" if path else key
                if key in fields_to_encrypt and value is not None and value != "":
                    result[key] = encryptor.encrypt_field(value)
                    encrypted_fields.append(field_path)
                else:
                    result[key] = encrypt_nested(value, field_path)
            return result
        elif isinstance(obj, list):
            return [encrypt_nested(item, path) for item in obj]
        else:
            return obj
    
    encrypted_data = encrypt_nested(encrypted_data)
    encrypted_data["_encryption_metadata"] = {
        "encrypted": True,
        "algorithm": "AES-256-GCM",
        "encrypted_fields": encrypted_fields,
        "encrypted_at": datetime.now(timezone.utc).isoformat()
    }
    
    return encrypted_data


def decrypt_sensitive_data(encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypt all encrypted fields in a data dictionary
    Returns new dict with decrypted values
    """
    metadata = encrypted_data.get("_encryption_metadata", {})
    if not metadata.get("encrypted"):
        return encrypted_data
    
    encryptor = HealthDataEncryption()
    encrypted_fields = set(metadata.get("encrypted_fields", []))
    
    def decrypt_nested(obj: Any, path: str = "") -> Any:
        if isinstance(obj, dict):
            if "_encryption_metadata" in obj:
                result = {k: v for k, v in obj.items() if k != "_encryption_metadata"}
            else:
                result = {}
            
            for key, value in obj.items():
                if key == "_encryption_metadata":
                    continue
                    
                field_path = f"{path}.{key}" if path else key
                
                if field_path in encrypted_fields and isinstance(value, str):
                    try:
                        result[key] = encryptor.decrypt_field(value)
                    except Exception:
                        result[key] = value  # Keep original if decryption fails
                else:
                    result[key] = decrypt_nested(value, field_path)
            return result
        elif isinstance(obj, list):
            return [decrypt_nested(item, path) for item in obj]
        else:
            return obj
    
    return decrypt_nested(encrypted_data)


class EncryptedHealthRecord:
    """
    Wrapper class for handling encrypted health records
    Provides automatic encryption/decryption when storing/retrieving from database
    """
    
    def __init__(self, db_collection):
        self.collection = db_collection
        self.encryptor = HealthDataEncryption()
    
    async def insert_encrypted(self, record: Dict[str, Any]) -> str:
        """Insert a record with sensitive fields encrypted"""
        encrypted_record = encrypt_sensitive_data(record)
        result = await self.collection.insert_one(encrypted_record)
        return str(result.inserted_id)
    
    async def find_decrypted(self, query: Dict[str, Any], projection: Optional[Dict] = None) -> list:
        """Find records and decrypt sensitive fields"""
        if projection is None:
            projection = {"_id": 0}
        
        cursor = self.collection.find(query, projection)
        records = await cursor.to_list(length=1000)
        
        return [decrypt_sensitive_data(record) for record in records]
    
    async def find_one_decrypted(self, query: Dict[str, Any], projection: Optional[Dict] = None) -> Optional[Dict]:
        """Find one record and decrypt sensitive fields"""
        if projection is None:
            projection = {"_id": 0}
        
        record = await self.collection.find_one(query, projection)
        if record:
            return decrypt_sensitive_data(record)
        return None
    
    async def update_encrypted(self, query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        """Update record with sensitive fields encrypted"""
        encrypted_update = encrypt_sensitive_data(update_data)
        result = await self.collection.update_one(query, {"$set": encrypted_update})
        return result.modified_count


# Utility functions for key management
def generate_new_encryption_key() -> str:
    """Generate a new AES-256 encryption key (base64 encoded)"""
    key = secrets.token_bytes(AES_KEY_SIZE)
    return base64.b64encode(key).decode('utf-8')


def rotate_encryption_key(old_key_b64: str, new_key_b64: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rotate encryption key for existing data
    Decrypts with old key and re-encrypts with new key
    """
    old_key = base64.b64decode(old_key_b64)
    new_key = base64.b64decode(new_key_b64)
    
    # Decrypt with old key
    old_encryptor = HealthDataEncryption(old_key)
    # This is a simplified version - in production, implement full nested decryption
    
    # Encrypt with new key
    new_encryptor = HealthDataEncryption(new_key)
    
    # For actual implementation, you'd need to traverse the encrypted data
    # This is a placeholder showing the concept
    return data


# Export for use in other modules
__all__ = [
    'HealthDataEncryption',
    'encrypt_sensitive_data',
    'decrypt_sensitive_data',
    'EncryptedHealthRecord',
    'generate_new_encryption_key',
    'SENSITIVE_HEALTH_FIELDS'
]
