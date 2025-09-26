"""
Device Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class DeviceBase(BaseModel):
    """Base device schema"""
    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Device name")
    device_type: Optional[str] = Field(None, description="Type of device")
    location: Optional[str] = Field(None, description="Device location")
    status: str = Field("unknown", description="Device status")
    is_test_device: bool = Field(False, description="Whether this is a test device")
    device_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional device metadata")

class DeviceCreate(DeviceBase):
    """Schema for creating a device"""
    pass

class DeviceUpdate(BaseModel):
    """Schema for updating a device"""
    name: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    is_test_device: Optional[bool] = None
    device_metadata: Optional[Dict[str, Any]] = None

class DeviceResponse(DeviceBase):
    """Schema for device response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DeviceListResponse(BaseModel):
    """Schema for device list response"""
    devices: list[DeviceResponse]
    total: int
    skip: int
    limit: int
