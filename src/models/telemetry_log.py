"""
Telemetry log model for raw IoT data
"""

from sqlalchemy import Column, BigInteger, DateTime, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.connection import Base
import uuid

class TelemetryLog(Base):
    """Telemetry log for raw device data"""

    __tablename__ = "telemetry_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    rss_value = Column(Float)
    raw_payload = Column(JSON)

    # Relationship (optional)
    # device = relationship("Device", back_populates="telemetry_logs")

    def __repr__(self):
        return f"<TelemetryLog(device_id={self.device_id}, timestamp={self.timestamp}, rss={self.rss_value})>"
