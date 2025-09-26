"""
KPI calculation models
"""

from sqlalchemy import Column, String, DateTime, Numeric, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.connection import Base
import uuid

class KPICalculation(Base):
    """KPI calculations for devices"""
    
    __tablename__ = "kpi_calculations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    calculation_type = Column(String(100), nullable=False, index=True)  # uptime_percentage, availability, response_time_avg
    time_period = Column(String(50), nullable=False, index=True)  # hourly, daily, weekly, monthly
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    value = Column(Numeric(15, 6), nullable=False)
    kpi_metadata = Column(JSON)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    device = relationship("Device", back_populates="kpi_calculations")
    
    def __repr__(self):
        return f"<KPICalculation(device_id={self.device_id}, type={self.calculation_type}, value={self.value})>"
