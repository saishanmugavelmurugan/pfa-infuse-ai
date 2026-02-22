"""Application settings and configuration management."""
import os
from typing import Optional
from functools import lru_cache

class Settings:
    """Application settings loaded from environment variables."""
    
    # App settings
    APP_NAME: str = "Infuse-AI Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # Database settings
    MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME: str = os.environ.get('DB_NAME', 'infuse_health')
    
    # JWT settings
    JWT_SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
    
    # External APIs
    OPENFDA_BASE_URL: str = 'https://api.fda.gov/drug'
    
    # ABDM settings
    ABDM_CLIENT_ID: Optional[str] = os.environ.get('ABDM_CLIENT_ID')
    ABDM_CLIENT_SECRET: Optional[str] = os.environ.get('ABDM_CLIENT_SECRET')
    ABDM_ENVIRONMENT: str = os.environ.get('ABDM_ENVIRONMENT', 'sandbox')
    
    # AI/LLM settings
    EMERGENT_LLM_KEY: Optional[str] = os.environ.get('EMERGENT_LLM_KEY')
    
    # CORS settings - Use environment variable for flexibility
    # Actual CORS is configured in server.py using os.environ.get('CORS_ORIGINS', '*')
    
    @classmethod
    def is_production(cls) -> bool:
        return not cls.DEBUG
    
    @classmethod
    def get_abdm_base_url(cls) -> str:
        if cls.ABDM_ENVIRONMENT == 'production':
            return 'https://healthidsbx.abdm.gov.in'
        return 'https://healthidsbx.abdm.gov.in'  # Sandbox

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Export settings instance
settings = get_settings()
