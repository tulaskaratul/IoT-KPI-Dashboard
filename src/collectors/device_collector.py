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
from src.models.telemetry_log import TelemetryLog
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
            # Get all production devices (not test devices)
            devices = self.db_session.query(Device).filter(Device.is_test_device == False).all()

            for device in devices:
                await self._collect_device_metrics(device)

        except Exception as e:
            logger.error("Error collecting device data", error=str(e))
    
    async def _collect_device_metrics(self, device: Device):
        """Collect metrics for a specific device and insert into telemetry_logs"""
        try:
            # Simulate device data collection
            # In a real implementation, this would call the actual device API
            device_data = await self._simulate_device_data(device)

            timestamp = datetime.utcnow()

            # Get RSS from metadata
            rss = device.device_metadata.get("rss_value", -70) if device.device_metadata else -70

            # Insert raw telemetry log
            telemetry_log = TelemetryLog(
                device_id=device.id,
                timestamp=timestamp,
                rss_value=rss,
                raw_payload=device_data if device_data else {"status": "no_response"}
            )
            self.db_session.add(telemetry_log)

            if device_data:
                # Update device last_seen only if responding
                device.last_seen = timestamp

                # Update device status to active
                await self._update_device_status(device, True, timestamp)

                logger.info("Device telemetry collected - responding", device_id=device.device_id)
            else:
                # No response, check if status should change to inactive
                time_since_last_seen = (timestamp - device.last_seen).total_seconds() if device.last_seen else float('inf')
                should_be_inactive = time_since_last_seen > 300  # 5 minutes threshold
                if should_be_inactive:
                    await self._update_device_status(device, False, timestamp)

                logger.info("Device not responding", device_id=device.device_id, time_since_last_seen=time_since_last_seen)

            self.db_session.commit()

        except Exception as e:
            logger.error("Error collecting metrics for device",
                        device_id=device.device_id, error=str(e))
            self.db_session.rollback()
    
    async def _simulate_device_data(self, device: Device) -> Optional[Dict]:
        """Simulate device data collection based on RSS and telemetry"""
        # This simulates calling an external API
        # In reality, you would call the actual Samasth API or device endpoints
        
        import random
        
        # Get RSS from metadata
        rss = device.device_metadata.get("rss_value", -70) if device.device_metadata else -70
        
        # Probability of responding based on RSS (better signal = higher chance)
        respond_prob = 0.3 + (rss + 100) / 60  # -100 to 0 dBm -> 0.3 to 0.9 prob
        respond_prob = min(0.95, max(0.1, respond_prob))
        is_responding = random.random() < respond_prob
        
        if not is_responding:
            return None  # No data if not responding
        
        # Simulate metrics
        if device.device_type == "sensor":
            response_time = random.uniform(50, 200)
            data_throughput = random.uniform(100, 1000)
            error_count = random.randint(0, 5)
            request_count = random.randint(10, 50)
        elif device.device_type == "camera":
            response_time = random.uniform(100, 500)
            data_throughput = random.uniform(1000, 5000)
            error_count = random.randint(0, 10)
            request_count = random.randint(5, 25)
        else:
            response_time = random.uniform(75, 300)
            data_throughput = random.uniform(200, 2000)
            error_count = random.randint(0, 8)
            request_count = random.randint(8, 40)
        
        return {
            "response_time": response_time,
            "data_throughput": data_throughput,
            "error_count": error_count,
            "request_count": request_count,
            "is_responding": True,
            "rss_adjusted": rss > -70  # For logging
        }
    



    
    async def _update_device_status(self, device: Device, is_responding: bool, timestamp: datetime):
        """Update device status and track status changes"""
        new_status = "active" if is_responding else "inactive"

        if device.status != new_status:
            # End current status period
            current_status = self.db_session.query(DeviceStatusHistory).filter(
                DeviceStatusHistory.device_id == device.id,
                DeviceStatusHistory.ended_at.is_(None)
            ).first()

            if current_status:
                current_status.ended_at = timestamp
                current_status.duration_seconds = int(
                    (current_status.ended_at - current_status.started_at).total_seconds()
                )

            # Start new status period
            new_status_history = DeviceStatusHistory(
                device_id=device.id,
                status=new_status,
                started_at=timestamp
            )
            self.db_session.add(new_status_history)

            # Update device status
            device.status = new_status

            logger.info("Device status changed",
                        device_id=device.device_id,
                        old_status=device.status,
                        new_status=new_status,
                        is_responding=is_responding)

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
