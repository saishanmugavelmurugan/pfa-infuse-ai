"""
Developer Portal API
Provides API documentation, code examples, and interactive playground

Features:
- OpenAPI/Swagger documentation
- Code examples in Python, JavaScript, cURL
- Interactive API playground
- Developer resources
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, List, Dict
from datetime import datetime, timezone

router = APIRouter(prefix="/developer", tags=["Developer Portal"])


# API Categories for documentation
API_CATEGORIES = {
    "authentication": {
        "name": "Authentication",
        "description": "User authentication and authorization endpoints",
        "endpoints": [
            {"method": "POST", "path": "/api/auth/login", "description": "Login with email and password"},
            {"method": "POST", "path": "/api/auth/register", "description": "Register a new user"},
            {"method": "GET", "path": "/api/auth/me", "description": "Get current user profile"}
        ]
    },
    "securesphere_scanner": {
        "name": "SecureSphere - URL/SMS Scanner",
        "description": "Scan URLs and SMS for threats",
        "endpoints": [
            {"method": "POST", "path": "/api/securesphere/url-scanner/scan", "description": "Scan a URL for threats"},
            {"method": "GET", "path": "/api/securesphere/url-scanner/recent", "description": "Get recent URL scans"},
            {"method": "GET", "path": "/api/securesphere/url-scanner/stats", "description": "Get URL scanning statistics"},
            {"method": "POST", "path": "/api/securesphere/sms-analyzer/analyze", "description": "Analyze SMS for fraud"},
            {"method": "GET", "path": "/api/securesphere/sms-analyzer/recent", "description": "Get recent SMS analyses"}
        ]
    },
    "securesphere_analytics": {
        "name": "SecureSphere - Analytics & Reports",
        "description": "Threat analytics, compliance reports, and security insights",
        "endpoints": [
            {"method": "GET", "path": "/api/securesphere/analytics/threat-trends", "description": "Get threat trend analysis"},
            {"method": "GET", "path": "/api/securesphere/analytics/attack-vectors", "description": "Get attack vector breakdown"},
            {"method": "GET", "path": "/api/securesphere/analytics/geographic", "description": "Get geographic threat distribution"},
            {"method": "GET", "path": "/api/securesphere/analytics/industry/{industry}", "description": "Get industry-specific analytics"},
            {"method": "GET", "path": "/api/securesphere/reports/compliance/summary", "description": "Get compliance status summary"},
            {"method": "GET", "path": "/api/securesphere/reports/executive/summary", "description": "Get executive summary report"}
        ]
    },
    "securesphere_iot": {
        "name": "SecureSphere - IoT Security",
        "description": "IoT device management and security monitoring",
        "endpoints": [
            {"method": "GET", "path": "/api/securesphere/iot-security/endpoints", "description": "List all IoT endpoints"},
            {"method": "POST", "path": "/api/securesphere/iot-security/register", "description": "Register a new IoT device"},
            {"method": "POST", "path": "/api/securesphere/iot-security/firmware/scan", "description": "Scan device firmware"},
            {"method": "GET", "path": "/api/securesphere/iot-security/vulnerabilities", "description": "Get vulnerability reports"}
        ]
    },
    "securesphere_telecom": {
        "name": "SecureSphere - Telecom & GSM Fraud",
        "description": "Telecom fraud detection and GSM security",
        "endpoints": [
            {"method": "GET", "path": "/api/securesphere/gsm-fraud/dashboard", "description": "Get GSM fraud dashboard"},
            {"method": "GET", "path": "/api/securesphere/gsm-fraud/sim-swap/alerts", "description": "Get SIM swap alerts"},
            {"method": "GET", "path": "/api/securesphere/gsm-fraud/otp/events", "description": "Get OTP interception events"},
            {"method": "GET", "path": "/api/securesphere/telecom/stats", "description": "Get telecom statistics"}
        ]
    },
    "securesphere_automotive": {
        "name": "SecureSphere - Automotive Security",
        "description": "Connected vehicle security and fleet management",
        "endpoints": [
            {"method": "GET", "path": "/api/securesphere/automotive/vehicles", "description": "List protected vehicles"},
            {"method": "GET", "path": "/api/securesphere/automotive-advanced/ecu/vulnerabilities", "description": "Get ECU vulnerabilities"},
            {"method": "GET", "path": "/api/securesphere/automotive-advanced/gps/spoofing-alerts", "description": "Get GPS spoofing alerts"},
            {"method": "GET", "path": "/api/securesphere/automotive-advanced/fleet/vehicles", "description": "Get fleet vehicles"}
        ]
    },
    "healthtrack": {
        "name": "HealthTrack Pro",
        "description": "Healthcare management platform APIs",
        "endpoints": [
            {"method": "GET", "path": "/api/patients", "description": "List all patients"},
            {"method": "GET", "path": "/api/appointments", "description": "List appointments"},
            {"method": "GET", "path": "/api/prescriptions", "description": "List prescriptions"},
            {"method": "GET", "path": "/api/lab-tests", "description": "List lab tests"}
        ]
    }
}


# Code examples templates - Using $$ as placeholder to avoid format() issues
CODE_EXAMPLES = {
    "python": '''import requests

API_BASE = "https://your-api-url.com/api"
API_KEY = "your-api-key"

headers = {{
    "Authorization": f"Bearer {{API_KEY}}",
    "Content-Type": "application/json"
}}

# {description}
response = requests.{method}(
    f"{{API_BASE}}{path}",
    headers=headers{body_param}
)
print(response.json())
''',
    "javascript": '''const API_BASE = "https://your-api-url.com/api";
const API_KEY = "your-api-key";

// {description}
const response = await fetch(`${{API_BASE}}{path}`, {{
    method: "{METHOD}",
    headers: {{
        "Authorization": `Bearer ${{API_KEY}}`,
        "Content-Type": "application/json"
    }}{body_param}
}});
const data = await response.json();
console.log(data);
''',
    "curl": '''curl -X {METHOD} "https://your-api-url.com{path}" \\
    -H "Authorization: Bearer YOUR_API_KEY" \\
    -H "Content-Type: application/json"{body_param}
'''
}


@router.get("/")
async def developer_portal_home():
    """
    Developer Portal Home - Overview of available APIs
    """
    return {
        "title": "Infuse.AI Developer Portal",
        "version": "1.0.0",
        "description": "Welcome to the Infuse.AI API Documentation. Access SecureSphere cybersecurity APIs and HealthTrack Pro healthcare APIs.",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "api_categories": list(API_CATEGORIES.keys()),
        "quick_start": {
            "step_1": "Register at /api/auth/register to get an API key",
            "step_2": "Use the API key in Authorization header",
            "step_3": "Explore endpoints in each category",
            "step_4": "Test using the interactive playground"
        },
        "rate_limits": {
            "free_tier": "100 requests/minute",
            "pro_tier": "1000 requests/minute",
            "enterprise": "Unlimited"
        }
    }


@router.get("/categories")
async def list_api_categories():
    """
    List all API categories with descriptions
    """
    categories = []
    for key, value in API_CATEGORIES.items():
        categories.append({
            "id": key,
            "name": value["name"],
            "description": value["description"],
            "endpoint_count": len(value["endpoints"])
        })
    return {
        "total_categories": len(categories),
        "categories": categories
    }


@router.get("/categories/{category_id}")
async def get_category_endpoints(category_id: str):
    """
    Get all endpoints for a specific API category
    """
    if category_id not in API_CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Category '{category_id}' not found")
    
    category = API_CATEGORIES[category_id]
    return {
        "category_id": category_id,
        "name": category["name"],
        "description": category["description"],
        "endpoints": category["endpoints"]
    }


@router.get("/code-example")
async def get_code_example(
    endpoint: str = Query(..., description="API endpoint path"),
    method: str = Query(default="GET", description="HTTP method"),
    language: str = Query(default="python", regex="^(python|javascript|curl)$"),
    description: str = Query(default="API call", description="Description of the call")
):
    """
    Generate code example for a specific endpoint
    """
    template = CODE_EXAMPLES.get(language, CODE_EXAMPLES["python"])
    
    # Determine if body is needed
    body_param = ""
    if method.upper() in ["POST", "PUT", "PATCH"]:
        if language == "python":
            body_param = ',\n    json={"key": "value"}'
        elif language == "javascript":
            body_param = ',\n    body: JSON.stringify({"key": "value"})'
        elif language == "curl":
            body_param = ' \\\n    -d \'{"key": "value"}\''
    
    code = template.format(
        path=endpoint,
        method=method.lower(),
        METHOD=method.upper(),
        description=description,
        body_param=body_param
    )
    
    return {
        "endpoint": endpoint,
        "method": method.upper(),
        "language": language,
        "code": code
    }


@router.get("/playground/test")
async def playground_test_endpoint(
    endpoint: str = Query(..., description="API endpoint to test"),
    method: str = Query(default="GET", description="HTTP method")
):
    """
    Test an API endpoint from the playground
    Returns sample response structure
    """
    # This would normally proxy the request, but we'll return mock data
    return {
        "status": "success",
        "endpoint_tested": endpoint,
        "method": method,
        "response_time_ms": 45,
        "sample_response": {
            "data": "Sample response data",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "note": "This is a sample response. Use the actual endpoint for real data."
    }


@router.get("/sdks")
async def list_available_sdks():
    """
    List available SDKs and client libraries
    """
    return {
        "sdks": [
            {
                "language": "Python",
                "package": "infuse-ai-sdk",
                "install": "pip install infuse-ai-sdk",
                "docs": "/developer/sdk/python",
                "status": "available"
            },
            {
                "language": "JavaScript/Node.js",
                "package": "@infuse-ai/sdk",
                "install": "npm install @infuse-ai/sdk",
                "docs": "/developer/sdk/javascript",
                "status": "available"
            },
            {
                "language": "Go",
                "package": "github.com/infuse-ai/go-sdk",
                "install": "go get github.com/infuse-ai/go-sdk",
                "docs": "/developer/sdk/go",
                "status": "coming_soon"
            },
            {
                "language": "Java",
                "package": "com.infuse-ai:sdk",
                "install": "Maven/Gradle",
                "docs": "/developer/sdk/java",
                "status": "coming_soon"
            }
        ],
        "api_clients": [
            {
                "name": "Postman Collection",
                "download": "/developer/postman-collection",
                "description": "Import directly into Postman"
            },
            {
                "name": "OpenAPI Spec",
                "download": "/openapi.json",
                "description": "OpenAPI 3.0 specification"
            }
        ]
    }


@router.get("/webhooks")
async def webhook_documentation():
    """
    Webhook integration documentation
    """
    return {
        "title": "Webhook Integration",
        "description": "Receive real-time notifications for security events",
        "supported_events": [
            {
                "event": "threat.detected",
                "description": "New threat detected (URL, SMS, IoT)",
                "payload_example": {
                    "event": "threat.detected",
                    "timestamp": "2025-12-14T12:00:00Z",
                    "severity": "high",
                    "threat_type": "phishing",
                    "details": {}
                }
            },
            {
                "event": "compliance.alert",
                "description": "Compliance status change",
                "payload_example": {
                    "event": "compliance.alert",
                    "timestamp": "2025-12-14T12:00:00Z",
                    "framework": "soc2",
                    "status": "attention_needed",
                    "details": {}
                }
            },
            {
                "event": "device.registered",
                "description": "New device registered",
                "payload_example": {
                    "event": "device.registered",
                    "timestamp": "2025-12-14T12:00:00Z",
                    "device_id": "device-123",
                    "device_type": "mobile",
                    "details": {}
                }
            }
        ],
        "setup_endpoint": "POST /api/webhooks/register",
        "headers_sent": {
            "X-Infuse-Signature": "HMAC-SHA256 signature",
            "X-Infuse-Timestamp": "Unix timestamp",
            "Content-Type": "application/json"
        }
    }


@router.get("/rate-limits")
async def rate_limit_documentation():
    """
    Rate limiting documentation
    """
    return {
        "title": "Rate Limiting",
        "description": "API rate limits by subscription tier",
        "tiers": {
            "free": {
                "requests_per_minute": 100,
                "requests_per_day": 10000,
                "concurrent_connections": 5
            },
            "pro": {
                "requests_per_minute": 1000,
                "requests_per_day": 100000,
                "concurrent_connections": 20
            },
            "enterprise": {
                "requests_per_minute": "unlimited",
                "requests_per_day": "unlimited",
                "concurrent_connections": "unlimited"
            }
        },
        "headers_returned": {
            "X-RateLimit-Limit": "Maximum requests allowed",
            "X-RateLimit-Remaining": "Requests remaining",
            "X-RateLimit-Reset": "Time when limit resets (Unix timestamp)"
        },
        "exceeded_response": {
            "status_code": 429,
            "body": {"error": "rate_limit_exceeded", "retry_after": 60}
        }
    }


@router.get("/changelog")
async def api_changelog():
    """
    API changelog and version history
    """
    return {
        "current_version": "1.0.0",
        "changelog": [
            {
                "version": "1.0.0",
                "date": "2025-12-14",
                "changes": [
                    "Initial release of SecureSphere APIs",
                    "Added Analytics & Reports module",
                    "Added Geographic Threat Map",
                    "Added Compliance Reporting (SOC 2, ISO 27001, GDPR, HIPAA, PCI DSS)",
                    "Added Developer Portal with code examples",
                    "Released SDKs for Python, JavaScript, Java, PHP, Android, and iOS"
                ]
            },
            {
                "version": "0.9.0",
                "date": "2025-12-01",
                "changes": [
                    "Beta release",
                    "URL Scanner API",
                    "SMS Analyzer API",
                    "IoT Security endpoints",
                    "GSM Fraud Detection"
                ]
            }
        ],
        "deprecation_policy": "APIs are supported for 12 months after deprecation notice",
        "migration_guides": "/developer/migrations"
    }


# SDK Information
SDK_INFO = {
    "python": {
        "name": "Python SDK",
        "version": "1.0.0",
        "package": "infuse-ai-sdk",
        "install": "pip install infuse-ai-sdk",
        "docs_url": "https://docs.infuse.ai/sdk/python",
        "github": "https://github.com/infuse-ai/python-sdk",
        "path": "/app/sdks/python",
        "description": "Official Python SDK for Infuse.AI SecureSphere and HealthTrack Pro APIs"
    },
    "javascript": {
        "name": "JavaScript/Node.js SDK",
        "version": "1.0.0",
        "package": "@infuse-ai/sdk",
        "install": "npm install @infuse-ai/sdk",
        "docs_url": "https://docs.infuse.ai/sdk/javascript",
        "github": "https://github.com/infuse-ai/javascript-sdk",
        "path": "/app/sdks/javascript",
        "description": "Official JavaScript/Node.js SDK for Infuse.AI SecureSphere and HealthTrack Pro APIs"
    },
    "java": {
        "name": "Java SDK",
        "version": "1.0.0",
        "package": "ai.infuse:infuse-sdk",
        "install": "Maven: ai.infuse:infuse-sdk:1.0.0",
        "docs_url": "https://docs.infuse.ai/sdk/java",
        "github": "https://github.com/infuse-ai/java-sdk",
        "path": "/app/sdks/java",
        "description": "Official Java SDK for Infuse.AI SecureSphere and HealthTrack Pro APIs"
    },
    "php": {
        "name": "PHP SDK",
        "version": "1.0.0",
        "package": "infuse-ai/sdk",
        "install": "composer require infuse-ai/sdk",
        "docs_url": "https://docs.infuse.ai/sdk/php",
        "github": "https://github.com/infuse-ai/php-sdk",
        "path": "/app/sdks/php",
        "description": "Official PHP SDK for Infuse.AI SecureSphere and HealthTrack Pro APIs"
    },
    "android": {
        "name": "Android SDK (Kotlin)",
        "version": "1.0.0",
        "package": "ai.infuse:android-sdk",
        "install": "implementation 'ai.infuse:android-sdk:1.0.0'",
        "docs_url": "https://docs.infuse.ai/sdk/android",
        "github": "https://github.com/infuse-ai/android-sdk",
        "path": "/app/sdks/android",
        "description": "Official Android SDK for Infuse.AI SecureSphere and HealthTrack Pro APIs"
    },
    "ios": {
        "name": "iOS SDK (Swift)",
        "version": "1.0.0",
        "package": "InfuseAI",
        "install": ".package(url: \"https://github.com/infuse-ai/ios-sdk.git\", from: \"1.0.0\")",
        "docs_url": "https://docs.infuse.ai/sdk/ios",
        "github": "https://github.com/infuse-ai/ios-sdk",
        "path": "/app/sdks/ios",
        "description": "Official iOS SDK for Infuse.AI SecureSphere and HealthTrack Pro APIs"
    }
}


@router.get("/sdk/{sdk_id}")
async def get_sdk_info(sdk_id: str):
    """
    Get information about a specific SDK
    """
    if sdk_id not in SDK_INFO:
        raise HTTPException(status_code=404, detail=f"SDK '{sdk_id}' not found")
    
    return SDK_INFO[sdk_id]


@router.get("/sdk/{sdk_id}/download")
async def download_sdk(sdk_id: str):
    """
    Download SDK source files as a zip archive
    """
    import os
    import zipfile
    import io
    from fastapi.responses import StreamingResponse
    
    if sdk_id not in SDK_INFO:
        raise HTTPException(status_code=404, detail=f"SDK '{sdk_id}' not found")
    
    sdk = SDK_INFO[sdk_id]
    sdk_path = sdk["path"]
    
    if not os.path.exists(sdk_path):
        raise HTTPException(status_code=404, detail="SDK files not found")
    
    # Create zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(sdk_path):
            # Skip node_modules, __pycache__, .git, etc.
            dirs[:] = [d for d in dirs if d not in ['node_modules', '__pycache__', '.git', 'dist', 'build', 'target']]
            for file in files:
                if file.endswith(('.pyc', '.pyo', '.class')):
                    continue
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, os.path.dirname(sdk_path))
                zip_file.write(file_path, arc_name)
    
    zip_buffer.seek(0)
    
    filename = f"infuse-ai-sdk-{sdk_id}-{sdk['version']}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/sdk/{sdk_id}/docs")
async def get_sdk_docs(sdk_id: str):
    """
    Get SDK documentation/README
    """
    import os
    from fastapi.responses import PlainTextResponse
    
    if sdk_id not in SDK_INFO:
        raise HTTPException(status_code=404, detail=f"SDK '{sdk_id}' not found")
    
    sdk = SDK_INFO[sdk_id]
    readme_path = os.path.join(sdk["path"], "README.md")
    
    if not os.path.exists(readme_path):
        return {"docs_url": sdk["docs_url"], "message": "See online documentation"}
    
    with open(readme_path, 'r') as f:
        content = f.read()
    
    return PlainTextResponse(content, media_type="text/markdown")


@router.get("/sdks/all")
async def list_all_sdks():
    """
    List all available SDKs
    """
    return {
        "total": len(SDK_INFO),
        "sdks": [
            {
                "id": sdk_id,
                **info
            }
            for sdk_id, info in SDK_INFO.items()
        ]
    }


@router.get("/postman-collection")
async def get_postman_collection():
    """
    Get Postman collection for API testing
    """
    return {
        "info": {
            "name": "Infuse.AI API Collection",
            "description": "Complete API collection for SecureSphere and HealthTrack Pro",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [
            {
                "name": "Authentication",
                "item": [
                    {
                        "name": "Login",
                        "request": {
                            "method": "POST",
                            "url": "{{base_url}}/api/auth/login",
                            "body": {
                                "mode": "raw",
                                "raw": '{"email": "user@example.com", "password": "password"}'
                            }
                        }
                    },
                    {
                        "name": "Register",
                        "request": {
                            "method": "POST",
                            "url": "{{base_url}}/api/auth/register"
                        }
                    }
                ]
            },
            {
                "name": "SecureSphere",
                "item": [
                    {
                        "name": "Scan URL",
                        "request": {
                            "method": "POST",
                            "url": "{{base_url}}/api/securesphere/url-scanner/scan",
                            "body": {
                                "mode": "raw",
                                "raw": '{"url": "https://example.com"}'
                            }
                        }
                    },
                    {
                        "name": "Analyze SMS",
                        "request": {
                            "method": "POST",
                            "url": "{{base_url}}/api/securesphere/sms-analyzer/analyze"
                        }
                    },
                    {
                        "name": "Get Threat Trends",
                        "request": {
                            "method": "GET",
                            "url": "{{base_url}}/api/securesphere/analytics/threat-trends"
                        }
                    }
                ]
            },
            {
                "name": "HealthTrack Pro",
                "item": [
                    {
                        "name": "List Patients",
                        "request": {
                            "method": "GET",
                            "url": "{{base_url}}/api/patients"
                        }
                    },
                    {
                        "name": "List Appointments",
                        "request": {
                            "method": "GET",
                            "url": "{{base_url}}/api/appointments"
                        }
                    }
                ]
            },
            {
                "name": "Webhooks",
                "item": [
                    {
                        "name": "List Webhooks",
                        "request": {
                            "method": "GET",
                            "url": "{{base_url}}/api/webhooks"
                        }
                    },
                    {
                        "name": "Create Webhook",
                        "request": {
                            "method": "POST",
                            "url": "{{base_url}}/api/webhooks"
                        }
                    }
                ]
            }
        ],
        "variable": [
            {
                "key": "base_url",
                "value": "https://api.infuse.ai"
            }
        ]
    }
