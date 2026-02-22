"""
Enterprise SSO (Single Sign-On) Integration
Supports: SAML 2.0, OAuth 2.0, Azure AD, Okta
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import os
import base64
import hashlib
import hmac
import json

router = APIRouter(prefix="/api/enterprise/sso", tags=["Enterprise SSO"])

# Get database
from dependencies import get_database


# Models
class SSOProviderConfig(BaseModel):
    provider_type: str = Field(..., description="Type: saml, oauth, azure_ad, okta")
    name: str = Field(..., description="Display name for the provider")
    enabled: bool = True
    # SAML specific
    entity_id: Optional[str] = None
    sso_url: Optional[str] = None
    certificate: Optional[str] = None
    # OAuth/OIDC specific
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None
    userinfo_url: Optional[str] = None
    scopes: Optional[List[str]] = ["openid", "profile", "email"]
    # Azure AD specific
    tenant_id: Optional[str] = None
    # Okta specific
    okta_domain: Optional[str] = None


class SSOSession(BaseModel):
    session_id: str
    user_id: str
    provider: str
    created_at: str
    expires_at: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# SSO Provider Templates
SSO_PROVIDER_TEMPLATES = {
    "saml": {
        "name": "SAML 2.0",
        "required_fields": ["entity_id", "sso_url", "certificate"],
        "description": "Enterprise SAML 2.0 integration for SSO"
    },
    "oauth": {
        "name": "OAuth 2.0 / OIDC",
        "required_fields": ["client_id", "client_secret", "authorization_url", "token_url"],
        "description": "Generic OAuth 2.0 / OpenID Connect integration"
    },
    "azure_ad": {
        "name": "Microsoft Azure AD",
        "required_fields": ["tenant_id", "client_id", "client_secret"],
        "description": "Microsoft Azure Active Directory integration"
    },
    "okta": {
        "name": "Okta",
        "required_fields": ["okta_domain", "client_id", "client_secret"],
        "description": "Okta Workforce Identity integration"
    }
}


@router.get("/providers/templates")
async def get_sso_templates():
    """Get available SSO provider templates"""
    return {
        "templates": SSO_PROVIDER_TEMPLATES,
        "supported_providers": list(SSO_PROVIDER_TEMPLATES.keys())
    }


@router.post("/providers")
async def create_sso_provider(config: SSOProviderConfig, db=Depends(get_database)):
    """Create a new SSO provider configuration"""
    if config.provider_type not in SSO_PROVIDER_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Invalid provider type. Supported: {list(SSO_PROVIDER_TEMPLATES.keys())}")
    
    provider_id = str(uuid4())
    provider_data = {
        "id": provider_id,
        "provider_type": config.provider_type,
        "name": config.name,
        "enabled": config.enabled,
        "config": config.dict(exclude={"provider_type", "name", "enabled"}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sso_providers.insert_one(provider_data)
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "sso.provider.created",
        "resource_type": "sso_provider",
        "resource_id": provider_id,
        "details": {"provider_type": config.provider_type, "name": config.name},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"id": provider_id, "message": "SSO provider created successfully", "provider": provider_data}


@router.get("/providers")
async def list_sso_providers(db=Depends(get_database)):
    """List all configured SSO providers"""
    providers = await db.sso_providers.find({}, {"_id": 0}).to_list(100)
    return {"providers": providers, "total": len(providers)}


@router.get("/providers/{provider_id}")
async def get_sso_provider(provider_id: str, db=Depends(get_database)):
    """Get SSO provider details"""
    provider = await db.sso_providers.find_one({"id": provider_id}, {"_id": 0})
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    return provider


@router.put("/providers/{provider_id}")
async def update_sso_provider(provider_id: str, config: SSOProviderConfig, db=Depends(get_database)):
    """Update SSO provider configuration"""
    existing = await db.sso_providers.find_one({"id": provider_id})
    if not existing:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    update_data = {
        "name": config.name,
        "enabled": config.enabled,
        "config": config.dict(exclude={"provider_type", "name", "enabled"}),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sso_providers.update_one({"id": provider_id}, {"$set": update_data})
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "sso.provider.updated",
        "resource_type": "sso_provider",
        "resource_id": provider_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "SSO provider updated successfully"}


@router.delete("/providers/{provider_id}")
async def delete_sso_provider(provider_id: str, db=Depends(get_database)):
    """Delete SSO provider"""
    result = await db.sso_providers.delete_one({"id": provider_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "sso.provider.deleted",
        "resource_type": "sso_provider",
        "resource_id": provider_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "SSO provider deleted successfully"}


@router.post("/providers/{provider_id}/toggle")
async def toggle_sso_provider(provider_id: str, db=Depends(get_database)):
    """Enable or disable SSO provider"""
    provider = await db.sso_providers.find_one({"id": provider_id})
    if not provider:
        raise HTTPException(status_code=404, detail="SSO provider not found")
    
    new_status = not provider.get("enabled", True)
    await db.sso_providers.update_one(
        {"id": provider_id},
        {"$set": {"enabled": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"enabled": new_status, "message": f"SSO provider {'enabled' if new_status else 'disabled'}"}


# SAML Endpoints
@router.get("/saml/metadata/{provider_id}")
async def get_saml_metadata(provider_id: str, db=Depends(get_database)):
    """Get SAML Service Provider metadata"""
    provider = await db.sso_providers.find_one({"id": provider_id, "provider_type": "saml"})
    if not provider:
        raise HTTPException(status_code=404, detail="SAML provider not found")
    
    # Generate SP metadata XML
    entity_id = f"https://infuse.net.in/sso/saml/{provider_id}"
    acs_url = f"https://infuse.net.in/api/enterprise/sso/saml/acs/{provider_id}"
    
    metadata = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{acs_url}" index="0" isDefault="true"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    
    return {"metadata": metadata, "entity_id": entity_id, "acs_url": acs_url}


@router.post("/saml/acs/{provider_id}")
async def saml_assertion_consumer(provider_id: str, request: Request, db=Depends(get_database)):
    """SAML Assertion Consumer Service endpoint"""
    provider = await db.sso_providers.find_one({"id": provider_id, "provider_type": "saml", "enabled": True})
    if not provider:
        raise HTTPException(status_code=404, detail="SAML provider not found or disabled")
    
    # In production, this would validate the SAML response
    # For now, return a placeholder response
    return {
        "status": "sso_callback_received",
        "provider_id": provider_id,
        "message": "SAML assertion processing - configure IdP to complete setup"
    }


# OAuth/OIDC Endpoints
@router.get("/oauth/authorize/{provider_id}")
async def oauth_authorize(provider_id: str, redirect_uri: str, db=Depends(get_database)):
    """Initiate OAuth authorization flow"""
    provider = await db.sso_providers.find_one({"id": provider_id, "enabled": True})
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found or disabled")
    
    config = provider.get("config", {})
    provider_type = provider.get("provider_type")
    
    # Build authorization URL based on provider type
    if provider_type == "azure_ad":
        tenant_id = config.get("tenant_id")
        auth_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
    elif provider_type == "okta":
        okta_domain = config.get("okta_domain")
        auth_url = f"https://{okta_domain}/oauth2/default/v1/authorize"
    else:
        auth_url = config.get("authorization_url")
    
    if not auth_url:
        raise HTTPException(status_code=400, detail="Authorization URL not configured")
    
    # Generate state for CSRF protection
    state = base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    # Store state in session
    await db.sso_states.insert_one({
        "state": state,
        "provider_id": provider_id,
        "redirect_uri": redirect_uri,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    })
    
    scopes = config.get("scopes", ["openid", "profile", "email"])
    
    authorization_url = (
        f"{auth_url}?"
        f"client_id={config.get('client_id')}&"
        f"response_type=code&"
        f"redirect_uri={redirect_uri}&"
        f"scope={' '.join(scopes)}&"
        f"state={state}"
    )
    
    return {"authorization_url": authorization_url, "state": state}


@router.post("/oauth/callback/{provider_id}")
async def oauth_callback(provider_id: str, code: str, state: str, db=Depends(get_database)):
    """OAuth callback endpoint"""
    # Verify state
    stored_state = await db.sso_states.find_one({"state": state, "provider_id": provider_id})
    if not stored_state:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    # Delete used state
    await db.sso_states.delete_one({"state": state})
    
    provider = await db.sso_providers.find_one({"id": provider_id, "enabled": True})
    if not provider:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    
    # In production, exchange code for tokens here
    return {
        "status": "callback_received",
        "provider_id": provider_id,
        "message": "OAuth code received - token exchange would occur here"
    }


# SSO Sessions
@router.get("/sessions")
async def list_sso_sessions(user_id: Optional[str] = None, limit: int = 50, db=Depends(get_database)):
    """List active SSO sessions"""
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    sessions = await db.sso_sessions.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"sessions": sessions, "total": len(sessions)}


@router.delete("/sessions/{session_id}")
async def revoke_sso_session(session_id: str, db=Depends(get_database)):
    """Revoke an SSO session"""
    result = await db.sso_sessions.delete_one({"session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "sso.session.revoked",
        "resource_type": "sso_session",
        "resource_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Session revoked successfully"}


@router.post("/sessions/revoke-all/{user_id}")
async def revoke_all_user_sessions(user_id: str, db=Depends(get_database)):
    """Revoke all SSO sessions for a user"""
    result = await db.sso_sessions.delete_many({"user_id": user_id})
    
    # Log audit event
    await db.audit_logs.insert_one({
        "id": str(uuid4()),
        "event_type": "sso.sessions.revoked_all",
        "resource_type": "user",
        "resource_id": user_id,
        "details": {"sessions_revoked": result.deleted_count},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"Revoked {result.deleted_count} sessions"}
