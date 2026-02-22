from motor.motor_asyncio import AsyncIOMotorDatabase

# This will be set from server.py
_db: AsyncIOMotorDatabase = None

def set_database(database: AsyncIOMotorDatabase):
    global _db
    _db = database

def get_db() -> AsyncIOMotorDatabase:
    return _db

async def get_database() -> AsyncIOMotorDatabase:
    """Dependency for FastAPI routes to get database connection"""
    return _db
