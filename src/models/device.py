"""
Device model for IoT devices
"""

from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.connection import Base
import uuid

class Device(Base):
    """Device model representing IoT devices"""
    
    __tablename__ = "devices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    device_type = Column(String(100))
    location = Column(String(255))
    status = Column(String(50), default="unknown")  # active, inactive, maintenance
    is_test_device = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_seen = Column(DateTime(timezone=True), index=True)
    device_metadata = Column(JSON)
    
    # Relationships
    metrics = relationship("DeviceMetric", back_populates="device", cascade="all, delete-orphan")
    status_history = relationship("DeviceStatusHistory", back_populates="device", cascade="all, delete-orphan")
    kpi_calculations = relationship("KPICalculation", back_populates="device", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Device(id={self.device_id}, name={self.name}, status={self.status})>"
