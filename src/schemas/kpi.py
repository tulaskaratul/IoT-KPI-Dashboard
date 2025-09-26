"""
KPI Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

class KPIBase(BaseModel):
    """Base KPI schema"""
    calculation_type: str = Field(..., description="Type of KPI calculation")
    time_period: str = Field(..., description="Time period for calculation")
    period_start: datetime = Field(..., description="Start of calculation period")
    period_end: datetime = Field(..., description="End of calculation period")
    value: Decimal = Field(..., description="Calculated KPI value")
    kpi_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class KPIResponse(KPIBase):
    """Schema for KPI response"""
    id: UUID
    device_id: Optional[UUID]
    calculated_at: datetime
    
    class Config:
        from_attributes = True

class KPICalculationRequest(BaseModel):
    """Schema for KPI calculation request"""
    calculation_types: List[str] = Field(..., description="Types of KPIs to calculate")
    time_period: str = Field(..., description="Time period for calculation")
    period_start: datetime = Field(..., description="Start of calculation period")
    period_end: datetime = Field(..., description="End of calculation period")
    kpi_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
