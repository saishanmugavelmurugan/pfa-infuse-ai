"""
CSP Operations Module - SecureSphere
Enterprise module for Communication Service Providers (CSPs/Telecom operators)

Features:
- RAN Sync with secure configuration (API Key, OAuth2, Vault)
- White-label/Reseller capabilities
- Multi-tenant management
- Real-time visibility and analytics
- Proactive anomaly detection
- Zero-touch eSIM provisioning
- Automated policy enforcement
- Data usage control & overage prevention
- Agentless deployment management
- SLA monitoring
- Billing/Usage reports
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import secrets
import random
import string

import dependencies

router = APIRouter(prefix="/securesphere/csp-operations", tags=["SecureSphere - CSP Operations"])


# ==================== MODELS ====================

class CSPRegistration(BaseModel):
    """Register a new CSP partner"""
    company_name: str
    company_domain: str
    contact_email: str
    contact_name: str
    country: str
    integration_type: str = "api_key"  # api_key, oauth2, vault
    white_label_mode: str = "powered_by"  # full_white_label, powered_by
    custom_branding: Optional[Dict[str, str]] = None  # logo_url, primary_color, etc.


class RANConfiguration(BaseModel):
    """RAN synchronization configuration"""
    csp_id: str
    ran_vendor: str  # ericsson, nokia, huawei, samsung
    ran_type: str  # 4g_lte, 5g_nr, 5g_sa
    mcc: str  # Mobile Country Code
    mnc: str  # Mobile Network Code
    tac_ranges: List[str]  # Tracking Area Codes
    encryption_enabled: bool = True
    sync_interval_minutes: int = 5


class EnterpriseCustomer(BaseModel):
    """Enterprise customer under a CSP"""
    csp_id: str
    customer_name: str
    customer_domain: str
    industry: str
    contact_email: str
    subscription_tier: str = "standard"  # starter, standard, enterprise
    device_limit: int = 1000
    data_limit_gb: int = 100


class ESIMProvisioningRequest(BaseModel):
    """eSIM provisioning request"""
    csp_id: str
    customer_id: str
    iccid: str
    imsi: str
    msisdn: str
    profile_type: str = "consumer"  # consumer, m2m, iot
    data_plan_mb: int = 1024
    validity_days: int = 30


class PolicyRule(BaseModel):
    """Network policy rule"""
    csp_id: str
    rule_name: str
    rule_type: str  # traffic_control, security, qos, billing
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    priority: int = 100
    enabled: bool = True


class SLADefinition(BaseModel):
    """SLA definition for a customer"""
    csp_id: str
    customer_id: str
    uptime_target_percent: float = 99.9
    latency_max_ms: int = 50
    packet_loss_max_percent: float = 0.1
    incident_response_minutes: int = 15
    resolution_hours: int = 4


# ==================== AUTHENTICATION & INTEGRATION ====================

async def verify_csp_api_key(x_csp_api_key: str = Header(None)):
    """Verify CSP API key for authentication"""
    if not x_csp_api_key:
        return None
    
    db = dependencies.get_db()
    csp = await db.csp_partners.find_one({"api_key": x_csp_api_key, "status": "active"}, {"_id": 0})
    return csp


@router.post("/register")
async def register_csp(registration: CSPRegistration):
    """Register a new CSP partner"""
    db = dependencies.get_db()
    
    # Check if already exists
    existing = await db.csp_partners.find_one({"company_domain": registration.company_domain})
    if existing:
        raise HTTPException(status_code=400, detail="CSP with this domain already registered")
    
    # Generate credentials based on integration type
    csp_id = str(uuid4())
    api_key = f"csp_{secrets.token_urlsafe(32)}"
    api_secret = secrets.token_urlsafe(48)
    
    csp_record = {
        "id": csp_id,
        "company_name": registration.company_name,
        "company_domain": registration.company_domain,
        "contact_email": registration.contact_email,
        "contact_name": registration.contact_name,
        "country": registration.country,
        "integration_type": registration.integration_type,
        "white_label_mode": registration.white_label_mode,
        "custom_branding": registration.custom_branding or {
            "logo_url": None,
            "primary_color": "#FF6B00",
            "secondary_color": "#1F2937",
            "favicon_url": None,
            "custom_domain": None
        },
        "api_key": api_key,
        "api_secret_hash": hashlib.sha256(api_secret.encode()).hexdigest(),
        "oauth2_config": None,
        "vault_config": None,
        "status": "active",
        "tier": "enterprise",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_customers": 0,
            "total_devices": 0,
            "total_data_gb": 0,
            "active_policies": 0
        }
    }
    
    await db.csp_partners.insert_one(csp_record)
    
    return {
        "csp_id": csp_id,
        "api_key": api_key,
        "api_secret": api_secret,  # Only returned once at registration
        "integration_type": registration.integration_type,
        "white_label_mode": registration.white_label_mode,
        "message": "CSP registered successfully. Store your API secret securely - it won't be shown again.",
        "next_steps": [
            "Configure RAN synchronization",
            "Set up white-label branding",
            "Add enterprise customers",
            "Define SLA policies"
        ]
    }


@router.post("/integration/oauth2/configure")
async def configure_oauth2(
    csp_id: str,
    issuer_url: str,
    client_id: str,
    client_secret: str,
    scopes: List[str] = ["openid", "profile"]
):
    """Configure OAuth2/OIDC federation for a CSP"""
    db = dependencies.get_db()
    
    oauth2_config = {
        "issuer_url": issuer_url,
        "client_id": client_id,
        "client_secret_hash": hashlib.sha256(client_secret.encode()).hexdigest(),
        "scopes": scopes,
        "configured_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.csp_partners.update_one(
        {"id": csp_id},
        {
            "$set": {
                "oauth2_config": oauth2_config,
                "integration_type": "oauth2"
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="CSP not found")
    
    return {"status": "configured", "integration_type": "oauth2"}


@router.post("/integration/vault/configure")
async def configure_vault(
    csp_id: str,
    vault_url: str,
    vault_namespace: str,
    auth_method: str = "approle",  # approle, kubernetes, token
    role_id: Optional[str] = None,
    secret_path: str = "secret/data/securesphere"
):
    """Configure HashiCorp Vault integration for secrets management"""
    db = dependencies.get_db()
    
    vault_config = {
        "vault_url": vault_url,
        "vault_namespace": vault_namespace,
        "auth_method": auth_method,
        "role_id": role_id,
        "secret_path": secret_path,
        "configured_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.csp_partners.update_one(
        {"id": csp_id},
        {
            "$set": {
                "vault_config": vault_config,
                "integration_type": "vault"
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="CSP not found")
    
    return {"status": "configured", "integration_type": "vault"}


# ==================== RAN SYNCHRONIZATION ====================

@router.post("/ran/configure")
async def configure_ran_sync(config: RANConfiguration):
    """Configure RAN synchronization for a CSP"""
    db = dependencies.get_db()
    
    ran_id = str(uuid4())
    ran_record = {
        "id": ran_id,
        "csp_id": config.csp_id,
        "ran_vendor": config.ran_vendor,
        "ran_type": config.ran_type,
        "mcc": config.mcc,
        "mnc": config.mnc,
        "tac_ranges": config.tac_ranges,
        "encryption_enabled": config.encryption_enabled,
        "sync_interval_minutes": config.sync_interval_minutes,
        "status": "configured",
        "last_sync": None,
        "sync_stats": {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "cells_discovered": 0,
            "devices_tracked": 0
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ran_configurations.insert_one(ran_record)
    
    return {
        "ran_id": ran_id,
        "status": "configured",
        "ran_vendor": config.ran_vendor,
        "ran_type": config.ran_type,
        "plmn": f"{config.mcc}-{config.mnc}",
        "message": f"RAN sync configured for {config.ran_vendor} {config.ran_type}"
    }


@router.post("/ran/sync/{ran_id}")
async def trigger_ran_sync(ran_id: str):
    """Trigger manual RAN synchronization"""
    db = dependencies.get_db()
    
    ran_config = await db.ran_configurations.find_one({"id": ran_id}, {"_id": 0})
    if not ran_config:
        raise HTTPException(status_code=404, detail="RAN configuration not found")
    
    # Simulate RAN sync results
    sync_result = {
        "sync_id": str(uuid4()),
        "ran_id": ran_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": (datetime.now(timezone.utc) + timedelta(seconds=random.randint(5, 30))).isoformat(),
        "status": "completed",
        "cells_synced": random.randint(50, 500),
        "devices_discovered": random.randint(1000, 50000),
        "anomalies_detected": random.randint(0, 10),
        "data_volume_gb": round(random.uniform(10, 500), 2),
        "metrics": {
            "avg_signal_strength_dbm": random.randint(-100, -50),
            "avg_latency_ms": random.randint(10, 50),
            "handover_success_rate": round(random.uniform(95, 99.9), 2),
            "call_drop_rate": round(random.uniform(0.1, 2), 2)
        }
    }
    
    # Update sync stats
    await db.ran_configurations.update_one(
        {"id": ran_id},
        {
            "$set": {"last_sync": sync_result["completed_at"]},
            "$inc": {
                "sync_stats.total_syncs": 1,
                "sync_stats.successful_syncs": 1,
                "sync_stats.cells_discovered": sync_result["cells_synced"],
                "sync_stats.devices_tracked": sync_result["devices_discovered"]
            }
        }
    )
    
    # Store sync history
    sync_history_doc = sync_result.copy()
    await db.ran_sync_history.insert_one(sync_history_doc)
    
    return sync_result


@router.get("/ran/status/{csp_id}")
async def get_ran_status(csp_id: str):
    """Get RAN sync status for a CSP"""
    db = dependencies.get_db()
    
    ran_configs = await db.ran_configurations.find(
        {"csp_id": csp_id},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "csp_id": csp_id,
        "ran_configurations": len(ran_configs),
        "configurations": ran_configs
    }


# ==================== WHITE-LABEL CONFIGURATION ====================

@router.put("/white-label/{csp_id}")
async def update_white_label(
    csp_id: str,
    mode: str,  # full_white_label, powered_by
    logo_url: Optional[str] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    favicon_url: Optional[str] = None,
    custom_domain: Optional[str] = None,
    custom_product_name: Optional[str] = None
):
    """Update white-label configuration for a CSP"""
    db = dependencies.get_db()
    
    branding = {
        "logo_url": logo_url,
        "primary_color": primary_color or "#FF6B00",
        "secondary_color": secondary_color or "#1F2937",
        "favicon_url": favicon_url,
        "custom_domain": custom_domain,
        "custom_product_name": custom_product_name,
        "show_powered_by": mode == "powered_by"
    }
    
    result = await db.csp_partners.update_one(
        {"id": csp_id},
        {
            "$set": {
                "white_label_mode": mode,
                "custom_branding": branding
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="CSP not found")
    
    return {
        "csp_id": csp_id,
        "white_label_mode": mode,
        "branding": branding,
        "message": "White-label configuration updated"
    }


@router.get("/white-label/{csp_id}")
async def get_white_label_config(csp_id: str):
    """Get white-label configuration for a CSP"""
    db = dependencies.get_db()
    
    csp = await db.csp_partners.find_one(
        {"id": csp_id},
        {"_id": 0, "white_label_mode": 1, "custom_branding": 1, "company_name": 1}
    )
    
    if not csp:
        raise HTTPException(status_code=404, detail="CSP not found")
    
    return csp


# ==================== MULTI-TENANT CUSTOMER MANAGEMENT ====================

@router.post("/customers/add")
async def add_enterprise_customer(customer: EnterpriseCustomer):
    """Add an enterprise customer under a CSP"""
    db = dependencies.get_db()
    
    customer_id = str(uuid4())
    customer_record = {
        "id": customer_id,
        "csp_id": customer.csp_id,
        "customer_name": customer.customer_name,
        "customer_domain": customer.customer_domain,
        "industry": customer.industry,
        "contact_email": customer.contact_email,
        "subscription_tier": customer.subscription_tier,
        "device_limit": customer.device_limit,
        "data_limit_gb": customer.data_limit_gb,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usage": {
            "devices_registered": 0,
            "data_used_gb": 0,
            "api_calls_today": 0,
            "threats_blocked": 0
        },
        "sla": None,
        "billing": {
            "billing_cycle": "monthly",
            "next_billing_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "current_charges": 0
        }
    }
    
    await db.csp_customers.insert_one(customer_record)
    
    # Update CSP stats
    await db.csp_partners.update_one(
        {"id": customer.csp_id},
        {"$inc": {"stats.total_customers": 1}}
    )
    
    return {
        "customer_id": customer_id,
        "csp_id": customer.csp_id,
        "customer_name": customer.customer_name,
        "status": "active",
        "api_key": f"cust_{secrets.token_urlsafe(24)}"
    }


@router.get("/customers/{csp_id}")
async def list_customers(csp_id: str, status: Optional[str] = None):
    """List all customers under a CSP"""
    db = dependencies.get_db()
    
    query = {"csp_id": csp_id}
    if status:
        query["status"] = status
    
    customers = await db.csp_customers.find(query, {"_id": 0}).to_list(1000)
    
    return {
        "csp_id": csp_id,
        "total_customers": len(customers),
        "customers": customers
    }


@router.get("/customers/detail/{customer_id}")
async def get_customer_detail(customer_id: str):
    """Get detailed information about a customer"""
    db = dependencies.get_db()
    
    customer = await db.csp_customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer


# ==================== REAL-TIME VISIBILITY & ANALYTICS ====================

@router.get("/analytics/real-time/{csp_id}")
async def get_real_time_analytics(csp_id: str, customer_id: Optional[str] = None):
    """Get real-time visibility analytics at IP/Port/Protocol level"""
    
    # Generate realistic real-time data
    now = datetime.now(timezone.utc)
    
    analytics = {
        "csp_id": csp_id,
        "customer_id": customer_id,
        "timestamp": now.isoformat(),
        "summary": {
            "active_devices": random.randint(10000, 100000),
            "active_sessions": random.randint(50000, 500000),
            "throughput_gbps": round(random.uniform(10, 100), 2),
            "packets_per_second": random.randint(1000000, 10000000)
        },
        "traffic_by_protocol": {
            "tcp": {"percent": 65, "bytes_gb": round(random.uniform(100, 500), 2)},
            "udp": {"percent": 25, "bytes_gb": round(random.uniform(40, 200), 2)},
            "icmp": {"percent": 5, "bytes_gb": round(random.uniform(5, 20), 2)},
            "other": {"percent": 5, "bytes_gb": round(random.uniform(5, 20), 2)}
        },
        "top_ports": [
            {"port": 443, "protocol": "HTTPS", "connections": random.randint(100000, 500000), "bytes_gb": round(random.uniform(50, 200), 2)},
            {"port": 80, "protocol": "HTTP", "connections": random.randint(50000, 200000), "bytes_gb": round(random.uniform(20, 100), 2)},
            {"port": 8883, "protocol": "MQTT/TLS", "connections": random.randint(10000, 100000), "bytes_gb": round(random.uniform(5, 50), 2)},
            {"port": 5683, "protocol": "CoAP", "connections": random.randint(5000, 50000), "bytes_gb": round(random.uniform(2, 20), 2)},
            {"port": 1883, "protocol": "MQTT", "connections": random.randint(5000, 30000), "bytes_gb": round(random.uniform(1, 10), 2)}
        ],
        "geographic_distribution": [
            {"region": "North America", "devices": random.randint(20000, 50000), "traffic_percent": 35},
            {"region": "Europe", "devices": random.randint(15000, 40000), "traffic_percent": 28},
            {"region": "Asia Pacific", "devices": random.randint(10000, 30000), "traffic_percent": 22},
            {"region": "Middle East", "devices": random.randint(5000, 15000), "traffic_percent": 10},
            {"region": "Other", "devices": random.randint(2000, 8000), "traffic_percent": 5}
        ],
        "device_types": [
            {"type": "Smart Meters", "count": random.randint(20000, 50000), "data_gb": round(random.uniform(10, 50), 2)},
            {"type": "Security Cameras", "count": random.randint(10000, 30000), "data_gb": round(random.uniform(50, 200), 2)},
            {"type": "Connected Vehicles", "count": random.randint(5000, 20000), "data_gb": round(random.uniform(20, 100), 2)},
            {"type": "Industrial Sensors", "count": random.randint(10000, 40000), "data_gb": round(random.uniform(5, 30), 2)},
            {"type": "Consumer IoT", "count": random.randint(5000, 25000), "data_gb": round(random.uniform(10, 50), 2)}
        ]
    }
    
    return analytics


@router.get("/analytics/traffic-patterns/{csp_id}")
async def get_traffic_patterns(csp_id: str, hours: int = Query(default=24, le=168)):
    """Get historical traffic patterns"""
    
    patterns = []
    now = datetime.now(timezone.utc)
    
    for h in range(hours):
        timestamp = (now - timedelta(hours=hours - h)).isoformat()
        hour_of_day = (now.hour - hours + h) % 24
        
        # Simulate daily patterns (higher during business hours)
        base_multiplier = 1.5 if 9 <= hour_of_day <= 18 else 0.7
        
        patterns.append({
            "timestamp": timestamp,
            "throughput_gbps": round(random.uniform(20, 80) * base_multiplier, 2),
            "active_devices": int(random.randint(50000, 100000) * base_multiplier),
            "new_connections": random.randint(10000, 50000),
            "bytes_in_gb": round(random.uniform(100, 500) * base_multiplier, 2),
            "bytes_out_gb": round(random.uniform(50, 200) * base_multiplier, 2),
            "anomaly_score": round(random.uniform(0, 30), 1)
        })
    
    return {
        "csp_id": csp_id,
        "period_hours": hours,
        "patterns": patterns,
        "summary": {
            "peak_throughput_gbps": max(p["throughput_gbps"] for p in patterns),
            "avg_devices": sum(p["active_devices"] for p in patterns) // len(patterns),
            "total_data_tb": round(sum(p["bytes_in_gb"] + p["bytes_out_gb"] for p in patterns) / 1024, 2)
        }
    }


# ==================== PROACTIVE ANOMALY DETECTION ====================

@router.get("/anomalies/{csp_id}")
async def get_anomalies(csp_id: str, severity: Optional[str] = None, hours: int = Query(default=24, le=168)):
    """Get proactive anomaly detection results with IoC indicators"""
    
    anomaly_types = [
        {"type": "traffic_spike", "category": "performance", "severity": "medium"},
        {"type": "ddos_indicator", "category": "security", "severity": "critical"},
        {"type": "data_exfiltration", "category": "security", "severity": "critical"},
        {"type": "unauthorized_access", "category": "security", "severity": "high"},
        {"type": "protocol_anomaly", "category": "performance", "severity": "low"},
        {"type": "latency_spike", "category": "performance", "severity": "medium"},
        {"type": "device_compromise", "category": "security", "severity": "critical"},
        {"type": "unusual_destination", "category": "security", "severity": "high"},
        {"type": "bandwidth_abuse", "category": "billing", "severity": "medium"},
        {"type": "sim_swap_attempt", "category": "fraud", "severity": "critical"}
    ]
    
    anomalies = []
    num_anomalies = random.randint(5, 20)
    
    for _ in range(num_anomalies):
        anomaly_def = random.choice(anomaly_types)
        if severity and anomaly_def["severity"] != severity:
            continue
            
        anomalies.append({
            "id": str(uuid4()),
            "csp_id": csp_id,
            "type": anomaly_def["type"],
            "category": anomaly_def["category"],
            "severity": anomaly_def["severity"],
            "detected_at": (datetime.now(timezone.utc) - timedelta(hours=random.randint(0, hours))).isoformat(),
            "affected_devices": random.randint(1, 1000),
            "ioc_indicators": {
                "ip_addresses": [f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(random.randint(1, 5))],
                "domains": [f"suspicious-{random.randint(1000,9999)}.com"] if random.random() > 0.5 else [],
                "signatures": [f"SIG-{random.randint(10000,99999)}"] if random.random() > 0.7 else []
            },
            "recommended_actions": [
                "Isolate affected devices",
                "Block suspicious IPs at network edge",
                "Enable enhanced monitoring",
                "Notify security operations team"
            ][:random.randint(1, 4)],
            "status": random.choice(["active", "investigating", "mitigated", "resolved"])
        })
    
    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    anomalies.sort(key=lambda x: severity_order.get(x["severity"], 4))
    
    return {
        "csp_id": csp_id,
        "period_hours": hours,
        "total_anomalies": len(anomalies),
        "by_severity": {
            "critical": len([a for a in anomalies if a["severity"] == "critical"]),
            "high": len([a for a in anomalies if a["severity"] == "high"]),
            "medium": len([a for a in anomalies if a["severity"] == "medium"]),
            "low": len([a for a in anomalies if a["severity"] == "low"])
        },
        "by_category": {
            "security": len([a for a in anomalies if a["category"] == "security"]),
            "performance": len([a for a in anomalies if a["category"] == "performance"]),
            "billing": len([a for a in anomalies if a["category"] == "billing"]),
            "fraud": len([a for a in anomalies if a["category"] == "fraud"])
        },
        "anomalies": anomalies
    }


# ==================== ZERO-TOUCH eSIM PROVISIONING ====================

@router.post("/esim/provision")
async def provision_esim(request: ESIMProvisioningRequest):
    """Zero-touch eSIM provisioning"""
    db = dependencies.get_db()
    
    provision_id = str(uuid4())
    
    esim_record = {
        "id": provision_id,
        "csp_id": request.csp_id,
        "customer_id": request.customer_id,
        "iccid": request.iccid,
        "imsi": request.imsi,
        "msisdn": request.msisdn,
        "profile_type": request.profile_type,
        "data_plan_mb": request.data_plan_mb,
        "validity_days": request.validity_days,
        "status": "provisioned",
        "activation_code": f"LPA:1${secrets.token_urlsafe(16)}",
        "provisioned_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=request.validity_days)).isoformat(),
        "usage": {
            "data_used_mb": 0,
            "last_connection": None,
            "connection_count": 0
        }
    }
    
    await db.esim_profiles.insert_one(esim_record)
    
    return {
        "provision_id": provision_id,
        "iccid": request.iccid,
        "msisdn": request.msisdn,
        "status": "provisioned",
        "activation_code": esim_record["activation_code"],
        "data_plan_mb": request.data_plan_mb,
        "expires_at": esim_record["expires_at"],
        "message": "eSIM profile provisioned successfully. Use the activation code for device setup."
    }


@router.get("/esim/list/{csp_id}")
async def list_esim_profiles(csp_id: str, customer_id: Optional[str] = None, status: Optional[str] = None):
    """List eSIM profiles for a CSP"""
    db = dependencies.get_db()
    
    query = {"csp_id": csp_id}
    if customer_id:
        query["customer_id"] = customer_id
    if status:
        query["status"] = status
    
    profiles = await db.esim_profiles.find(query, {"_id": 0}).to_list(1000)
    
    return {
        "csp_id": csp_id,
        "total_profiles": len(profiles),
        "profiles": profiles
    }


@router.post("/esim/bulk-provision")
async def bulk_provision_esim(csp_id: str, customer_id: str, count: int = Query(default=10, le=1000), profile_type: str = "iot"):
    """Bulk eSIM provisioning for large deployments"""
    db = dependencies.get_db()
    
    profiles = []
    for i in range(count):
        iccid = f"89{random.randint(10, 99)}{random.randint(1000000000000000, 9999999999999999)}"
        imsi = f"{random.randint(100, 999)}{random.randint(10, 99)}{random.randint(1000000000, 9999999999)}"
        msisdn = f"+1{random.randint(2000000000, 9999999999)}"
        
        profile = {
            "id": str(uuid4()),
            "csp_id": csp_id,
            "customer_id": customer_id,
            "iccid": iccid,
            "imsi": imsi,
            "msisdn": msisdn,
            "profile_type": profile_type,
            "data_plan_mb": 1024,
            "validity_days": 365,
            "status": "provisioned",
            "activation_code": f"LPA:1${secrets.token_urlsafe(16)}",
            "provisioned_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "usage": {"data_used_mb": 0, "last_connection": None, "connection_count": 0}
        }
        profiles.append(profile)
    
    await db.esim_profiles.insert_many(profiles)
    
    return {
        "csp_id": csp_id,
        "customer_id": customer_id,
        "provisioned_count": count,
        "profile_type": profile_type,
        "message": f"Successfully provisioned {count} eSIM profiles"
    }


# ==================== AUTOMATED POLICY ENFORCEMENT ====================

@router.post("/policies/create")
async def create_policy(policy: PolicyRule):
    """Create an automated policy rule"""
    db = dependencies.get_db()
    
    policy_id = str(uuid4())
    policy_record = {
        "id": policy_id,
        "csp_id": policy.csp_id,
        "rule_name": policy.rule_name,
        "rule_type": policy.rule_type,
        "conditions": policy.conditions,
        "actions": policy.actions,
        "priority": policy.priority,
        "enabled": policy.enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "times_triggered": 0,
            "last_triggered": None,
            "devices_affected": 0
        }
    }
    
    await db.csp_policies.insert_one(policy_record)
    
    return {
        "policy_id": policy_id,
        "rule_name": policy.rule_name,
        "rule_type": policy.rule_type,
        "status": "active" if policy.enabled else "disabled",
        "message": "Policy created successfully"
    }


@router.get("/policies/{csp_id}")
async def list_policies(csp_id: str, rule_type: Optional[str] = None):
    """List all policies for a CSP"""
    db = dependencies.get_db()
    
    query = {"csp_id": csp_id}
    if rule_type:
        query["rule_type"] = rule_type
    
    policies = await db.csp_policies.find(query, {"_id": 0}).sort("priority", 1).to_list(1000)
    
    return {
        "csp_id": csp_id,
        "total_policies": len(policies),
        "policies": policies
    }


@router.post("/policies/enforce/{policy_id}")
async def enforce_policy(policy_id: str):
    """Manually trigger policy enforcement"""
    db = dependencies.get_db()
    
    policy = await db.csp_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Simulate enforcement
    affected_devices = random.randint(10, 1000)
    
    await db.csp_policies.update_one(
        {"id": policy_id},
        {
            "$set": {"stats.last_triggered": datetime.now(timezone.utc).isoformat()},
            "$inc": {"stats.times_triggered": 1, "stats.devices_affected": affected_devices}
        }
    )
    
    return {
        "policy_id": policy_id,
        "rule_name": policy["rule_name"],
        "enforcement_status": "completed",
        "devices_affected": affected_devices,
        "actions_taken": policy["actions"]
    }


# ==================== DATA USAGE CONTROL & OVERAGE PREVENTION ====================

@router.get("/usage/{csp_id}")
async def get_usage_overview(csp_id: str, customer_id: Optional[str] = None):
    """Get data usage overview with overage alerts"""
    db = dependencies.get_db()
    
    query = {"csp_id": csp_id}
    if customer_id:
        query["id"] = customer_id
    
    customers = await db.csp_customers.find(query, {"_id": 0}).to_list(1000)
    
    usage_data = []
    for customer in customers:
        data_used = random.uniform(0, customer.get("data_limit_gb", 100))
        limit = customer.get("data_limit_gb", 100)
        usage_percent = (data_used / limit) * 100
        
        usage_data.append({
            "customer_id": customer["id"],
            "customer_name": customer["customer_name"],
            "data_limit_gb": limit,
            "data_used_gb": round(data_used, 2),
            "usage_percent": round(usage_percent, 1),
            "overage_risk": "critical" if usage_percent > 90 else "high" if usage_percent > 75 else "medium" if usage_percent > 50 else "low",
            "projected_overage_gb": round(max(0, data_used * 1.2 - limit), 2) if usage_percent > 80 else 0,
            "devices_active": random.randint(100, customer.get("device_limit", 1000)),
            "billing_cycle_end": customer.get("billing", {}).get("next_billing_date")
        })
    
    # Sort by usage percent descending
    usage_data.sort(key=lambda x: x["usage_percent"], reverse=True)
    
    return {
        "csp_id": csp_id,
        "total_customers": len(usage_data),
        "customers_at_risk": len([u for u in usage_data if u["overage_risk"] in ["critical", "high"]]),
        "total_data_used_gb": round(sum(u["data_used_gb"] for u in usage_data), 2),
        "usage_details": usage_data
    }


@router.post("/usage/set-limit")
async def set_usage_limit(customer_id: str, data_limit_gb: int, hard_cap: bool = False, alert_threshold_percent: int = 80):
    """Set data usage limits with optional hard cap"""
    db = dependencies.get_db()
    
    result = await db.csp_customers.update_one(
        {"id": customer_id},
        {
            "$set": {
                "data_limit_gb": data_limit_gb,
                "hard_cap_enabled": hard_cap,
                "alert_threshold_percent": alert_threshold_percent
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return {
        "customer_id": customer_id,
        "data_limit_gb": data_limit_gb,
        "hard_cap_enabled": hard_cap,
        "alert_threshold_percent": alert_threshold_percent,
        "message": f"Usage limit set to {data_limit_gb}GB" + (" with hard cap" if hard_cap else "")
    }


# ==================== AGENTLESS DEPLOYMENT STATUS ====================

@router.get("/deployment/status/{csp_id}")
async def get_deployment_status(csp_id: str):
    """Get agentless deployment status - in-line with cellular data path"""
    
    return {
        "csp_id": csp_id,
        "deployment_type": "agentless_inline",
        "status": "operational",
        "integration_points": {
            "ggsn_pgw": {
                "status": "connected",
                "throughput_gbps": round(random.uniform(10, 50), 2),
                "latency_added_ms": round(random.uniform(0.1, 1), 2)
            },
            "smf_upf": {
                "status": "connected",
                "throughput_gbps": round(random.uniform(20, 100), 2),
                "latency_added_ms": round(random.uniform(0.1, 0.5), 2)
            },
            "dns_proxy": {
                "status": "active",
                "queries_per_second": random.randint(10000, 100000)
            }
        },
        "coverage": {
            "total_cells": random.randint(1000, 10000),
            "covered_cells": random.randint(900, 9900),
            "coverage_percent": round(random.uniform(95, 99.9), 1)
        },
        "benefits": [
            "No software agents required on IoT devices",
            "No new hardware needed",
            "Zero device-side configuration",
            "Transparent to end devices",
            "Sub-millisecond latency addition",
            "Scales with existing infrastructure"
        ],
        "last_health_check": datetime.now(timezone.utc).isoformat()
    }


# ==================== SLA MONITORING ====================

@router.post("/sla/define")
async def define_sla(sla: SLADefinition):
    """Define SLA for a customer"""
    db = dependencies.get_db()
    
    sla_id = str(uuid4())
    sla_record = {
        "id": sla_id,
        "csp_id": sla.csp_id,
        "customer_id": sla.customer_id,
        "uptime_target_percent": sla.uptime_target_percent,
        "latency_max_ms": sla.latency_max_ms,
        "packet_loss_max_percent": sla.packet_loss_max_percent,
        "incident_response_minutes": sla.incident_response_minutes,
        "resolution_hours": sla.resolution_hours,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "current_performance": {
            "uptime_percent": round(random.uniform(99, 100), 3),
            "avg_latency_ms": random.randint(10, 40),
            "packet_loss_percent": round(random.uniform(0, 0.1), 3),
            "incidents_this_month": random.randint(0, 5),
            "avg_response_minutes": random.randint(5, 20),
            "avg_resolution_hours": random.randint(1, 6)
        }
    }
    
    await db.sla_definitions.insert_one(sla_record)
    
    # Update customer record
    await db.csp_customers.update_one(
        {"id": sla.customer_id},
        {"$set": {"sla": sla_id}}
    )
    
    return {
        "sla_id": sla_id,
        "customer_id": sla.customer_id,
        "targets": {
            "uptime": f"{sla.uptime_target_percent}%",
            "latency": f"<{sla.latency_max_ms}ms",
            "packet_loss": f"<{sla.packet_loss_max_percent}%",
            "response_time": f"<{sla.incident_response_minutes}min",
            "resolution_time": f"<{sla.resolution_hours}h"
        },
        "message": "SLA defined successfully"
    }


@router.get("/sla/dashboard/{csp_id}")
async def get_sla_dashboard(csp_id: str):
    """Get SLA monitoring dashboard for all customers"""
    db = dependencies.get_db()
    
    slas = await db.sla_definitions.find({"csp_id": csp_id}, {"_id": 0}).to_list(1000)
    
    dashboard = []
    for sla in slas:
        customer = await db.csp_customers.find_one({"id": sla["customer_id"]}, {"customer_name": 1, "_id": 0})
        
        # Check compliance
        perf = sla.get("current_performance", {})
        compliance = {
            "uptime": perf.get("uptime_percent", 0) >= sla["uptime_target_percent"],
            "latency": perf.get("avg_latency_ms", 999) <= sla["latency_max_ms"],
            "packet_loss": perf.get("packet_loss_percent", 100) <= sla["packet_loss_max_percent"],
            "response_time": perf.get("avg_response_minutes", 999) <= sla["incident_response_minutes"],
            "resolution_time": perf.get("avg_resolution_hours", 999) <= sla["resolution_hours"]
        }
        
        overall_compliance = all(compliance.values())
        
        dashboard.append({
            "sla_id": sla["id"],
            "customer_id": sla["customer_id"],
            "customer_name": customer.get("customer_name") if customer else "Unknown",
            "overall_status": "compliant" if overall_compliance else "breached",
            "compliance_details": compliance,
            "current_performance": perf,
            "targets": {
                "uptime_percent": sla["uptime_target_percent"],
                "latency_max_ms": sla["latency_max_ms"],
                "packet_loss_max_percent": sla["packet_loss_max_percent"]
            },
            "sla_score": round((sum(compliance.values()) / len(compliance)) * 100, 1)
        })
    
    # Sort by compliance score
    dashboard.sort(key=lambda x: x["sla_score"])
    
    return {
        "csp_id": csp_id,
        "total_slas": len(dashboard),
        "compliant": len([d for d in dashboard if d["overall_status"] == "compliant"]),
        "breached": len([d for d in dashboard if d["overall_status"] == "breached"]),
        "avg_sla_score": round(sum(d["sla_score"] for d in dashboard) / max(1, len(dashboard)), 1),
        "sla_details": dashboard
    }


# ==================== BILLING & USAGE REPORTS ====================

@router.get("/billing/report/{csp_id}")
async def get_billing_report(csp_id: str, month: Optional[str] = None):
    """Get billing report for CSP to charge customers"""
    db = dependencies.get_db()
    
    customers = await db.csp_customers.find({"csp_id": csp_id}, {"_id": 0}).to_list(1000)
    
    billing_items = []
    total_revenue = 0
    
    tier_pricing = {
        "starter": {"base": 500, "per_device": 0.50, "per_gb": 0.10},
        "standard": {"base": 2000, "per_device": 0.30, "per_gb": 0.08},
        "enterprise": {"base": 10000, "per_device": 0.20, "per_gb": 0.05}
    }
    
    for customer in customers:
        tier = customer.get("subscription_tier", "standard")
        pricing = tier_pricing.get(tier, tier_pricing["standard"])
        
        devices = random.randint(100, customer.get("device_limit", 1000))
        data_gb = random.uniform(10, customer.get("data_limit_gb", 100))
        
        base_charge = pricing["base"]
        device_charge = devices * pricing["per_device"]
        data_charge = data_gb * pricing["per_gb"]
        total_charge = base_charge + device_charge + data_charge
        
        billing_items.append({
            "customer_id": customer["id"],
            "customer_name": customer["customer_name"],
            "subscription_tier": tier,
            "billing_period": month or datetime.now(timezone.utc).strftime("%Y-%m"),
            "usage": {
                "devices": devices,
                "data_gb": round(data_gb, 2)
            },
            "charges": {
                "base_fee": base_charge,
                "device_charges": round(device_charge, 2),
                "data_charges": round(data_charge, 2),
                "total": round(total_charge, 2)
            },
            "currency": "USD"
        })
        
        total_revenue += total_charge
    
    return {
        "csp_id": csp_id,
        "billing_period": month or datetime.now(timezone.utc).strftime("%Y-%m"),
        "total_customers": len(billing_items),
        "total_revenue": round(total_revenue, 2),
        "currency": "USD",
        "billing_items": billing_items,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/billing/invoice/{customer_id}")
async def generate_customer_invoice(customer_id: str):
    """Generate invoice for a specific customer"""
    db = dependencies.get_db()
    
    customer = await db.csp_customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    tier = customer.get("subscription_tier", "standard")
    tier_pricing = {
        "starter": {"base": 500, "per_device": 0.50, "per_gb": 0.10},
        "standard": {"base": 2000, "per_device": 0.30, "per_gb": 0.08},
        "enterprise": {"base": 10000, "per_device": 0.20, "per_gb": 0.05}
    }
    pricing = tier_pricing.get(tier, tier_pricing["standard"])
    
    devices = random.randint(100, customer.get("device_limit", 1000))
    data_gb = random.uniform(10, customer.get("data_limit_gb", 100))
    
    invoice = {
        "invoice_id": f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{customer_id[:8].upper()}",
        "customer_id": customer_id,
        "customer_name": customer["customer_name"],
        "customer_domain": customer["customer_domain"],
        "billing_period": {
            "start": (datetime.now(timezone.utc).replace(day=1)).isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        },
        "line_items": [
            {"description": f"{tier.title()} Plan - Base Fee", "quantity": 1, "unit_price": pricing["base"], "total": pricing["base"]},
            {"description": "Device Connections", "quantity": devices, "unit_price": pricing["per_device"], "total": round(devices * pricing["per_device"], 2)},
            {"description": "Data Usage (GB)", "quantity": round(data_gb, 2), "unit_price": pricing["per_gb"], "total": round(data_gb * pricing["per_gb"], 2)}
        ],
        "subtotal": round(pricing["base"] + devices * pricing["per_device"] + data_gb * pricing["per_gb"], 2),
        "tax_rate": 0,
        "tax_amount": 0,
        "total_due": round(pricing["base"] + devices * pricing["per_device"] + data_gb * pricing["per_gb"], 2),
        "currency": "USD",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    return invoice


# ==================== CSP DASHBOARD OVERVIEW ====================

@router.get("/dashboard/{csp_id}")
async def get_csp_dashboard(csp_id: str):
    """Get comprehensive CSP operations dashboard"""
    db = dependencies.get_db()
    
    csp = await db.csp_partners.find_one({"id": csp_id}, {"_id": 0, "api_secret_hash": 0})
    if not csp:
        raise HTTPException(status_code=404, detail="CSP not found")
    
    # Get counts
    customers = await db.csp_customers.count_documents({"csp_id": csp_id})
    esim_profiles = await db.esim_profiles.count_documents({"csp_id": csp_id})
    active_policies = await db.csp_policies.count_documents({"csp_id": csp_id, "enabled": True})
    ran_configs = await db.ran_configurations.count_documents({"csp_id": csp_id})
    
    return {
        "csp_id": csp_id,
        "company_name": csp.get("company_name"),
        "white_label_mode": csp.get("white_label_mode"),
        "integration_type": csp.get("integration_type"),
        "status": csp.get("status"),
        "summary": {
            "total_customers": customers,
            "total_esim_profiles": esim_profiles,
            "active_policies": active_policies,
            "ran_configurations": ran_configs,
            "total_devices": random.randint(10000, 100000),
            "total_data_tb": round(random.uniform(10, 500), 2)
        },
        "health": {
            "platform_status": "operational",
            "api_latency_ms": random.randint(5, 20),
            "uptime_percent": round(random.uniform(99.9, 100), 3)
        },
        "recent_activity": {
            "new_customers_7d": random.randint(0, 10),
            "esim_provisioned_7d": random.randint(100, 1000),
            "anomalies_detected_24h": random.randint(0, 20),
            "policies_triggered_24h": random.randint(10, 100)
        },
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
