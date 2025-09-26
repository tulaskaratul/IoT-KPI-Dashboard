"""
Metrics models for time-series data
"""

from sqlalchemy import Column, String, DateTime, Numeric, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.connection import Base
import uuid

class DeviceMetric(Base):
    """Device metrics for time-series data"""
    
    __tablename__ = "device_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    metric_type = Column(String(100), nullable=False, index=True)  # uptime, response_time, data_throughput, error_count
    value = Column(Numeric(15, 6))
    unit = Column(String(50))
    tags = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    device = relationship("Device", back_populates="metrics")
    
    def __repr__(self):
        return f"<DeviceMetric(device_id={self.device_id}, type={self.metric_type}, value={self.value})>"

class DeviceStatusHistory(Base):
    """Device status history for tracking status changes"""
    
    __tablename__ = "device_status_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Numeric(10, 0))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    device = relationship("Device", back_populates="status_history")
    
    def __repr__(self):
        return f"<DeviceStatusHistory(device_id={self.device_id}, status={self.status}, duration={self.duration_seconds})>"
