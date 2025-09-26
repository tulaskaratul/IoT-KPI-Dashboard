"""
Metrics endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from src.database.connection import get_database
from src.models.metrics import DeviceMetric
from src.schemas.metrics import MetricCreate, MetricResponse, MetricListResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/devices/{device_id}/metrics", response_model=MetricListResponse)
async def get_device_metrics(
    device_id: str,
    metric_type: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_database)
):
    """Get metrics for a specific device"""
    
    query = db.query(DeviceMetric).filter(DeviceMetric.device_id == device_id)
    
    # Apply filters
    if metric_type:
        query = query.filter(DeviceMetric.metric_type == metric_type)
    if start_time:
        query = query.filter(DeviceMetric.timestamp >= start_time)
    if end_time:
        query = query.filter(DeviceMetric.timestamp <= end_time)
    
    # Order by timestamp descending and limit
    metrics = query.order_by(desc(DeviceMetric.timestamp)).limit(limit).all()
    
    return MetricListResponse(
        metrics=[MetricResponse.from_orm(metric) for metric in metrics],
        total=len(metrics)
    )

@router.post("/devices/{device_id}/metrics", response_model=MetricResponse)
async def create_metric(
    device_id: str,
    metric_data: MetricCreate,
    db: Session = Depends(get_database)
):
    """Create a new metric for a device"""
    
    # Verify device exists
    from src.models.device import Device
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Create metric
    metric = DeviceMetric(
        device_id=device.id,
        **metric_data.dict()
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    
    logger.info("Metric created", device_id=device_id, metric_type=metric.metric_type)
    return MetricResponse.from_orm(metric)

@router.get("/metrics/summary")
async def get_metrics_summary(
    device_type: Optional[str] = Query(None),
    time_period: str = Query("24h", description="Time period: 1h, 24h, 7d, 30d"),
    db: Session = Depends(get_database)
):
    """Get metrics summary across all devices"""
    
    # Calculate time range
    now = datetime.utcnow()
    if time_period == "1h":
        start_time = now - timedelta(hours=1)
    elif time_period == "24h":
        start_time = now - timedelta(days=1)
    elif time_period == "7d":
        start_time = now - timedelta(days=7)
    elif time_period == "30d":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(days=1)
    
    # Build query
    query = db.query(DeviceMetric).filter(DeviceMetric.timestamp >= start_time)
    
    if device_type:
        from src.models.device import Device
        query = query.join(Device).filter(Device.device_type == device_type)
    
    metrics = query.all()
    
    # Calculate summary statistics
    metric_types = {}
    for metric in metrics:
        if metric.metric_type not in metric_types:
            metric_types[metric.metric_type] = []
        metric_types[metric.metric_type].append(float(metric.value))
    
    summary = {}
    for metric_type, values in metric_types.items():
        if values:
            summary[metric_type] = {
                "count": len(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
    
    return {
        "time_period": time_period,
        "start_time": start_time,
        "end_time": now,
        "summary": summary
    }
