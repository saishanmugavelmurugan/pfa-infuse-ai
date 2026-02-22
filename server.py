from fastapi import FastAPI, APIRouter, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone

# Import dependencies
import dependencies

# Import route modules
from routes import auth, health, marketing, security, ppt_generator, lab_reports
from routes import organization, subscription, billing, razorpay, dashboard
# HealthTrack Pro routes
from routes import patients, appointments, medical_records, prescriptions, drugs, lab_tests, consent
from routes import healthtrack_billing, telemedicine, notifications
# Vitals & AI Health Analysis
from routes import vitals, ai_health_analysis
# Video Consent
from routes import video_consent
# Developer Portal & Webhooks
from routes import developer_portal, webhooks

ROOT_DIR = Path(__file__).parent

# Load environment variables (only if .env exists, for local development)
env_file = ROOT_DIR / '.env'
if env_file.exists():
    load_dotenv(env_file, override=False)
    logging.info("Loaded environment from .env file")
else:
    logging.info("No .env file found, using system environment variables")

# MongoDB connection with proper error handling
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    raise ValueError("MONGO_URL environment variable is required")

db_name = os.environ.get('DB_NAME', 'infuse_ai_platform')

# MongoDB Atlas connection settings for production with DNS resilience
connection_options = {
    'serverSelectionTimeoutMS': 30000,  # Increased to 30s for DNS resolution
    'connectTimeoutMS': 30000,  # Increased to 30s
    'socketTimeoutMS': 60000,
    'retryWrites': True,
    'retryReads': True,
    'directConnection': False  # Use replica set connection
}

# Enhanced settings for Atlas
if 'mongodb+srv://' in mongo_url or 'mongodb.net' in mongo_url or 'atlas' in mongo_url.lower():
    logging.info("Configuring for MongoDB Atlas with enhanced DNS and connection settings")
    connection_options.update({
        'maxPoolSize': 50,
        'minPoolSize': 5,  # Reduced min pool to allow faster startup
        'w': 'majority',
        'maxIdleTimeMS': 45000,
        'maxConnecting': 10,  # Limit concurrent connection attempts
        'serverSelectionTimeoutMS': 30000,  # Extra time for DNS + server selection
        'waitQueueTimeoutMS': 30000
    })
else:
    logging.info("Configuring for local MongoDB")
    connection_options['maxPoolSize'] = 10

# Initialize MongoDB client (connection will be tested during startup event)
client = AsyncIOMotorClient(mongo_url, **connection_options)
db = client[db_name]
logging.info(f"MongoDB client initialized for database: {db_name}")

# Set database in dependencies module
dependencies.set_database(db)

# Create the main app without a prefix
app = FastAPI(
    title="Infuse-ai API",
    description="Enterprise SaaS & PaaS Solutions API",
    version="1.0.0",
    redirect_slashes=False  # Disable automatic redirect for trailing slashes
)

# Root-level health endpoint for Kubernetes probes (MUST be before api_router)
@app.get("/health")
async def root_health_check():
    """Root-level health check for Kubernetes liveness/readiness probes"""
    return {
        "status": "healthy",
        "app": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {
        "message": "Infuse-ai API",
        "version": "1.0.0",
        "status": "running",
        "products": ["HealthTrack Pro", "MarketLake AI", "SecureSphere"]
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint - always returns 200 immediately for K8s readiness"""
    # Return immediately without checking DB - let K8s keep container alive
    return {
        "status": "healthy",
        "app": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/health/detailed")
async def health_check_detailed():
    """Detailed health check with database status - for monitoring, not K8s probes"""
    try:
        # Test database connection with very short timeout
        await db.command("ping", maxTimeMS=1000)
        return {
            "status": "healthy",
            "app": "running",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        # Return 200 with degraded status - don't crash container
        logging.warning(f"Detailed health check: Database disconnected - {e}")
        return {
            "status": "degraded",
            "app": "running",
            "database": "disconnected",
            "message": "Application running but database unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include routers
api_router.include_router(auth.router)
api_router.include_router(organization.router)
api_router.include_router(subscription.router)
api_router.include_router(billing.router)
api_router.include_router(razorpay.router)
api_router.include_router(dashboard.router)
api_router.include_router(health.router)
api_router.include_router(marketing.router)
api_router.include_router(security.router)
api_router.include_router(ppt_generator.router)
api_router.include_router(lab_reports.router, prefix="/lab-reports", tags=["Lab Reports"])
# HealthTrack Pro routers
api_router.include_router(patients.router)
api_router.include_router(appointments.router)
api_router.include_router(medical_records.router)
api_router.include_router(prescriptions.router)
api_router.include_router(drugs.router)
api_router.include_router(lab_tests.router)
api_router.include_router(consent.router)
api_router.include_router(healthtrack_billing.router)
api_router.include_router(telemedicine.router)
api_router.include_router(notifications.router)

# AI Analytics and Wearables
from routes import ai_analytics, wearable_devices
api_router.include_router(ai_analytics.router)
api_router.include_router(wearable_devices.router)

# AI Agents and Drug Database
from routes import ai_agents, drug_database
api_router.include_router(ai_agents.router)
api_router.include_router(drug_database.router)

# Vitals & AI Health Analysis
api_router.include_router(vitals.router)
api_router.include_router(ai_health_analysis.router)

# Video Consent
api_router.include_router(video_consent.router)

# Doctor Directory
from routes import doctors
api_router.include_router(doctors.router)

# Language and Localization
from routes import language
api_router.include_router(language.router)

# ABDM Integration (Ayushman Bharat Digital Mission)
from routes import abdm
api_router.include_router(abdm.router, prefix="/healthtrack")

# Global Health Schemes and AI Comparator
from routes import health_schemes, ai_comparator, super_admin
api_router.include_router(health_schemes.router)
api_router.include_router(ai_comparator.router)
api_router.include_router(super_admin.router)

# AI Lifestyle Correction Plan
from routes import ai_lifestyle
api_router.include_router(ai_lifestyle.router)

# Video Consulting & HMS Integration
from routes import video_consulting
api_router.include_router(video_consulting.router)

# Health Data Sync (Apple Health, Google Fit, Fitbit, Samsung Health, Garmin)
from routes import health_sync
api_router.include_router(health_sync.router)

# Appointment Reminders
from routes import reminders
api_router.include_router(reminders.router)

# Twilio Video Integration
from routes import twilio_video
api_router.include_router(twilio_video.router)

# Wearable Device Integrations (Fitbit, Google Fit, Apple Health)
from routes import wearable_integrations
api_router.include_router(wearable_integrations.router)

# SecureSphere - Cybersecurity Platform
from routes.securesphere import (
    url_scanner_router, sms_analyzer_router, threat_scoring_router,
    device_registry_router, dashboard_router, telecom_adapter_router,
    automotive_security_router, ai_agents_router, iot_security_router,
    gsm_fraud_router, automotive_advanced_router, analytics_router, reports_router
)
from routes.securesphere import surveillance_iot
from routes.securesphere import mobile_protection
api_router.include_router(url_scanner_router)
api_router.include_router(sms_analyzer_router)
api_router.include_router(threat_scoring_router)
api_router.include_router(device_registry_router)
api_router.include_router(dashboard_router)
api_router.include_router(telecom_adapter_router)
api_router.include_router(automotive_security_router)
api_router.include_router(ai_agents_router)
api_router.include_router(iot_security_router)
api_router.include_router(gsm_fraud_router)
api_router.include_router(automotive_advanced_router)
api_router.include_router(analytics_router)
api_router.include_router(reports_router)
api_router.include_router(surveillance_iot.router)
api_router.include_router(mobile_protection.router)
# CSP Operations - White-label and Multi-tenant Management for Telecom Operators
from routes.securesphere import csp_operations
api_router.include_router(csp_operations.router)

# Developer Portal
api_router.include_router(developer_portal.router)

# Webhooks
api_router.include_router(webhooks.router)

# Doctor OTP Access for Health Records
from routes import doctor_access
api_router.include_router(doctor_access.router)

# Enterprise Features (Phase 4D)
from routes.enterprise import sso, bulk_export, ip_whitelist, audit_logs
app.include_router(sso.router)
app.include_router(bulk_export.router)
app.include_router(ip_whitelist.router)
app.include_router(audit_logs.router)

# Admin Console (Phase 4E)
from routes.admin import api_keys, usage_analytics, license_management
app.include_router(api_keys.router)
app.include_router(usage_analytics.router)
app.include_router(license_management.router)

# vRAN Integration & Threat Detection System
from routes import vran_api
app.include_router(vran_api.router)

# Unified vRAN Service (Integrated Telco-Grade)
from routes import unified_vran_api
app.include_router(unified_vran_api.router)

# Internal Admin Console (Infuse Team Only)
from routes import internal_admin
app.include_router(internal_admin.router)

# Enterprise Admin (Customer Portal)
from routes import enterprise_admin
app.include_router(enterprise_admin.router)

# AI Agents Admin (Infuse Super Admin Only)
from routes import ai_agents_admin
app.include_router(ai_agents_admin.router)

# Unified Admin Dashboard (Internal Team - Single Login for Both Platforms)
from routes import unified_admin
app.include_router(unified_admin.router)

# OEM SDK - Device Protection for Manufacturers
from routes import oem_sdk
app.include_router(oem_sdk.router)

# SSO Integration - Enterprise Single Sign-On
from routes import sso_integration
app.include_router(sso_integration.router)

# IP Whitelisting - Enterprise Security
from routes import ip_whitelist
app.include_router(ip_whitelist.router)

# Multi-Tenant Organizations - Unified Management
from routes import multi_tenant_api
app.include_router(multi_tenant_api.router)

# Feature Flags API - Modular Feature Management
from routes import feature_flags
app.include_router(feature_flags.router)

# SecureSphere 5G-IoT Regulatory Compliance Module
from routes.securesphere import iot_5g_compliance
app.include_router(iot_5g_compliance.router)

# Multi-Protocol Connectivity Platform
from routes import connectivity_platform
app.include_router(connectivity_platform.router)

# Alerts API - Email, SMS, WhatsApp notifications
from routes import alerts
app.include_router(alerts.router)

# Architecture Documentation - Word Download
from routes import architecture_doc
app.include_router(architecture_doc.router)

# Integration Architecture PPT - Block Diagrams
from routes import integration_architecture_ppt
app.include_router(integration_architecture_ppt.router)

# Team Management - Enterprise user invitation and management
from routes import team_management
app.include_router(team_management.router)

# Monitoring & Metrics - Performance monitoring, alerting, capacity planning
from routes import monitoring
api_router.include_router(monitoring.router)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# Background MongoDB connection retry task
async def retry_mongodb_connection():
    """Retry MongoDB connection in background until successful"""
    import asyncio
    retry_count = 0
    retry_delay = 5
    max_delay = 60
    
    logging.info("🔄 Starting background MongoDB connection retry task...")
    
    while True:
        try:
            retry_count += 1
            logging.info(f"🔄 Background retry #{retry_count}: Testing MongoDB connection...")
            await client.admin.command('ping', maxTimeMS=5000)
            logging.info(f"✅ Background retry successful! MongoDB connected after {retry_count} attempts.")
            return  # Success, exit retry loop
            
        except Exception as e:
            logging.warning(f"⚠️ Background retry #{retry_count} failed: {e}")
            # Exponential backoff with max limit
            retry_delay = min(retry_delay * 1.5, max_delay)
            logging.info(f"🔄 Next retry in {retry_delay:.0f} seconds...")
            await asyncio.sleep(retry_delay)


# Startup event - MUST complete quickly for Kubernetes health checks
@app.on_event("startup")
async def startup_db_client():
    """
    Non-blocking startup - immediately schedules MongoDB connection in background.
    This prevents Kubernetes health check timeout during deployment.
    """
    import asyncio
    
    # Immediately start background MongoDB connection task
    logging.info("Scheduling MongoDB connection test in background...")
    asyncio.create_task(test_mongodb_connection_background())
    
    # Return immediately - don't block Kubernetes health checks
    logging.info("✅ Application startup complete. MongoDB connection running in background.")


async def test_mongodb_connection_background():
    """Background task to test and retry MongoDB connection without blocking startup."""
    import asyncio
    max_retries = 10  # Increased retries for Atlas DNS resolution
    retry_delay = 3  # Start with 3 seconds for DNS resolution
    
    for attempt in range(max_retries):
        try:
            # Test MongoDB connection
            logging.info(f"Testing MongoDB connection (attempt {attempt + 1}/{max_retries})...")
            await client.admin.command('ping')
            logging.info(f"✅ Successfully connected to MongoDB database: {db_name}")
            
            # Test database accessibility
            collections = await db.list_collection_names()
            logging.info(f"Database accessible. Collections: {len(collections)}")
            return
            
        except Exception as e:
            logging.error(f"❌ Failed to connect to MongoDB (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Log connection details for debugging (sanitized)
            if '@' in mongo_url:
                parts = mongo_url.split('@')
                if len(parts) > 1:
                    sanitized_url = f"mongodb://***:***@{parts[1]}"
                else:
                    sanitized_url = "mongodb://***"
            else:
                sanitized_url = "mongodb://localhost:27017"
            
            logging.error(f"Connection format: {sanitized_url}")
            logging.error(f"Database name: {db_name}")
            
            if attempt < max_retries - 1:
                logging.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                # All attempts failed - log warning
                logging.warning("⚠️ All MongoDB connection attempts failed.")
                logging.warning("⚠️ Health check endpoint will report 'database: disconnected' until connection succeeds.")
                # Continue retrying indefinitely with longer delays
                asyncio.create_task(retry_mongodb_connection())

@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        logging.info("Closing MongoDB connection...")
        client.close()
        logging.info("✅ MongoDB connection closed successfully")
    except Exception as e:
        logging.error(f"Error closing MongoDB connection: {e}")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()