"""
Mobile Protection Module - SecureSphere
Comprehensive mobile device protection with QR linking, SMS verification,
and real-time threat protection.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import random
import string
import base64
import json

import dependencies

router = APIRouter(prefix="/securesphere/mobile-protection", tags=["SecureSphere - Mobile Protection"])


# ==================== MODELS ====================

class MobileDeviceRegistration(BaseModel):
    """Register a mobile device for protection"""
    device_name: str
    device_type: str  # android, ios
    os_version: str
    manufacturer: str
    model: str
    phone_number: Optional[str] = None
    imei: Optional[str] = None
    owner_id: str


class QRLinkRequest(BaseModel):
    """Request QR code for device linking"""
    owner_id: str
    device_type: str = "android"  # android, ios


class SMSVerification(BaseModel):
    """SMS verification request"""
    phone_number: str
    device_id: str


class OTPVerification(BaseModel):
    """OTP verification"""
    phone_number: str
    otp_code: str
    device_id: str


class URLScanRequest(BaseModel):
    """URL scan request from mobile"""
    device_id: str
    url: str
    source: str = "sms"  # sms, browser, app


class AppPermissionReport(BaseModel):
    """App permission report from device"""
    device_id: str
    app_package: str
    app_name: str
    permissions: List[str]
    is_system_app: bool = False


class NetworkTrafficReport(BaseModel):
    """Network traffic report from device"""
    device_id: str
    connections: List[Dict[str, Any]]
    timestamp: Optional[str] = None


# ==================== THREAT DATABASES ====================

KNOWN_PHISHING_DOMAINS = [
    "secure-bank-login.com", "paypa1.com", "amaz0n-verify.com",
    "faceb00k-security.com", "g00gle-alert.com", "app1e-id.com",
    "netf1ix-update.com", "whatsapp-verify.net", "instagram-help.org"
]

SUSPICIOUS_PATTERNS = [
    "verify-account", "urgent-action", "suspended-account",
    "confirm-identity", "prize-winner", "lottery-claim",
    "free-gift", "click-here-now", "act-fast"
]

DANGEROUS_PERMISSIONS = {
    "android.permission.READ_SMS": {"risk": "high", "reason": "Can read your SMS messages"},
    "android.permission.SEND_SMS": {"risk": "high", "reason": "Can send SMS without your knowledge"},
    "android.permission.READ_CONTACTS": {"risk": "medium", "reason": "Can access your contacts"},
    "android.permission.ACCESS_FINE_LOCATION": {"risk": "medium", "reason": "Can track your precise location"},
    "android.permission.RECORD_AUDIO": {"risk": "high", "reason": "Can record audio"},
    "android.permission.CAMERA": {"risk": "medium", "reason": "Can access camera"},
    "android.permission.READ_CALL_LOG": {"risk": "high", "reason": "Can read call history"},
    "android.permission.WRITE_EXTERNAL_STORAGE": {"risk": "low", "reason": "Can write to storage"},
    "android.permission.INTERNET": {"risk": "low", "reason": "Can access internet"},
    "android.permission.RECEIVE_BOOT_COMPLETED": {"risk": "medium", "reason": "Starts automatically"},
    "android.permission.SYSTEM_ALERT_WINDOW": {"risk": "high", "reason": "Can draw over other apps"},
    "android.permission.REQUEST_INSTALL_PACKAGES": {"risk": "critical", "reason": "Can install other apps"},
    "android.permission.BIND_ACCESSIBILITY_SERVICE": {"risk": "critical", "reason": "Full device control"}
}

MALICIOUS_IPS = [
    "185.220.101.", "91.121.87.", "45.33.32.", "104.131.0.",
    "192.42.116.", "178.62.197.", "138.197.148."
]


# ==================== QR CODE & DEVICE LINKING ====================

@router.post("/qr/generate")
async def generate_qr_link(request: QRLinkRequest):
    """Generate QR code data for device linking"""
    db = dependencies.get_db()
    
    # Create a unique link token
    link_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    # QR data structure
    qr_data = {
        "action": "link_device",
        "token": link_token,
        "platform": "securesphere",
        "owner_id": request.owner_id,
        "device_type": request.device_type,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    }
    
    # Store the pending link
    await db.pending_device_links.insert_one({
        "id": str(uuid4()),
        "token": link_token,
        "owner_id": request.owner_id,
        "device_type": request.device_type,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": qr_data["expires_at"]
    })
    
    # Base64 encode for QR
    qr_string = base64.b64encode(json.dumps(qr_data).encode()).decode()
    
    return {
        "qr_data": qr_string,
        "qr_content": qr_data,
        "link_token": link_token,
        "expires_in_minutes": 15,
        "instructions": [
            "1. Open SecureSphere app on your mobile device",
            "2. Go to Settings > Link Device",
            "3. Scan this QR code",
            "4. Verify with SMS OTP"
        ]
    }


@router.post("/qr/validate")
async def validate_qr_link(token: str, device_info: MobileDeviceRegistration):
    """Validate QR code and register device"""
    db = dependencies.get_db()
    
    # Find pending link
    pending = await db.pending_device_links.find_one({
        "token": token,
        "status": "pending"
    })
    
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid or expired link token")
    
    # Check expiry
    expires_at = datetime.fromisoformat(pending["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="Link token has expired")
    
    # Register the device
    device_id = str(uuid4())
    device_record = {
        "id": device_id,
        "device_name": device_info.device_name,
        "device_type": device_info.device_type,
        "os_version": device_info.os_version,
        "manufacturer": device_info.manufacturer,
        "model": device_info.model,
        "phone_number": device_info.phone_number,
        "imei": device_info.imei,
        "owner_id": device_info.owner_id,
        "link_token": token,
        "status": "pending_verification",
        "protection_status": "inactive",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "features_enabled": {
            "sms_protection": False,
            "url_blocking": False,
            "app_monitoring": False,
            "network_analysis": False
        },
        "stats": {
            "urls_scanned": 0,
            "threats_blocked": 0,
            "sms_analyzed": 0,
            "apps_monitored": 0
        }
    }
    
    await db.protected_mobiles.insert_one(device_record)
    
    # Update pending link status
    await db.pending_device_links.update_one(
        {"token": token},
        {"$set": {"status": "validated", "device_id": device_id}}
    )
    
    return {
        "device_id": device_id,
        "status": "pending_verification",
        "next_step": "sms_verification",
        "message": "Device registered. Please complete SMS verification."
    }


# ==================== SMS VERIFICATION ====================

@router.post("/sms/send-otp")
async def send_sms_otp(request: SMSVerification):
    """Send SMS OTP for verification"""
    db = dependencies.get_db()
    
    # Verify device exists
    device = await db.protected_mobiles.find_one({"id": request.device_id})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Generate OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    
    # Store OTP
    await db.sms_otps.insert_one({
        "id": str(uuid4()),
        "device_id": request.device_id,
        "phone_number": request.phone_number,
        "otp_code": otp_code,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    })
    
    # Update device phone number
    await db.protected_mobiles.update_one(
        {"id": request.device_id},
        {"$set": {"phone_number": request.phone_number}}
    )
    
    # In production, would send actual SMS via Twilio/etc
    # For demo, we return success and log the OTP
    print(f"[DEMO] OTP for {request.phone_number}: {otp_code}")
    
    return {
        "status": "sent",
        "phone_number": request.phone_number[-4:].rjust(len(request.phone_number), '*'),
        "expires_in_minutes": 5,
        "message": "OTP sent successfully",
        # Demo only - remove in production
        "demo_otp": otp_code
    }


@router.post("/sms/verify-otp")
async def verify_sms_otp(request: OTPVerification):
    """Verify SMS OTP"""
    db = dependencies.get_db()
    
    # Find OTP record
    otp_record = await db.sms_otps.find_one({
        "device_id": request.device_id,
        "phone_number": request.phone_number,
        "otp_code": request.otp_code,
        "status": "pending"
    })
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Check expiry
    expires_at = datetime.fromisoformat(otp_record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired")
    
    # Mark OTP as used
    await db.sms_otps.update_one(
        {"id": otp_record["id"]},
        {"$set": {"status": "verified"}}
    )
    
    # Activate device protection
    await db.protected_mobiles.update_one(
        {"id": request.device_id},
        {
            "$set": {
                "status": "active",
                "protection_status": "active",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "features_enabled": {
                    "sms_protection": True,
                    "url_blocking": True,
                    "app_monitoring": True,
                    "network_analysis": True
                }
            }
        }
    )
    
    return {
        "status": "verified",
        "device_id": request.device_id,
        "protection_status": "active",
        "features_enabled": ["sms_protection", "url_blocking", "app_monitoring", "network_analysis"],
        "message": "Device verified and protection activated!"
    }


# ==================== REAL-TIME SMS LINK SCANNING ====================

@router.post("/scan/url")
async def scan_url(request: URLScanRequest):
    """Scan a URL for threats"""
    db = dependencies.get_db()
    
    url = request.url.lower()
    threats = []
    risk_score = 0
    
    # Check against known phishing domains
    for domain in KNOWN_PHISHING_DOMAINS:
        if domain in url:
            threats.append({
                "type": "phishing",
                "severity": "critical",
                "description": f"Known phishing domain detected: {domain}"
            })
            risk_score += 40
    
    # Check for suspicious patterns
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in url:
            threats.append({
                "type": "suspicious_pattern",
                "severity": "high",
                "description": f"Suspicious URL pattern: {pattern}"
            })
            risk_score += 15
    
    # Check for IP-based URLs (often malicious)
    import re
    ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    if re.search(ip_pattern, url):
        threats.append({
            "type": "ip_url",
            "severity": "medium",
            "description": "URL uses IP address instead of domain"
        })
        risk_score += 20
    
    # Check for URL shorteners (can hide malicious links)
    shorteners = ["bit.ly", "tinyurl", "t.co", "goo.gl", "ow.ly", "is.gd"]
    for shortener in shorteners:
        if shortener in url:
            threats.append({
                "type": "url_shortener",
                "severity": "low",
                "description": f"URL shortened with {shortener} - destination unknown"
            })
            risk_score += 10
    
    # Check for typosquatting
    typos = {
        "googel": "google", "gogle": "google", "amazom": "amazon",
        "facebok": "facebook", "instgram": "instagram", "whatsap": "whatsapp"
    }
    for typo, correct in typos.items():
        if typo in url:
            threats.append({
                "type": "typosquatting",
                "severity": "high",
                "description": f"Possible typosquatting: {typo} (should be {correct})"
            })
            risk_score += 25
    
    # Determine verdict
    risk_score = min(100, risk_score)
    if risk_score >= 70:
        verdict = "malicious"
        action = "blocked"
    elif risk_score >= 40:
        verdict = "suspicious"
        action = "warning"
    elif risk_score >= 20:
        verdict = "potentially_unsafe"
        action = "caution"
    else:
        verdict = "safe"
        action = "allowed"
    
    # Store scan result
    scan_record = {
        "id": str(uuid4()),
        "device_id": request.device_id,
        "url": request.url,
        "source": request.source,
        "verdict": verdict,
        "risk_score": risk_score,
        "threats": threats,
        "action": action,
        "scanned_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.url_scans.insert_one(scan_record)
    
    # Update device stats
    await db.protected_mobiles.update_one(
        {"id": request.device_id},
        {
            "$inc": {
                "stats.urls_scanned": 1,
                "stats.threats_blocked": 1 if action == "blocked" else 0
            }
        }
    )
    
    return {
        "url": request.url,
        "verdict": verdict,
        "risk_score": risk_score,
        "action": action,
        "threats": threats,
        "recommendation": "Do not click this link" if risk_score >= 40 else "Link appears safe"
    }


@router.post("/scan/sms")
async def scan_sms_content(device_id: str, sms_content: str, sender: str = "unknown"):
    """Scan SMS content for threats"""
    db = dependencies.get_db()
    
    threats = []
    risk_score = 0
    extracted_urls = []
    
    # Extract URLs from SMS
    import re
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, sms_content)
    
    # Scan each URL
    for url in urls:
        extracted_urls.append(url)
        # Quick check
        for domain in KNOWN_PHISHING_DOMAINS:
            if domain in url.lower():
                threats.append({
                    "type": "phishing_link",
                    "severity": "critical",
                    "url": url
                })
                risk_score += 50
    
    # Check for urgent language (social engineering)
    urgent_phrases = [
        "urgent", "immediately", "account suspended", "verify now",
        "act fast", "limited time", "your account", "click here",
        "congratulations", "you've won", "claim your prize"
    ]
    
    content_lower = sms_content.lower()
    for phrase in urgent_phrases:
        if phrase in content_lower:
            threats.append({
                "type": "social_engineering",
                "severity": "medium",
                "phrase": phrase
            })
            risk_score += 10
    
    # Check sender
    suspicious_senders = ["unknown", "+1", "+44", "+91"]
    for sus in suspicious_senders:
        if sender.startswith(sus) or sender == "unknown":
            risk_score += 5
    
    risk_score = min(100, risk_score)
    verdict = "malicious" if risk_score >= 60 else "suspicious" if risk_score >= 30 else "safe"
    
    # Store result
    await db.sms_scans.insert_one({
        "id": str(uuid4()),
        "device_id": device_id,
        "sender": sender,
        "content_hash": hashlib.sha256(sms_content.encode()).hexdigest(),
        "extracted_urls": extracted_urls,
        "verdict": verdict,
        "risk_score": risk_score,
        "threats": threats,
        "scanned_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update stats
    await db.protected_mobiles.update_one(
        {"id": device_id},
        {"$inc": {"stats.sms_analyzed": 1}}
    )
    
    return {
        "verdict": verdict,
        "risk_score": risk_score,
        "threats": threats,
        "extracted_urls": extracted_urls,
        "recommendation": "Delete this message" if risk_score >= 60 else "Be cautious" if risk_score >= 30 else "Message appears safe"
    }


# ==================== APP PERMISSION MONITORING ====================

@router.post("/apps/report-permissions")
async def report_app_permissions(report: AppPermissionReport):
    """Report app permissions for analysis"""
    db = dependencies.get_db()
    
    risk_assessment = {
        "app_package": report.app_package,
        "app_name": report.app_name,
        "total_permissions": len(report.permissions),
        "dangerous_permissions": [],
        "risk_score": 0,
        "risk_level": "low"
    }
    
    # Analyze permissions
    for perm in report.permissions:
        if perm in DANGEROUS_PERMISSIONS:
            perm_info = DANGEROUS_PERMISSIONS[perm]
            risk_assessment["dangerous_permissions"].append({
                "permission": perm,
                "risk": perm_info["risk"],
                "reason": perm_info["reason"]
            })
            
            # Add to risk score
            if perm_info["risk"] == "critical":
                risk_assessment["risk_score"] += 30
            elif perm_info["risk"] == "high":
                risk_assessment["risk_score"] += 20
            elif perm_info["risk"] == "medium":
                risk_assessment["risk_score"] += 10
            else:
                risk_assessment["risk_score"] += 5
    
    # Determine risk level
    score = min(100, risk_assessment["risk_score"])
    risk_assessment["risk_score"] = score
    
    if score >= 70:
        risk_assessment["risk_level"] = "critical"
        risk_assessment["recommendation"] = "Uninstall this app immediately"
    elif score >= 50:
        risk_assessment["risk_level"] = "high"
        risk_assessment["recommendation"] = "Review app necessity and permissions"
    elif score >= 30:
        risk_assessment["risk_level"] = "medium"
        risk_assessment["recommendation"] = "Monitor app behavior"
    else:
        risk_assessment["risk_level"] = "low"
        risk_assessment["recommendation"] = "App permissions are reasonable"
    
    # Store report
    await db.app_permissions.insert_one({
        "id": str(uuid4()),
        "device_id": report.device_id,
        **risk_assessment,
        "is_system_app": report.is_system_app,
        "reported_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update stats
    await db.protected_mobiles.update_one(
        {"id": report.device_id},
        {"$inc": {"stats.apps_monitored": 1}}
    )
    
    return risk_assessment


@router.get("/apps/risky/{device_id}")
async def get_risky_apps(device_id: str):
    """Get list of risky apps on device"""
    db = dependencies.get_db()
    
    risky_apps = await db.app_permissions.find(
        {"device_id": device_id, "risk_score": {"$gte": 30}},
        {"_id": 0}
    ).sort("risk_score", -1).to_list(50)
    
    return {
        "device_id": device_id,
        "risky_apps_count": len(risky_apps),
        "apps": risky_apps
    }


# ==================== NETWORK TRAFFIC ANALYSIS ====================

@router.post("/network/analyze")
async def analyze_network_traffic(report: NetworkTrafficReport):
    """Analyze network traffic from device"""
    db = dependencies.get_db()
    
    analysis = {
        "device_id": report.device_id,
        "total_connections": len(report.connections),
        "suspicious_connections": [],
        "blocked_connections": [],
        "data_summary": {
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "unique_destinations": set()
        },
        "risk_indicators": []
    }
    
    for conn in report.connections:
        dest_ip = conn.get("dest_ip", "")
        dest_port = conn.get("dest_port", 0)
        bytes_sent = conn.get("bytes_sent", 0)
        bytes_received = conn.get("bytes_received", 0)
        app = conn.get("app", "unknown")
        
        analysis["data_summary"]["total_bytes_sent"] += bytes_sent
        analysis["data_summary"]["total_bytes_received"] += bytes_received
        analysis["data_summary"]["unique_destinations"].add(dest_ip)
        
        # Check for malicious IPs
        for mal_ip in MALICIOUS_IPS:
            if dest_ip.startswith(mal_ip):
                analysis["suspicious_connections"].append({
                    "dest_ip": dest_ip,
                    "dest_port": dest_port,
                    "app": app,
                    "reason": "Known malicious IP range"
                })
                analysis["risk_indicators"].append({
                    "type": "malicious_ip",
                    "severity": "critical",
                    "details": f"Connection to known malicious IP: {dest_ip}"
                })
        
        # Check for suspicious ports
        suspicious_ports = [22, 23, 445, 3389, 4444, 5555, 6666, 31337]
        if dest_port in suspicious_ports:
            analysis["suspicious_connections"].append({
                "dest_ip": dest_ip,
                "dest_port": dest_port,
                "app": app,
                "reason": f"Suspicious port {dest_port}"
            })
        
        # Check for high data exfiltration
        if bytes_sent > 10000000:  # 10MB
            analysis["risk_indicators"].append({
                "type": "data_exfiltration",
                "severity": "high",
                "details": f"Large data upload ({bytes_sent/1000000:.2f}MB) to {dest_ip}"
            })
    
    analysis["data_summary"]["unique_destinations"] = len(analysis["data_summary"]["unique_destinations"])
    
    # Store analysis
    await db.network_analysis.insert_one({
        "id": str(uuid4()),
        "device_id": report.device_id,
        "analysis": analysis,
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return analysis


# ==================== DEVICE MANAGEMENT ====================

@router.get("/devices")
async def list_protected_devices(owner_id: Optional[str] = None, status: Optional[str] = None):
    """List all protected mobile devices"""
    db = dependencies.get_db()
    
    query = {}
    if owner_id:
        query["owner_id"] = owner_id
    if status:
        query["status"] = status
    
    devices = await db.protected_mobiles.find(query, {"_id": 0}).to_list(100)
    
    return {
        "total": len(devices),
        "devices": devices
    }


@router.get("/devices/{device_id}")
async def get_device_details(device_id: str):
    """Get detailed device information"""
    db = dependencies.get_db()
    
    device = await db.protected_mobiles.find_one({"id": device_id}, {"_id": 0})
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get recent activity
    recent_scans = await db.url_scans.find(
        {"device_id": device_id},
        {"_id": 0}
    ).sort("scanned_at", -1).limit(10).to_list(10)
    
    recent_sms = await db.sms_scans.find(
        {"device_id": device_id},
        {"_id": 0}
    ).sort("scanned_at", -1).limit(10).to_list(10)
    
    risky_apps = await db.app_permissions.find(
        {"device_id": device_id, "risk_score": {"$gte": 30}},
        {"_id": 0}
    ).sort("risk_score", -1).limit(5).to_list(5)
    
    return {
        **device,
        "recent_activity": {
            "url_scans": recent_scans,
            "sms_scans": recent_sms,
            "risky_apps": risky_apps
        }
    }


@router.get("/dashboard/overview")
async def get_mobile_protection_overview(owner_id: Optional[str] = None):
    """Get mobile protection dashboard overview"""
    db = dependencies.get_db()
    
    query = {}
    if owner_id:
        query["owner_id"] = owner_id
    
    # Device counts
    total_devices = await db.protected_mobiles.count_documents(query)
    active_devices = await db.protected_mobiles.count_documents({**query, "status": "active"})
    
    # Get aggregate stats
    devices = await db.protected_mobiles.find(query, {"stats": 1, "_id": 0}).to_list(1000)
    
    total_stats = {
        "urls_scanned": sum(d.get("stats", {}).get("urls_scanned", 0) for d in devices),
        "threats_blocked": sum(d.get("stats", {}).get("threats_blocked", 0) for d in devices),
        "sms_analyzed": sum(d.get("stats", {}).get("sms_analyzed", 0) for d in devices),
        "apps_monitored": sum(d.get("stats", {}).get("apps_monitored", 0) for d in devices)
    }
    
    # Recent threats
    recent_threats = await db.url_scans.find(
        {"verdict": {"$in": ["malicious", "suspicious"]}},
        {"_id": 0}
    ).sort("scanned_at", -1).limit(5).to_list(5)
    
    return {
        "summary": {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "pending_devices": total_devices - active_devices
        },
        "stats": total_stats,
        "recent_threats": recent_threats,
        "protection_rate": round((total_stats["threats_blocked"] / max(1, total_stats["urls_scanned"])) * 100, 1)
    }


# ==================== SDK DOWNLOAD ====================

@router.get("/sdk/info")
async def get_sdk_info():
    """Get SDK download information"""
    return {
        "android": {
            "version": "2.5.1",
            "min_sdk": 21,
            "target_sdk": 34,
            "size_mb": 3.2,
            "download_url": "/api/securesphere/mobile-protection/sdk/download/android",
            "documentation": "/docs/android-sdk",
            "features": [
                "Real-time SMS protection",
                "URL scanning",
                "App permission monitoring",
                "Network traffic analysis",
                "Push notifications for threats"
            ]
        },
        "ios": {
            "version": "2.5.0",
            "min_ios": "13.0",
            "size_mb": 2.8,
            "download_url": "/api/securesphere/mobile-protection/sdk/download/ios",
            "documentation": "/docs/ios-sdk",
            "features": [
                "Safari content blocking",
                "URL scanning",
                "Network traffic analysis",
                "Push notifications for threats"
            ]
        },
        "web_sdk": {
            "version": "1.2.0",
            "description": "Browser-based protection without app installation",
            "setup_url": "/api/securesphere/mobile-protection/browser-protection/setup"
        }
    }


@router.get("/browser-protection/setup")
async def setup_browser_protection(device_id: Optional[str] = None):
    """Setup app-less browser protection"""
    return {
        "setup_steps": [
            {
                "step": 1,
                "title": "Install Browser Extension",
                "description": "Add SecureSphere extension to your mobile browser",
                "platforms": ["Chrome", "Firefox", "Safari"]
            },
            {
                "step": 2,
                "title": "Configure DNS Protection",
                "description": "Set your DNS to SecureSphere secure DNS",
                "dns_servers": {
                    "primary": "103.247.36.36",
                    "secondary": "103.247.37.37"
                }
            },
            {
                "step": 3,
                "title": "Enable Safe Browsing",
                "description": "Bookmark this page for quick URL checks",
                "quick_scan_url": "/securesphere/quick-scan"
            }
        ],
        "protection_level": "basic",
        "note": "For full protection, install the SecureSphere mobile app"
    }
