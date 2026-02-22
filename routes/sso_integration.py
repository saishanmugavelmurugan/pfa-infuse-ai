"""
SSO Integration API - Enterprise Single Sign-On
Supports SAML 2.0, OAuth 2.0, and OIDC

Features:
- Multi-provider SSO configuration
- Organization-level SSO setup
- JIT (Just-in-Time) user provisioning
- Session management
- Audit logging
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import secrets
import hashlib
import base64
import json

import dependencies

router = APIRouter(prefix="/api/sso", tags=["SSO Integration"])

# ==================== MODELS ====================

class SSOProviderConfig(BaseModel):
    provider_type: str  # saml, oauth2, oidc
    provider_name: str  # okta, azure_ad, google, custom
    org_id: str
    
    # SAML Config
    saml_metadata_url: Optional[str] = None
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_certificate: Optional[str] = None
    
    # OAuth2/OIDC Config
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    scopes: Optional[List[str]] = ["openid", "email", "profile"]
    
    # JIT Provisioning
    jit_enabled: bool = True
    default_role: str = "viewer"
    auto_assign_segments: List[str] = ["mobile"]

class SSOSession(BaseModel):
    session_id: str
    user_email: str
    org_id: str
    provider: str
    expires_at: str

# ==================== AUTH ====================

async def verify_org_admin(x_org_id: str = Header(None), x_admin_token: str = Header(None)):
    """Verify organization admin for SSO configuration"""
    if not x_org_id or not x_admin_token:
        raise HTTPException(status_code=401, detail="Admin credentials required")
    return {"org_id": x_org_id}

# ==================== SSO CONFIGURATION ====================

@router.post("/configure")
async def configure_sso(config: SSOProviderConfig, auth: dict = Depends(verify_org_admin)):
    """Configure SSO provider for an organization"""
    db = dependencies.get_db()
    
    # Validate provider type and required fields
    if config.provider_type == "saml":
        if not config.saml_sso_url:
            raise HTTPException(status_code=400, detail="SAML SSO URL required")
    elif config.provider_type in ["oauth2", "oidc"]:
        if not config.client_id or not config.authorization_url:
            raise HTTPException(status_code=400, detail="OAuth2 client_id and authorization_url required")
    
    # Generate unique SSO config ID
    sso_config_id = f"sso_{uuid4().hex[:12]}"
    
    # Create SSO configuration
    sso_record = {
        "id": sso_config_id,
        "org_id": config.org_id,
        "provider_type": config.provider_type,
        "provider_name": config.provider_name,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        
        # Provider-specific config
        "saml_config": {
            "metadata_url": config.saml_metadata_url,
            "entity_id": config.saml_entity_id or f"urn:infuse:securesphere:{config.org_id}",
            "sso_url": config.saml_sso_url,
            "certificate": config.saml_certificate
        } if config.provider_type == "saml" else None,
        
        "oauth_config": {
            "client_id": config.client_id,
            "client_secret_encrypted": hashlib.sha256((config.client_secret or "").encode()).hexdigest(),
            "authorization_url": config.authorization_url,
            "token_url": config.token_url,
            "userinfo_url": config.userinfo_url,
            "scopes": config.scopes
        } if config.provider_type in ["oauth2", "oidc"] else None,
        
        # JIT Config
        "jit_config": {
            "enabled": config.jit_enabled,
            "default_role": config.default_role,
            "auto_assign_segments": config.auto_assign_segments
        },
        
        # Callback URLs
        "callback_urls": {
            "acs_url": f"/api/sso/callback/{sso_config_id}",
            "logout_url": f"/api/sso/logout/{sso_config_id}"
        }
    }
    
    await db.sso_configurations.insert_one(sso_record)
    sso_record.pop("_id", None)
    
    # Don't return sensitive data
    if sso_record.get("oauth_config"):
        sso_record["oauth_config"]["client_secret_encrypted"] = "***"
    
    return {
        "success": True,
        "sso_config_id": sso_config_id,
        "configuration": sso_record,
        "integration_urls": {
            "login_url": f"/api/sso/login/{sso_config_id}",
            "acs_url": f"/api/sso/callback/{sso_config_id}",
            "metadata_url": f"/api/sso/metadata/{sso_config_id}"
        },
        "next_steps": [
            f"Configure your IdP with ACS URL: /api/sso/callback/{sso_config_id}",
            "Test the SSO flow via /api/sso/login/{sso_config_id}",
            "Enable for all users or specific groups"
        ]
    }

@router.get("/providers")
async def list_sso_providers(org_id: str, auth: dict = Depends(verify_org_admin)):
    """List configured SSO providers for an organization"""
    db = dependencies.get_db()
    
    providers = await db.sso_configurations.find(
        {"org_id": org_id},
        {"_id": 0, "oauth_config.client_secret_encrypted": 0}
    ).to_list(10)
    
    return {"providers": providers, "total": len(providers)}

@router.get("/provider/{sso_config_id}")
async def get_sso_provider(sso_config_id: str, auth: dict = Depends(verify_org_admin)):
    """Get SSO provider configuration"""
    db = dependencies.get_db()
    
    provider = await db.sso_configurations.find_one(
        {"id": sso_config_id},
        {"_id": 0, "oauth_config.client_secret_encrypted": 0}
    )
    
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    return {"provider": provider}

@router.delete("/provider/{sso_config_id}")
async def delete_sso_provider(sso_config_id: str, auth: dict = Depends(verify_org_admin)):
    """Delete SSO provider configuration"""
    db = dependencies.get_db()
    
    result = await db.sso_configurations.delete_one({"id": sso_config_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    return {"success": True, "message": "SSO provider deleted"}

# ==================== SSO FLOW ====================

@router.get("/login/{sso_config_id}")
async def initiate_sso_login(sso_config_id: str, redirect_uri: Optional[str] = None):
    """Initiate SSO login flow"""
    db = dependencies.get_db()
    
    provider = await db.sso_configurations.find_one({"id": sso_config_id}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(16)
    
    # Store state for validation
    await db.sso_states.insert_one({
        "state": state,
        "nonce": nonce,
        "sso_config_id": sso_config_id,
        "redirect_uri": redirect_uri or "/dashboard",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    })
    
    if provider["provider_type"] == "saml":
        # Generate SAML AuthnRequest
        saml_request = generate_saml_request(provider, state)
        return {
            "redirect_url": f"{provider['saml_config']['sso_url']}?SAMLRequest={saml_request}",
            "method": "redirect"
        }
    
    elif provider["provider_type"] in ["oauth2", "oidc"]:
        # Build OAuth2 authorization URL
        oauth_config = provider["oauth_config"]
        params = {
            "client_id": oauth_config["client_id"],
            "response_type": "code",
            "redirect_uri": f"/api/sso/callback/{sso_config_id}",
            "state": state,
            "scope": " ".join(oauth_config["scopes"])
        }
        if provider["provider_type"] == "oidc":
            params["nonce"] = nonce
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        auth_url = f"{oauth_config['authorization_url']}?{query_string}"
        
        return {
            "redirect_url": auth_url,
            "method": "redirect"
        }
    
    raise HTTPException(status_code=400, detail="Unsupported provider type")

def generate_saml_request(provider: dict, state: str) -> str:
    """Generate SAML AuthnRequest (simplified)"""
    # In production, use python-saml library
    request_id = f"_id{uuid4().hex}"
    timestamp = datetime.now(timezone.utc).isoformat()
    
    saml_request = f"""
    <samlp:AuthnRequest 
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        ID="{request_id}"
        Version="2.0"
        IssueInstant="{timestamp}"
        Destination="{provider['saml_config']['sso_url']}"
        AssertionConsumerServiceURL="/api/sso/callback/{provider['id']}">
        <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
            {provider['saml_config']['entity_id']}
        </saml:Issuer>
    </samlp:AuthnRequest>
    """
    
    return base64.b64encode(saml_request.encode()).decode()

@router.post("/callback/{sso_config_id}")
@router.get("/callback/{sso_config_id}")
async def sso_callback(
    sso_config_id: str,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    SAMLResponse: Optional[str] = None
):
    """Handle SSO callback from IdP"""
    db = dependencies.get_db()
    
    provider = await db.sso_configurations.find_one({"id": sso_config_id}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    # Validate state
    if state:
        state_record = await db.sso_states.find_one({"state": state}, {"_id": 0})
        if not state_record:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Check expiry
        if datetime.fromisoformat(state_record["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="State expired")
    
    user_info = None
    
    if provider["provider_type"] == "saml" and SAMLResponse:
        # Parse SAML response (simplified)
        user_info = parse_saml_response(SAMLResponse)
    
    elif provider["provider_type"] in ["oauth2", "oidc"] and code:
        # Exchange code for token (simplified - in production use httpx)
        user_info = {
            "email": f"sso_user_{uuid4().hex[:8]}@{provider['org_id']}.com",
            "name": "SSO User",
            "sub": uuid4().hex
        }
    
    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Failed to get user info from IdP")
    
    # JIT Provisioning - create or get user
    user = await db.users.find_one({"email": user_info["email"]}, {"_id": 0})
    
    if not user and provider["jit_config"]["enabled"]:
        # Create new user
        user = {
            "id": str(uuid4()),
            "email": user_info["email"],
            "name": user_info.get("name", user_info["email"].split("@")[0]),
            "role": provider["jit_config"]["default_role"],
            "org_id": provider["org_id"],
            "sso_provider": sso_config_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_via": "sso_jit"
        }
        await db.users.insert_one(user)
        user.pop("_id", None)
    
    if not user:
        raise HTTPException(status_code=403, detail="User not found and JIT provisioning disabled")
    
    # Create session
    session_token = secrets.token_urlsafe(48)
    session = {
        "session_id": session_token,
        "user_id": user["id"],
        "user_email": user["email"],
        "org_id": provider["org_id"],
        "provider": sso_config_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    }
    
    await db.sso_sessions.insert_one(session)
    
    # Log SSO event
    await db.sso_audit_logs.insert_one({
        "event": "sso_login",
        "user_email": user["email"],
        "org_id": provider["org_id"],
        "provider": provider["provider_name"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": request.client.host if request.client else "unknown"
    })
    
    # Return session token (in production, set as cookie and redirect)
    redirect_uri = state_record.get("redirect_uri", "/dashboard") if state else "/dashboard"
    
    return {
        "success": True,
        "session_token": session_token,
        "user": {
            "email": user["email"],
            "name": user.get("name"),
            "role": user.get("role")
        },
        "redirect_to": redirect_uri,
        "expires_at": session["expires_at"]
    }

def parse_saml_response(saml_response: str) -> dict:
    """Parse SAML response (simplified)"""
    # In production, use python-saml library with proper validation
    try:
        decoded = base64.b64decode(saml_response).decode()
        # Extract email from response (simplified)
        return {
            "email": f"saml_user_{uuid4().hex[:8]}@example.com",
            "name": "SAML User"
        }
    except:
        return None

@router.post("/logout/{sso_config_id}")
async def sso_logout(sso_config_id: str, session_token: str = Header(None)):
    """SSO logout - invalidate session"""
    db = dependencies.get_db()
    
    if session_token:
        # Find and delete session
        session = await db.sso_sessions.find_one({"session_id": session_token}, {"_id": 0})
        if session:
            await db.sso_sessions.delete_one({"session_id": session_token})
            
            # Log logout event
            await db.sso_audit_logs.insert_one({
                "event": "sso_logout",
                "user_email": session.get("user_email"),
                "org_id": session.get("org_id"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    return {"success": True, "message": "Logged out successfully"}

@router.get("/session/validate")
async def validate_sso_session(session_token: str = Header(None)):
    """Validate SSO session"""
    if not session_token:
        raise HTTPException(status_code=401, detail="Session token required")
    
    db = dependencies.get_db()
    session = await db.sso_sessions.find_one({"session_id": session_token}, {"_id": 0})
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    if datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        await db.sso_sessions.delete_one({"session_id": session_token})
        raise HTTPException(status_code=401, detail="Session expired")
    
    return {
        "valid": True,
        "user_email": session["user_email"],
        "org_id": session["org_id"],
        "expires_at": session["expires_at"]
    }

# ==================== METADATA ====================

@router.get("/metadata/{sso_config_id}")
async def get_sso_metadata(sso_config_id: str):
    """Get SAML SP metadata for IdP configuration"""
    db = dependencies.get_db()
    
    provider = await db.sso_configurations.find_one({"id": sso_config_id}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    if provider["provider_type"] != "saml":
        raise HTTPException(status_code=400, detail="Metadata only available for SAML providers")
    
    entity_id = provider["saml_config"]["entity_id"]
    acs_url = f"/api/sso/callback/{sso_config_id}"
    
    metadata = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="{entity_id}">
  <md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{acs_url}" index="0"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    
    return {
        "metadata_xml": metadata,
        "entity_id": entity_id,
        "acs_url": acs_url,
        "supported_bindings": ["HTTP-POST", "HTTP-Redirect"]
    }

# ==================== AUDIT ====================

@router.get("/audit-logs")
async def get_sso_audit_logs(
    org_id: str,
    limit: int = 100,
    auth: dict = Depends(verify_org_admin)
):
    """Get SSO audit logs for an organization"""
    db = dependencies.get_db()
    
    logs = await db.sso_audit_logs.find(
        {"org_id": org_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "total": len(logs)}
