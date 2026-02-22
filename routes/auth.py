from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone, timedelta
import uuid
import secrets
import os
from utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from dependencies import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Models
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(default="user", pattern="^(user|doctor|admin)$")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)

class ForgotPasswordResponse(BaseModel):
    message: str
    reset_link: str = None  # Only included in development/testing

# Routes
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_dict = {
        "id": str(uuid.uuid4()),
        "name": user_data.name,
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_dict)
    
    # Return user without password
    return UserResponse(
        id=user_dict["id"],
        name=user_dict["name"],
        email=user_dict["email"],
        role=user_dict["role"],
        created_at=user_dict["created_at"]
    )

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db = Depends(get_db)):
    """Login user and return JWT token"""
    # Find user
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    print(user)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"], "role": user["role"]}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get current user information"""
    user = await db.users.find_one({"id": current_user["user_id"]}, {"_id": 0})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        created_at=user["created_at"]
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db = Depends(get_db)):
    """
    Request password reset. Generates a reset token and returns a reset link.
    In production, this would send an email. For testing, the reset link is returned directly.
    """
    # Find user by email
    user = await db.users.find_one({"email": request.email}, {"_id": 0})
    
    # Always return success to prevent email enumeration attacks
    # But only create token if user exists
    if user:
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store reset token with expiry (1 hour)
        reset_data = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "email": request.email,
            "token": reset_token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Remove any existing reset tokens for this user
        await db.password_resets.delete_many({"email": request.email})
        
        # Store new reset token
        await db.password_resets.insert_one(reset_data)
        
        # Get frontend URL for reset link - use CORS_ORIGINS or fall back to backend URL
        cors_origins = os.environ.get("CORS_ORIGINS", "*")
        if cors_origins and cors_origins != "*":
            frontend_url = cors_origins.split(",")[0].strip()
        else:
            # Fall back to extracting from request or use a reasonable default
            frontend_url = os.environ.get("FRONTEND_URL", "")
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        # In production, send email here using SendGrid/Twilio
        # For now, return the reset link directly for testing
        print(f"[PASSWORD RESET] Reset link for {request.email}: {reset_link}")
        
        return ForgotPasswordResponse(
            message="If an account exists with this email, a password reset link has been sent.",
            reset_link=reset_link  # Remove this in production
        )
    
    # Return same message even if user doesn't exist (security)
    return ForgotPasswordResponse(
        message="If an account exists with this email, a password reset link has been sent."
    )

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db = Depends(get_db)):
    """
    Reset password using the token from forgot-password.
    """
    # Find reset token
    reset_record = await db.password_resets.find_one({
        "token": request.token,
        "used": False
    }, {"_id": 0})
    
    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token is expired
    expires_at = datetime.fromisoformat(reset_record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )
    
    # Update user's password
    new_password_hash = get_password_hash(request.new_password)
    result = await db.users.update_one(
        {"id": reset_record["user_id"]},
        {"$set": {
            "password_hash": new_password_hash,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Mark token as used
    await db.password_resets.update_one(
        {"token": request.token},
        {"$set": {"used": True}}
    )
    
    return {"message": "Password has been reset successfully. You can now login with your new password."}
