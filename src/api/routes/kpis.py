"""
KPI calculation and retrieval endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import structlog

from src.database.connection import get_database
from src.models.kpi import KPICalculation
from src.models.device import Device
from src.models.metrics import DeviceMetric
from src.schemas.kpi import KPIResponse, KPICalculationRequest

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/devices/{device_id}/kpis", response_model=List[KPIResponse])
async def get_device_kpis(
    device_id: str,
    calculation_type: Optional[str] = Query(None),
    time_period: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database)
):
    """Get KPIs for a specific device"""
    
    # Verify device exists
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    query = db.query(KPICalculation).filter(KPICalculation.device_id == device.id)
    
    # Apply filters
    if calculation_type:
        query = query.filter(KPICalculation.calculation_type == calculation_type)
    if time_period:
        query = query.filter(KPICalculation.time_period == time_period)
    
    # Order by calculated_at descending and limit
    kpis = query.order_by(desc(KPICalculation.calculated_at)).limit(limit).all()
    
    return [KPIResponse.from_orm(kpi) for kpi in kpis]

@router.post("/devices/{device_id}/kpis/calculate")
async def calculate_device_kpis(
    device_id: str,
    request: KPICalculationRequest,
    db: Session = Depends(get_database)
):
    """Calculate KPIs for a specific device"""
    
    # Verify device exists
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Calculate KPIs based on request
    results = []
    
    for calculation_type in request.calculation_types:
        kpi_value = await _calculate_kpi(
            db, device.id, calculation_type, 
            request.time_period, request.period_start, request.period_end
        )
        
        if kpi_value is not None:
            # Store KPI calculation
            kpi_calculation = KPICalculation(
                device_id=device.id,
                calculation_type=calculation_type,
                time_period=request.time_period,
                period_start=request.period_start,
                period_end=request.period_end,
                value=kpi_value,
                kpi_metadata=request.kpi_metadata
            )
            db.add(kpi_calculation)
            results.append({
                "calculation_type": calculation_type,
                "value": kpi_value,
                "time_period": request.time_period
            })
    
    db.commit()
    
    logger.info("KPIs calculated", device_id=device_id, count=len(results))
    return {"results": results}

@router.get("/kpis/summary")
async def get_kpis_summary(
    device_type: Optional[str] = Query(None),
    time_period: str = Query("daily"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_database)
):
    """Get KPI summary across all devices"""
    
    query = db.query(KPICalculation).filter(KPICalculation.time_period == time_period)
    
    if device_type:
        query = query.join(Device).filter(Device.device_type == device_type)
    
    kpis = query.order_by(desc(KPICalculation.calculated_at)).limit(limit).all()
    
    # Group by calculation type
    kpi_summary = {}
    for kpi in kpis:
        if kpi.calculation_type not in kpi_summary:
            kpi_summary[kpi.calculation_type] = []
        kpi_summary[kpi.calculation_type].append(float(kpi.value))
    
    # Calculate statistics
    summary = {}
    for calc_type, values in kpi_summary.items():
        if values:
            summary[calc_type] = {
                "count": len(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
    
    return {
        "time_period": time_period,
        "summary": summary,
        "total_kpis": len(kpis)
    }

async def _calculate_kpi(db: Session, device_id: UUID, calculation_type: str, 
                       time_period: str, period_start: datetime, period_end: datetime) -> Optional[float]:
    """Calculate a specific KPI for a device"""
    
    if calculation_type == "uptime_percentage":
        return await _calculate_uptime_percentage(db, device_id, period_start, period_end)
    elif calculation_type == "availability":
        return await _calculate_availability(db, device_id, period_start, period_end)
    elif calculation_type == "response_time_avg":
        return await _calculate_response_time_avg(db, device_id, period_start, period_end)
    elif calculation_type == "error_rate":
        return await _calculate_error_rate(db, device_id, period_start, period_end)
    else:
        logger.warning("Unknown calculation type", calculation_type=calculation_type)
        return None

async def _calculate_uptime_percentage(db: Session, device_id: UUID, 
                                     period_start: datetime, period_end: datetime) -> float:
    """Calculate uptime percentage for a device"""
    
    # Get device status history for the period
    from src.models.metrics import DeviceStatusHistory
    
    status_history = db.query(DeviceStatusHistory).filter(
        and_(
            DeviceStatusHistory.device_id == device_id,
            DeviceStatusHistory.started_at >= period_start,
            DeviceStatusHistory.started_at <= period_end
        )
    ).all()
    
    if not status_history:
        return 0.0
    
    total_uptime = 0
    total_time = (period_end - period_start).total_seconds()
    
    for status in status_history:
        if status.status == "active":
            if status.ended_at:
                duration = (status.ended_at - status.started_at).total_seconds()
            else:
                # Still active, calculate until period_end
                duration = (period_end - status.started_at).total_seconds()
            total_uptime += duration
    
    return (total_uptime / total_time) * 100 if total_time > 0 else 0.0

async def _calculate_availability(db: Session, device_id: UUID, 
                                period_start: datetime, period_end: datetime) -> float:
    """Calculate device availability from status history only.

    For now, treat availability as the percentage of time in 'active' status
    over the requested window (same as uptime_percentage).
    """
    from src.models.metrics import DeviceStatusHistory

    status_history = db.query(DeviceStatusHistory).filter(
        and_(
            DeviceStatusHistory.device_id == device_id,
            DeviceStatusHistory.started_at >= period_start,
            DeviceStatusHistory.started_at <= period_end
        )
    ).all()

    if not status_history:
        return 0.0

    total_active = 0
    total_time = (period_end - period_start).total_seconds()

    for status in status_history:
        if status.status == "active":
            if status.ended_at:
                duration = (status.ended_at - status.started_at).total_seconds()
            else:
                duration = (period_end - status.started_at).total_seconds()
            total_active += duration

    return (total_active / total_time) * 100 if total_time > 0 else 0.0

async def _calculate_response_time_avg(db: Session, device_id: UUID, 
                                     period_start: datetime, period_end: datetime) -> float:
    """Calculate average response time for a device"""
    
    metrics = db.query(DeviceMetric).filter(
        and_(
            DeviceMetric.device_id == device_id,
            DeviceMetric.timestamp >= period_start,
            DeviceMetric.timestamp <= period_end,
            DeviceMetric.metric_type == "response_time"
        )
    ).all()
    
    if not metrics:
        return 0.0
    
    response_times = [float(m.value) for m in metrics if m.value is not None]
    return sum(response_times) / len(response_times) if response_times else 0.0

async def _calculate_error_rate(db: Session, device_id: UUID, 
                              period_start: datetime, period_end: datetime) -> float:
    """Calculate error rate for a device"""
    
    # Get total requests and error count
    total_requests = db.query(func.count(DeviceMetric.id)).filter(
        and_(
            DeviceMetric.device_id == device_id,
            DeviceMetric.timestamp >= period_start,
            DeviceMetric.timestamp <= period_end,
            DeviceMetric.metric_type == "request_count"
        )
    ).scalar() or 0
    
    error_count = db.query(func.count(DeviceMetric.id)).filter(
        and_(
            DeviceMetric.device_id == device_id,
            DeviceMetric.timestamp >= period_start,
            DeviceMetric.timestamp <= period_end,
            DeviceMetric.metric_type == "error_count"
        )
    ).scalar() or 0
    
    return (error_count / total_requests * 100) if total_requests > 0 else 0.0
