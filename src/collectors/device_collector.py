"""
Device data collector for IoT KPI Dashboard
Collects data from external APIs and updates device metrics
"""

import asyncio
import aiohttp
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import time
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from src.database.connection import engine
from src.models.device import Device
from src.models.metrics import DeviceMetric, DeviceStatusHistory
from src.core.config import settings

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class DeviceCollector:
    """Collects device data from external APIs"""
    
    def __init__(self):
        self.session = None
        self.db_session = sessionmaker(bind=engine)()
        self.running = False
        
    async def start(self):
        """Start the data collector"""
        self.running = True
        logger.info("Starting device data collector")
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            await self._collect_loop()
    
    async def stop(self):
        """Stop the data collector"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Device data collector stopped")
    
    async def _collect_loop(self):
        """Main collection loop"""
        while self.running:
            try:
                await self._collect_device_data()
                await asyncio.sleep(settings.collection_interval)
            except Exception as e:
                logger.error("Error in collection loop", error=str(e))
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _collect_device_data(self):
        """Collect data for all devices"""
        try:
            # Get all test devices
            devices = self.db_session.query(Device).filter(Device.is_test_device == True).all()
            
            for device in devices:
                await self._collect_device_metrics(device)
                
        except Exception as e:
            logger.error("Error collecting device data", error=str(e))
    
    async def _collect_device_metrics(self, device: Device):
        """Collect metrics for a specific device"""
        try:
            # Simulate device data collection
            # In a real implementation, this would call the actual device API
            device_data = await self._simulate_device_data(device)
            
            if device_data:
                # Update device last_seen
                device.last_seen = datetime.utcnow()
                
                # Create metrics
                await self._create_device_metrics(device, device_data)
                
                # Update device status
                await self._update_device_status(device, device_data)
                
                self.db_session.commit()
                logger.info("Device metrics collected", device_id=device.device_id)
                
        except Exception as e:
            logger.error("Error collecting metrics for device", 
                        device_id=device.device_id, error=str(e))
            self.db_session.rollback()
    
    async def _simulate_device_data(self, device: Device) -> Optional[Dict]:
        """Simulate device data collection"""
        # This simulates calling an external API
        # In reality, you would call the actual Samasth API or device endpoints
        
        import random
        
        # Simulate different device behaviors
        if device.device_type == "sensor":
            return {
                "uptime": random.uniform(0.85, 1.0),
                "response_time": random.uniform(50, 200),
                "data_throughput": random.uniform(100, 1000),
                "error_count": random.randint(0, 5),
                "request_count": random.randint(10, 50),
                "status": "active" if random.random() > 0.1 else "inactive"
            }
        elif device.device_type == "camera":
            return {
                "uptime": random.uniform(0.7, 0.95),
                "response_time": random.uniform(100, 500),
                "data_throughput": random.uniform(1000, 5000),
                "error_count": random.randint(0, 10),
                "request_count": random.randint(5, 25),
                "status": "active" if random.random() > 0.15 else "inactive"
            }
        else:
            return {
                "uptime": random.uniform(0.8, 1.0),
                "response_time": random.uniform(75, 300),
                "data_throughput": random.uniform(200, 2000),
                "error_count": random.randint(0, 8),
                "request_count": random.randint(8, 40),
                "status": "active" if random.random() > 0.12 else "inactive"
            }
    
    async def _create_device_metrics(self, device: Device, data: Dict):
        """Create device metrics from collected data"""
        timestamp = datetime.utcnow()
        
        # Create various metrics (uptime is computed from status history, so we do NOT insert it)
        metrics_data = [
            {"metric_type": "response_time", "value": data.get("response_time", 0), "unit": "ms"},
            {"metric_type": "data_throughput", "value": data.get("data_throughput", 0), "unit": "bytes/s"},
            {"metric_type": "error_count", "value": data.get("error_count", 0), "unit": "count"},
            {"metric_type": "request_count", "value": data.get("request_count", 0), "unit": "count"},
        ]
        
        for metric_data in metrics_data:
            metric = DeviceMetric(
                device_id=device.id,
                timestamp=timestamp,
                **metric_data
            )
            self.db_session.add(metric)
    
    async def _update_device_status(self, device: Device, data: Dict):
        """Update device status and track status changes"""
        new_status = data.get("status", "unknown")
        
        if device.status != new_status:
            # End current status period
            current_status = self.db_session.query(DeviceStatusHistory).filter(
                DeviceStatusHistory.device_id == device.id,
                DeviceStatusHistory.ended_at.is_(None)
            ).first()
            
            if current_status:
                current_status.ended_at = datetime.utcnow()
                current_status.duration_seconds = int(
                    (current_status.ended_at - current_status.started_at).total_seconds()
                )
            
            # Start new status period
            new_status_history = DeviceStatusHistory(
                device_id=device.id,
                status=new_status,
                started_at=datetime.utcnow()
            )
            self.db_session.add(new_status_history)
            
            # Update device status
            device.status = new_status
            
            logger.info("Device status changed", 
                        device_id=device.device_id, 
                        old_status=device.status, 
                        new_status=new_status)

async def main():
    """Main entry point for the collector"""
    collector = DeviceCollector()
    
    try:
        await collector.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await collector.stop()

if __name__ == "__main__":
    asyncio.run(main())
