"""
Configuration settings for the IoT KPI Dashboard
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql://iot_user:iot_password@localhost:5432/iot_kpi_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # External APIs
    samasth_api_url: str = "https://samasth.io/api"
    samasth_api_key: Optional[str] = None
    
    # Data Collection
    collection_interval: int = 60  # seconds
    metrics_retention_days: int = 90
    
    # KPI Calculation
    kpi_calculation_interval: int = 300  # 5 minutes
    uptime_threshold: float = 0.95  # 95% uptime threshold
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
