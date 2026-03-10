"""
Multi-Factor Authentication (MFA) System for DHA Compliance
Implements TOTP-based 2FA with optional SMS backup codes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone, timedelta
import uuid
import secrets
import hashlib
import hmac
import struct
import time
import base64
import os
from typing import Optional, List
from utils.auth import get_current_user, get_password_hash, verify_password, create_access_token
from dependencies import get_db

router = APIRouter(prefix="/mfa", tags=["Multi-Factor Authentication"])

# TOTP Settings
TOTP_INTERVAL = 30  # Time step in seconds
TOTP_DIGITS = 6     # Number of digits in TOTP code
TOTP_ALGORITHM = "sha1"
BACKUP_CODE_COUNT = 10

# Models
class MFASetupRequest(BaseModel):
    password: str  # Require password to enable MFA

class MFAEnableRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6)

class MFAVerifyRequest(BaseModel):
    user_id: str
    totp_code: str = Field(..., min_length=6, max_length=6)

class MFABackupCodeRequest(BaseModel):
    backup_code: str = Field(..., min_length=10, max_length=10)

class MFADisableRequest(BaseModel):
    password: str
    totp_code: str = Field(..., min_length=6, max_length=6)

class MFALoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

# TOTP Implementation
def generate_totp_secret() -> str:
    """Generate a random TOTP secret (base32 encoded)"""
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode('utf-8')

def generate_totp_uri(secret: str, email: str, issuer: str = "HealthTrack Pro") -> str:
    """Generate otpauth URI for QR code generation"""
    return f"otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

def get_totp_token(secret: str, counter: Optional[int] = None) -> str:
    """Generate TOTP token from secret"""
    if counter is None:
        counter = int(time.time()) // TOTP_INTERVAL
    
    # Decode base32 secret
    key = base64.b32decode(secret.upper())
    
    # Pack counter as 8-byte big-endian
    counter_bytes = struct.pack(">Q", counter)
    
    # HMAC-SHA1
    hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    
    # Dynamic truncation
    offset = hmac_digest[-1] & 0x0f
    code = struct.unpack(">I", hmac_digest[offset:offset+4])[0]
    code &= 0x7fffffff
    code %= 10 ** TOTP_DIGITS
    
    return str(code).zfill(TOTP_DIGITS)

def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verify TOTP code with time window tolerance"""
    current_counter = int(time.time()) // TOTP_INTERVAL
    
    # Check current and adjacent time windows
    for offset in range(-window, window + 1):
        if get_totp_token(secret, current_counter + offset) == code:
            return True
    return False

def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> List[str]:
    """Generate backup codes for MFA recovery"""
    return [secrets.token_hex(5).upper() for _ in range(count)]

def hash_backup_code(code: str) -> str:
    """Hash a backup code for secure storage"""
    return hashlib.sha256(code.encode()).hexdigest()


# API Endpoints

@router.get("/status")
async def get_mfa_status(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Check if MFA is enabled for current user"""
    user = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    mfa_enabled = user.get("mfa_enabled", False)
    mfa_setup_at = user.get("mfa_setup_at")
    
    return {
        "mfa_enabled": mfa_enabled,
        "mfa_setup_at": mfa_setup_at,
        "backup_codes_remaining": len(user.get("mfa_backup_codes_hash", [])) if mfa_enabled else 0,
        "last_verified": user.get("mfa_last_verified")
    }


@router.post("/setup")
async def setup_mfa(
    request: MFASetupRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Initialize MFA setup - generates secret and returns QR code URI"""
    user = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify password
    if not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Check if MFA already enabled
    if user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is already enabled. Disable it first to reconfigure.")
    
    # Generate TOTP secret
    secret = generate_totp_secret()
    
    # Store pending secret (not enabled yet)
    await db.users.update_one(
        {"id": current_user["user_id"]},
        {"$set": {
            "mfa_pending_secret": secret,
            "mfa_setup_initiated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Generate QR code URI
    qr_uri = generate_totp_uri(secret, user["email"])
    
    return {
        "message": "MFA setup initiated. Scan the QR code with your authenticator app and verify with a code.",
        "secret": secret,  # For manual entry
        "qr_uri": qr_uri,  # For QR code generation
        "instructions": [
            "1. Install an authenticator app (Google Authenticator, Authy, Microsoft Authenticator)",
            "2. Scan the QR code or manually enter the secret",
            "3. Enter the 6-digit code from your app to complete setup"
        ]
    }


@router.post("/enable")
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Complete MFA setup by verifying the TOTP code"""
    user = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for pending secret
    pending_secret = user.get("mfa_pending_secret")
    if not pending_secret:
        raise HTTPException(status_code=400, detail="No MFA setup in progress. Call /mfa/setup first.")
    
    # Verify TOTP code
    if not verify_totp(pending_secret, request.totp_code):
        raise HTTPException(status_code=400, detail="Invalid verification code. Please try again.")
    
    # Generate backup codes
    backup_codes = generate_backup_codes()
    backup_codes_hash = [hash_backup_code(code) for code in backup_codes]
    
    # Enable MFA
    await db.users.update_one(
        {"id": current_user["user_id"]},
        {
            "$set": {
                "mfa_enabled": True,
                "mfa_secret": pending_secret,
                "mfa_setup_at": datetime.now(timezone.utc).isoformat(),
                "mfa_backup_codes_hash": backup_codes_hash,
                "mfa_last_verified": datetime.now(timezone.utc).isoformat()
            },
            "$unset": {
                "mfa_pending_secret": "",
                "mfa_setup_initiated_at": ""
            }
        }
    )
    
    return {
        "message": "MFA has been successfully enabled for your account.",
        "backup_codes": backup_codes,
        "warning": "Save these backup codes in a secure location. Each code can only be used once.",
        "mfa_enabled": True
    }


@router.post("/verify")
async def verify_mfa_code(
    request: MFAVerifyRequest,
    db = Depends(get_db)
):
    """Verify MFA code during login (called after password verification)"""
    user = await db.users.find_one({"id": request.user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is not enabled for this user")
    
    mfa_secret = user.get("mfa_secret")
    if not mfa_secret:
        raise HTTPException(status_code=500, detail="MFA configuration error")
    
    # Verify TOTP code
    if not verify_totp(mfa_secret, request.totp_code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Update last verified timestamp
    await db.users.update_one(
        {"id": request.user_id},
        {"$set": {"mfa_last_verified": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Generate full access token
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"], "role": user.get("role", "user"), "mfa_verified": True}
    )
    
    return {
        "message": "MFA verification successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "user")
        }
    }


@router.post("/verify-backup")
async def verify_backup_code(
    request: MFABackupCodeRequest,
    user_id: str,
    db = Depends(get_db)
):
    """Verify MFA using backup code"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is not enabled for this user")
    
    backup_codes_hash = user.get("mfa_backup_codes_hash", [])
    code_hash = hash_backup_code(request.backup_code.upper())
    
    if code_hash not in backup_codes_hash:
        raise HTTPException(status_code=401, detail="Invalid backup code")
    
    # Remove used backup code
    backup_codes_hash.remove(code_hash)
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "mfa_backup_codes_hash": backup_codes_hash,
                "mfa_last_verified": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Generate full access token
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"], "role": user.get("role", "user"), "mfa_verified": True}
    )
    
    return {
        "message": "Backup code verified successfully",
        "access_token": access_token,
        "token_type": "bearer",
        "backup_codes_remaining": len(backup_codes_hash),
        "warning": f"You have {len(backup_codes_hash)} backup codes remaining." if len(backup_codes_hash) < 3 else None,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "user")
        }
    }


@router.post("/disable")
async def disable_mfa(
    request: MFADisableRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Disable MFA (requires password and current TOTP code)"""
    user = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    
    # Verify password
    if not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Verify TOTP code
    mfa_secret = user.get("mfa_secret")
    if not verify_totp(mfa_secret, request.totp_code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Disable MFA
    await db.users.update_one(
        {"id": current_user["user_id"]},
        {
            "$set": {"mfa_enabled": False},
            "$unset": {
                "mfa_secret": "",
                "mfa_backup_codes_hash": "",
                "mfa_setup_at": "",
                "mfa_last_verified": ""
            }
        }
    )
    
    return {
        "message": "MFA has been disabled for your account",
        "mfa_enabled": False
    }


@router.post("/regenerate-backup-codes")
async def regenerate_backup_codes(
    password: str,
    totp_code: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Regenerate backup codes (invalidates old ones)"""
    user = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA is not enabled")
    
    # Verify password
    if not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Verify TOTP code
    mfa_secret = user.get("mfa_secret")
    if not verify_totp(mfa_secret, totp_code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Generate new backup codes
    backup_codes = generate_backup_codes()
    backup_codes_hash = [hash_backup_code(code) for code in backup_codes]
    
    await db.users.update_one(
        {"id": current_user["user_id"]},
        {"$set": {"mfa_backup_codes_hash": backup_codes_hash}}
    )
    
    return {
        "message": "New backup codes generated. Old codes are now invalid.",
        "backup_codes": backup_codes,
        "warning": "Save these backup codes in a secure location. Each code can only be used once."
    }


@router.post("/login-with-mfa")
async def login_with_mfa(
    request: MFALoginRequest,
    db = Depends(get_db)
):
    """
    Enhanced login endpoint that handles MFA flow
    Step 1: Verify email/password
    Step 2: If MFA enabled, require TOTP code
    """
    # Find user
    user = await db.users.find_one({"email": request.email}, {"_id": 0})
    
    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    mfa_enabled = user.get("mfa_enabled", False)
    
    # If MFA not enabled, return token directly
    if not mfa_enabled:
        access_token = create_access_token(
            data={"sub": user["id"], "email": user["email"], "role": user.get("role", "user")}
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "mfa_required": False,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user.get("role", "user")
            }
        }
    
    # MFA is enabled - check if code provided
    if not request.totp_code:
        # Return partial auth requiring MFA
        return {
            "mfa_required": True,
            "user_id": user["id"],
            "message": "MFA verification required. Please provide your 6-digit code."
        }
    
    # Verify TOTP code
    mfa_secret = user.get("mfa_secret")
    if not verify_totp(mfa_secret, request.totp_code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    
    # Update last verified
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"mfa_last_verified": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Return full access token
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"], "role": user.get("role", "user"), "mfa_verified": True}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "mfa_required": False,
        "mfa_verified": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "user")
        }
    }
