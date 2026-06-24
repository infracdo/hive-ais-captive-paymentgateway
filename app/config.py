"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Apollo Captive Payment Gateway"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    
    # Payment
    PAYMENT_URL: str = "https://www.coronatel.com/"
    
    # Apollo Device Provisioner API
    APOLLO_PROVISIONER_URL: str = "http://10.42.4.19:8000"
    APOLLO_PROVISIONER_API_PREFIX: str = "/api/v1"
    APOLLO_PROVISIONER_TIMEOUT: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
