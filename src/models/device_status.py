"""
Device status model for aggregated uptime data
"""

from sqlalchemy import Column, DateTime, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from src.database.connection import Base

class DeviceStatus(Base):
    """Aggregated device status for uptime KPIs"""

    __tablename__ = "device_status"

    device_id = Column(UUID(as_uuid=True), primary_key=True)
    window_start = Column(DateTime, primary_key=True)
    window_end = Column(DateTime, nullable=False)
    uptime_percentage = Column(Float)
    avg_rss = Column(Float)
    active_minutes = Column(Integer)
    inactive_minutes = Column(Integer)

    def __repr__(self):
        return f"<DeviceStatus(device_id={self.device_id}, window_start={self.window_start}, uptime={self.uptime_percentage})>"
