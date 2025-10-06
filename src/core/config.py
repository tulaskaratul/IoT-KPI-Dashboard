"""
Configuration settings for the IoT KPI Dashboard
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    db_host: str = "postgres"
    db_port: str = "5432"
    db_name: str = "iot_kpi_db"
    db_user: str = "iot_user"
    db_password: str = "iot_password"
    database_url: str = ""
    
    # Redis
    redis_host: str = "redis"
    redis_port: str = "6379"
    redis_url: str = ""
    
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
    cleanup_interval: str = "86400"
    
    # KPI Calculation
    kpi_calculation_interval: int = 300  # 5 minutes
    uptime_threshold: float = 0.95  # 95% uptime threshold
    
    # Airflow Settings
    airflow_uid: str = "50000"
    airflow_gid: str = "50000"
    
    # Logging
    log_level: str = "INFO"
    log_retention_days: str = "30"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Build database_url from components
        self.database_url = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        # Build redis_url from components
        self.redis_url = f"redis://{self.redis_host}:{self.redis_port}"

# Global settings instance
settings = Settings()
