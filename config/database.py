from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    
db = Database()

async def get_database():
    return db.client[os.environ.get('DB_NAME', 'infuse_health')]

async def connect_to_mongo():
    """Connect to MongoDB and create indexes for optimal performance"""
    logger.info("Connecting to MongoDB...")
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    
    # MongoDB Atlas connection settings
    # Add connection options for production Atlas clusters
    connection_options = {
        'maxPoolSize': 50,
        'minPoolSize': 10,
        'serverSelectionTimeoutMS': 5000,
        'connectTimeoutMS': 10000,
        'socketTimeoutMS': 45000,
        'retryWrites': True,
        'w': 'majority'
    }
    
    # Check if using Atlas (contains mongodb+srv or mongodb.net)
    if 'mongodb+srv://' in mongo_url or 'mongodb.net' in mongo_url:
        logger.info("Detected MongoDB Atlas connection")
        db.client = AsyncIOMotorClient(mongo_url, **connection_options)
    else:
        logger.info("Using local MongoDB connection")
        db.client = AsyncIOMotorClient(mongo_url)
    
    # Test connection
    try:
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        logger.error(f"MongoDB URL format: {mongo_url.split('@')[0] if '@' in mongo_url else 'localhost'}")
        raise
    
    # Create indexes for performance (Enterprise-grade)
    database = await get_database()
    
    # Users collection indexes
    await database.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True, name="email_unique"),
        IndexModel([("phone", ASCENDING)], sparse=True, name="phone_idx"),
        IndexModel([("role", ASCENDING)], name="role_idx"),
        IndexModel([("created_at", DESCENDING)], name="created_at_idx"),
        IndexModel([("is_active", ASCENDING), ("role", ASCENDING)], name="active_role_idx")
    ])
    
    # Health records indexes
    await database.health_records.create_indexes([
        IndexModel([("user_id", ASCENDING), ("date", DESCENDING)], name="user_date_idx"),
        IndexModel([("record_type", ASCENDING)], name="record_type_idx"),
        IndexModel([("abdm_record_id", ASCENDING)], sparse=True, name="abdm_id_idx"),
        IndexModel([("created_at", DESCENDING)], name="created_at_idx")
    ])
    
    # Health risk predictions indexes
    await database.health_risk_predictions.create_indexes([
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created_idx"),
        IndexModel([("risk_level", ASCENDING), ("is_active", ASCENDING)], name="risk_active_idx"),
        IndexModel([("risk_category", ASCENDING)], name="category_idx")
    ])
    
    # Doctor profiles indexes
    await database.doctor_profiles.create_indexes([
        IndexModel([("user_id", ASCENDING)], unique=True, name="user_id_unique"),
        IndexModel([("country", ASCENDING), ("city", ASCENDING)], name="location_idx"),
        IndexModel([("specialization.primary", ASCENDING)], name="specialization_idx"),
        IndexModel([("rating", DESCENDING)], name="rating_idx"),
        IndexModel([("is_verified", ASCENDING), ("is_accepting_patients", ASCENDING)], name="verified_accepting_idx")
    ])
    
    # Consultations indexes
    await database.consultations.create_indexes([
        IndexModel([("patient_id", ASCENDING), ("appointment_date", DESCENDING)], name="patient_appt_idx"),
        IndexModel([("doctor_id", ASCENDING), ("appointment_date", DESCENDING)], name="doctor_appt_idx"),
        IndexModel([("status", ASCENDING), ("appointment_date", ASCENDING)], name="status_date_idx")
    ])
    
    # Billing records indexes
    await database.billing_records.create_indexes([
        IndexModel([("patient_id", ASCENDING), ("invoice_date", DESCENDING)], name="patient_invoice_idx"),
        IndexModel([("doctor_id", ASCENDING), ("invoice_date", DESCENDING)], name="doctor_invoice_idx"),
        IndexModel([("status", ASCENDING)], name="status_idx"),
        IndexModel([("invoice_number", ASCENDING)], unique=True, name="invoice_unique")
    ])
    
    # Medicine inventory indexes
    await database.medicine_inventory.create_indexes([
        IndexModel([("name", ASCENDING)], name="name_idx"),
        IndexModel([("category", ASCENDING), ("subcategory", ASCENDING)], name="category_idx"),
        IndexModel([("expiry_date", ASCENDING)], name="expiry_idx"),
        IndexModel([("stock_quantity", ASCENDING)], name="stock_idx"),
        IndexModel([("is_active", ASCENDING)], name="active_idx")
    ])
    
    logger.info("Database indexes created successfully")

async def close_mongo_connection():
    """Close MongoDB connection"""
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
    logger.info("MongoDB connection closed")
