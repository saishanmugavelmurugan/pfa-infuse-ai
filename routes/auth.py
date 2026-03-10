from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid
import secrets
import os
import httpx
import asyncio
import logging
from utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from dependencies import get_db

# Import security alerts (lazy import to avoid circular dependencies)
async def _check_and_alert_new_login(*args, **kwargs):
    """Lazy import wrapper for security alerts"""
    from services.security_alerts import check_and_alert_new_login
    return await check_and_alert_new_login(*args, **kwargs)

# GeoIP cache to reduce API calls
_geoip_cache = {}
_geoip_cache_ttl = 3600  # 1 hour TTL

async def get_location_from_ip(ip_address: str) -> str:
    """Get location from IP address using free GeoIP service"""
    # Skip private/local IPs
    if ip_address in ["unknown", "127.0.0.1", "localhost"] or ip_address.startswith(("10.", "192.168.", "172.")):
        return "Local Network"
    
    # Check cache first
    cache_key = ip_address.split(".")[0:3]  # Cache by /24 subnet
    cache_key = ".".join(cache_key)
    
    if cache_key in _geoip_cache:
        cached_time, cached_location = _geoip_cache[cache_key]
        if (datetime.now(timezone.utc).timestamp() - cached_time) < _geoip_cache_ttl:
            return cached_location
    
    try:
        # Use ip-api.com (free, no API key required, 45 requests/minute)
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"http://ip-api.com/json/{ip_address}?fields=status,city,country")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    city = data.get("city", "")
                    country = data.get("country", "")
                    
                    if city and country:
                        location = f"{city}, {country}"
                    elif country:
                        location = country
                    else:
                        location = "Unknown"
                    
                    # Cache the result
                    _geoip_cache[cache_key] = (datetime.now(timezone.utc).timestamp(), location)
                    return location
    except Exception as e:
        logging.warning(f"GeoIP lookup failed for {ip_address}: {e}")
    
    return "Unknown"

# Helper function to get client IP address
def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers or connection"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"

# Helper function to mask IP address for privacy
def mask_ip(ip: str) -> str:
    """Mask last octet of IP for privacy"""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    return ip

# Helper function to parse user agent
def parse_user_agent(user_agent: str) -> str:
    """Parse user agent to get device/browser info"""
    if not user_agent:
        return "Unknown device"
    
    # Browser detection
    browser = "Unknown"
    if "Chrome" in user_agent and "Edg" not in user_agent:
        browser = "Chrome"
    elif "Firefox" in user_agent:
        browser = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser = "Safari"
    elif "Edg" in user_agent:
        browser = "Edge"
    elif "MSIE" in user_agent or "Trident" in user_agent:
        browser = "IE"
    
    # OS detection
    os_name = "Unknown"
    if "Windows" in user_agent:
        os_name = "Windows"
    elif "Mac OS" in user_agent or "Macintosh" in user_agent:
        os_name = "MacOS"
    elif "Linux" in user_agent:
        os_name = "Linux"
    elif "Android" in user_agent:
        os_name = "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        os_name = "iOS"
    
    return f"{browser} on {os_name}"

# Helper function to log login attempt
async def log_login_attempt(
    db, 
    user_id: str, 
    email: str,
    ip_address: str, 
    user_agent: str, 
    success: bool,
    session_id: str = None
):
    """Log a login attempt to the database with GeoIP location"""
    # Get location from IP (async)
    location = await get_location_from_ip(ip_address)
    
    login_record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "email": email,
        "ip_address": ip_address,
        "masked_ip": mask_ip(ip_address),
        "device": parse_user_agent(user_agent),
        "user_agent": user_agent,
        "status": "success" if success else "failed",
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": location
    }
    await db.login_history.insert_one(login_record)

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
    mfa_code: str = None  # Optional MFA code for 2FA

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    mfa_required: bool = False  # Indicates if MFA verification is needed

class MFARequiredResponse(BaseModel):
    mfa_required: bool = True
    user_id: str
    message: str = "MFA verification required. Please provide your 6-digit code."

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

@router.post("/login")
async def login(credentials: UserLogin, request: Request, db = Depends(get_db)):
    """
    Login user and return JWT token.
    If MFA is enabled, requires mfa_code parameter.
    Returns mfa_required=True if MFA is enabled but code not provided.
    """
    # Get client info for logging
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    print(db.name)
    # Find user
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    print(user)
    if not user or not verify_password(credentials.password, user.get("password_hash", "")):
        # Log failed attempt if user exists
        if user:
            await log_login_attempt(db, user["id"], credentials.email, client_ip, user_agent, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if MFA is enabled for this user
    mfa_enabled = user.get("mfa_enabled", False)
    
    if mfa_enabled:
        # MFA is enabled - check if code was provided
        if not credentials.mfa_code:
            # Return MFA required response
            return {
                "mfa_required": True,
                "user_id": user["id"],
                "message": "MFA verification required. Please provide your 6-digit code.",
                "access_token": None,
                "token_type": "bearer",
                "user": None
            }
        
        # Verify MFA code
        mfa_secret = user.get("mfa_secret")
        if not mfa_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MFA configuration error. Please contact support."
            )
        
        # Import MFA verification function
        from routes.mfa import verify_totp, hash_backup_code
        
        # Try TOTP code first
        if not verify_totp(mfa_secret, credentials.mfa_code):
            # Try backup code
            backup_codes_hash = user.get("mfa_backup_codes_hash", [])
            code_hash = hash_backup_code(credentials.mfa_code.upper())
            
            if code_hash in backup_codes_hash:
                # Valid backup code - remove it (one-time use)
                backup_codes_hash.remove(code_hash)
                await db.users.update_one(
                    {"id": user["id"]},
                    {"$set": {"mfa_backup_codes_hash": backup_codes_hash}}
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code"
                )
        
        # Update last verified timestamp
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"mfa_last_verified": datetime.now(timezone.utc).isoformat()}}
        )
    
    # Create access token with MFA verified flag
    session_id = str(uuid.uuid4())
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "session_id": session_id
    }
    if mfa_enabled:
        token_data["mfa_verified"] = True
    
    access_token = create_access_token(data=token_data)
    
    # Get location from IP for both login history and session
    location = await get_location_from_ip(client_ip)
    
    # Log successful login attempt (location already fetched)
    login_record = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "email": credentials.email,
        "ip_address": client_ip,
        "masked_ip": mask_ip(client_ip),
        "device": parse_user_agent(user_agent),
        "user_agent": user_agent,
        "status": "success",
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": location
    }
    await db.login_history.insert_one(login_record)
    
    # Create/update active session with location
    session_record = {
        "id": session_id,
        "user_id": user["id"],
        "device": parse_user_agent(user_agent),
        "device_type": "mobile" if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent else "desktop",
        "ip_address": client_ip,
        "masked_ip": mask_ip(client_ip),
        "user_agent": user_agent,
        "location": location,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_active": datetime.now(timezone.utc).isoformat(),
        "is_current": True
    }
    await db.active_sessions.insert_one(session_record)
    
    # Update user's last login timestamp
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Check for new location/device and send security alert if needed (non-blocking)
    asyncio.create_task(_check_and_alert_new_login(
        db=db,
        user_id=user["id"],
        user_email=user["email"],
        user_name=user["name"],
        device=parse_user_agent(user_agent),
        location=location,
        ip_address=mask_ip(client_ip),
        timestamp=datetime.now(timezone.utc).isoformat()
    ))
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "mfa_required": False,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "user"),
            "mfa_enabled": mfa_enabled
        }
    }

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


# =============================================================================
# SECURITY DASHBOARD ENDPOINTS
# =============================================================================

class LoginHistoryResponse(BaseModel):
    id: str
    timestamp: str
    ip_address: str
    location: str
    device: str
    status: str
    is_current: bool = False

class ActiveSessionResponse(BaseModel):
    id: str
    device: str
    device_type: str
    ip_address: str
    location: str
    last_active: str
    is_current: bool = False

class SecurityOverviewResponse(BaseModel):
    mfa_enabled: bool
    password_last_changed: Optional[str] = None
    password_strength: str = "strong"
    last_login: Optional[str] = None
    total_logins_30d: int = 0
    failed_login_attempts: int = 0
    account_created: Optional[str] = None
    security_score: int = 50
    login_history: List[dict] = []
    active_sessions: List[dict] = []


@router.get("/security-overview")
async def get_security_overview(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get comprehensive security overview for the current user"""
    user_id = current_user["user_id"]
    
    # Get user details
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get login history (last 20 entries)
    login_cursor = db.login_history.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(20)
    login_history = await login_cursor.to_list(20)
    
    # Format login history for response
    formatted_history = []
    for record in login_history:
        formatted_history.append({
            "id": record.get("id", ""),
            "timestamp": record.get("timestamp", ""),
            "ip_address": record.get("masked_ip", record.get("ip_address", "unknown")),
            "location": record.get("location", "Unknown"),
            "device": record.get("device", "Unknown device"),
            "status": record.get("status", "unknown"),
            "is_current": False
        })
    
    # Get active sessions
    sessions_cursor = db.active_sessions.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("last_active", -1)
    active_sessions = await sessions_cursor.to_list(10)
    
    # Format sessions for response
    formatted_sessions = []
    current_session_id = current_user.get("session_id")
    for session in active_sessions:
        formatted_sessions.append({
            "id": session.get("id", ""),
            "device": session.get("device", "Unknown device"),
            "device_type": session.get("device_type", "desktop"),
            "ip_address": session.get("masked_ip", session.get("ip_address", "unknown")),
            "location": session.get("location", "Unknown"),
            "last_active": session.get("last_active", ""),
            "is_current": session.get("id") == current_session_id
        })
    
    # Mark current session in history if exists
    if formatted_history and current_session_id:
        for record in formatted_history:
            if record.get("session_id") == current_session_id:
                record["is_current"] = True
                break
    
    # Calculate statistics
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    total_logins_30d = await db.login_history.count_documents({
        "user_id": user_id,
        "status": "success",
        "timestamp": {"$gte": thirty_days_ago}
    })
    
    failed_attempts = await db.login_history.count_documents({
        "user_id": user_id,
        "status": "failed",
        "timestamp": {"$gte": thirty_days_ago}
    })
    
    # Calculate security score
    security_score = 50  # Base score
    if user.get("mfa_enabled"):
        security_score += 30
    if failed_attempts == 0:
        security_score += 10
    elif failed_attempts < 3:
        security_score += 5
    # Strong password assumed
    security_score += 10
    security_score = min(100, security_score)
    
    return {
        "mfa_enabled": user.get("mfa_enabled", False),
        "password_last_changed": user.get("password_changed_at", user.get("updated_at")),
        "password_strength": "strong",
        "last_login": user.get("last_login"),
        "total_logins_30d": total_logins_30d,
        "failed_login_attempts": failed_attempts,
        "account_created": user.get("created_at"),
        "security_score": security_score,
        "login_history": formatted_history,
        "active_sessions": formatted_sessions
    }


@router.get("/login-history")
async def get_login_history(
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get login history for the current user"""
    user_id = current_user["user_id"]
    
    # Get login history
    cursor = db.login_history.find(
        {"user_id": user_id},
        {"_id": 0, "user_agent": 0, "ip_address": 0}  # Exclude sensitive fields, use masked_ip
    ).sort("timestamp", -1).limit(min(limit, 100))
    
    history = await cursor.to_list(min(limit, 100))
    
    # Use masked IP in response
    for record in history:
        record["ip_address"] = record.pop("masked_ip", "xxx.xxx.xxx.xxx")
    
    return {"login_history": history, "total": len(history)}


@router.get("/sessions")
async def get_active_sessions(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get active sessions for the current user"""
    user_id = current_user["user_id"]
    current_session_id = current_user.get("session_id")
    
    # Get active sessions
    cursor = db.active_sessions.find(
        {"user_id": user_id},
        {"_id": 0, "user_agent": 0, "ip_address": 0}  # Use masked_ip instead
    ).sort("last_active", -1)
    
    sessions = await cursor.to_list(20)
    
    # Mark current session and use masked IP
    for session in sessions:
        session["is_current"] = session.get("id") == current_session_id
        session["ip_address"] = session.pop("masked_ip", "xxx.xxx.xxx.xxx")
    
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/sessions/{session_id}")
async def terminate_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Terminate a specific session"""
    user_id = current_user["user_id"]
    current_session_id = current_user.get("session_id")
    
    # Prevent terminating current session
    if session_id == current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot terminate your current session. Use logout instead."
        )
    
    # Find and delete the session
    result = await db.active_sessions.delete_one({
        "id": session_id,
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {"message": "Session terminated successfully", "session_id": session_id}


@router.post("/sessions/terminate-all")
async def terminate_all_other_sessions(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Terminate all sessions except the current one"""
    user_id = current_user["user_id"]
    current_session_id = current_user.get("session_id")
    
    # Delete all sessions except current
    result = await db.active_sessions.delete_many({
        "user_id": user_id,
        "id": {"$ne": current_session_id}
    })
    
    return {
        "message": f"Terminated {result.deleted_count} other sessions",
        "terminated_count": result.deleted_count
    }


@router.get("/security-alert-preview")
async def preview_security_alert_email(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Preview the security alert email template (for testing/debugging)"""
    from services.security_alerts import SecurityEmailService
    
    service = SecurityEmailService()
    html_content, text_content = service._generate_new_login_email(
        user_name="Test User",
        device="Chrome on Windows",
        location="Dubai, UAE",
        ip_address="192.168.xxx.xxx",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    return {
        "html": html_content,
        "text": text_content,
        "email_configured": service.configured
    }


@router.get("/known-locations")
async def get_known_login_locations(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get list of known login locations/devices for the current user"""
    user_id = current_user["user_id"]
    
    locations = await db.known_login_locations.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("last_seen", -1).to_list(50)
    
    # Add an id field if not present (use combination of location+device)
    for loc in locations:
        if "id" not in loc:
            loc["id"] = f"{loc.get('location', 'unknown')}_{loc.get('device', 'unknown')}".replace(" ", "_").lower()[:50]
    
    return {
        "known_locations": locations,
        "total": len(locations)
    }


@router.delete("/known-locations/clear-all")
async def clear_all_trusted_locations(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Clear all trusted locations/devices for the user"""
    user_id = current_user["user_id"]
    
    result = await db.known_login_locations.delete_many({
        "user_id": user_id
    })
    
    return {
        "message": f"Cleared {result.deleted_count} trusted locations",
        "deleted_count": result.deleted_count
    }


@router.delete("/known-locations/{location_id}")
async def remove_trusted_location(
    location_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Remove a trusted location/device from the user's list"""
    user_id = current_user["user_id"]
    
    # Try to find by id field first, then by location+device combo
    result = await db.known_login_locations.delete_one({
        "user_id": user_id,
        "id": location_id
    })
    
    if result.deleted_count == 0:
        # Try matching by reconstructed ID from location+device
        locations = await db.known_login_locations.find(
            {"user_id": user_id},
            {"_id": 0}
        ).to_list(100)
        
        for loc in locations:
            generated_id = f"{loc.get('location', 'unknown')}_{loc.get('device', 'unknown')}".replace(" ", "_").lower()[:50]
            if generated_id == location_id:
                await db.known_login_locations.delete_one({
                    "user_id": user_id,
                    "location": loc.get("location"),
                    "device": loc.get("device")
                })
                return {"message": "Trusted location removed successfully", "id": location_id}
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trusted location not found"
        )
    
    return {"message": "Trusted location removed successfully", "id": location_id}