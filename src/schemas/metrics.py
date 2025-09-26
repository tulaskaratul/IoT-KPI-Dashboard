"""
Metrics Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

class MetricBase(BaseModel):
    """Base metric schema"""
    timestamp: datetime = Field(..., description="Metric timestamp")
    metric_type: str = Field(..., description="Type of metric")
    value: Optional[Decimal] = Field(None, description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    tags: Optional[Dict[str, Any]] = Field(None, description="Additional tags")

class MetricCreate(MetricBase):
    """Schema for creating a metric"""
    pass

class MetricResponse(MetricBase):
    """Schema for metric response"""
    id: UUID
    device_id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class MetricListResponse(BaseModel):
    """Schema for metric list response"""
    metrics: List[MetricResponse]
    total: int
