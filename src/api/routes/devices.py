"""
Device management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from src.database.connection import get_database
from src.models.device import Device
from src.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/devices", response_model=DeviceListResponse)
async def get_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    test_devices_only: bool = Query(False),
    db: Session = Depends(get_database)
):
    """Get list of devices with filtering options"""
    
    query = db.query(Device)
    
    # Apply filters
    if status:
        query = query.filter(Device.status == status)
    if device_type:
        query = query.filter(Device.device_type == device_type)
    if test_devices_only:
        query = query.filter(Device.is_test_device == True)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    devices = query.offset(skip).limit(limit).all()
    
    return DeviceListResponse(
        devices=[DeviceResponse.from_orm(device) for device in devices],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: Session = Depends(get_database)):
    """Get a specific device by device_id"""
    
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceResponse.from_orm(device)

@router.post("/devices", response_model=DeviceResponse)
async def create_device(device_data: DeviceCreate, db: Session = Depends(get_database)):
    """Create a new device"""
    
    # Check if device already exists
    existing_device = db.query(Device).filter(Device.device_id == device_data.device_id).first()
    if existing_device:
        raise HTTPException(status_code=400, detail="Device with this ID already exists")
    
    # Create new device
    device = Device(**device_data.dict())
    db.add(device)
    db.commit()
    db.refresh(device)
    
    logger.info("Device created", device_id=device.device_id, name=device.name)
    return DeviceResponse.from_orm(device)

@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str, 
    device_data: DeviceUpdate, 
    db: Session = Depends(get_database)
):
    """Update a device"""
    
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update device fields
    update_data = device_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)
    
    db.commit()
    db.refresh(device)
    
    logger.info("Device updated", device_id=device.device_id)
    return DeviceResponse.from_orm(device)

@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, db: Session = Depends(get_database)):
    """Delete a device"""
    
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db.delete(device)
    db.commit()
    
    logger.info("Device deleted", device_id=device_id)
    return {"message": "Device deleted successfully"}

@router.get("/devices/{device_id}/status")
async def get_device_status(device_id: str, db: Session = Depends(get_database)):
    """Get current device status and uptime information"""
    
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Calculate uptime based on last_seen
    now = datetime.utcnow()
    if device.last_seen:
        time_since_last_seen = now - device.last_seen
        is_online = time_since_last_seen.total_seconds() < 300  # 5 minutes threshold
    else:
        is_online = False
        time_since_last_seen = None
    
    return {
        "device_id": device.device_id,
        "status": device.status,
        "is_online": is_online,
        "last_seen": device.last_seen,
        "time_since_last_seen": time_since_last_seen.total_seconds() if time_since_last_seen else None
    }
