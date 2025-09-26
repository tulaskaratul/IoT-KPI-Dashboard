#!/usr/bin/env python3
"""
Initialize the database with sample data
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import random

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.database.connection import init_database, engine
from src.models.device import Device
from src.models.metrics import DeviceMetric, DeviceStatusHistory
from sqlalchemy.orm import sessionmaker

def create_sample_data():
    """Create sample data for testing"""
    
    # Initialize database
    asyncio.run(init_database())
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create sample devices if they don't exist
        sample_devices = [
            {
                "device_id": "TEMP_001",
                "name": "Temperature Sensor 1",
                "device_type": "sensor",
                "location": "Building A - Floor 1",
                "status": "active",
                "is_test_device": True,
                "device_metadata": {"model": "TempSense Pro", "firmware": "1.2.3"}
            },
            {
                "device_id": "HUMID_001",
                "name": "Humidity Monitor 1",
                "device_type": "sensor",
                "location": "Building A - Floor 2",
                "status": "active",
                "is_test_device": True,
                "device_metadata": {"model": "HumidityMax", "firmware": "2.1.0"}
            },
            {
                "device_id": "MOTION_001",
                "name": "Motion Detector 1",
                "device_type": "sensor",
                "location": "Building B - Entrance",
                "status": "inactive",
                "is_test_device": True,
                "device_metadata": {"model": "MotionPro", "firmware": "1.5.2"}
            },
            {
                "device_id": "AIR_001",
                "name": "Air Quality Monitor",
                "device_type": "sensor",
                "location": "Building A - Lobby",
                "status": "active",
                "is_test_device": True,
                "device_metadata": {"model": "AirQuality Pro", "firmware": "3.0.1"}
            },
            {
                "device_id": "CAM_001",
                "name": "Smart Camera 1",
                "device_type": "camera",
                "location": "Building B - Parking",
                "status": "maintenance",
                "is_test_device": True,
                "device_metadata": {"model": "SmartCam 4K", "firmware": "4.2.1"}
            }
        ]
        
        for device_data in sample_devices:
            existing = session.query(Device).filter(Device.device_id == device_data["device_id"]).first()
            if not existing:
                device = Device(**device_data)
                session.add(device)
        
        session.commit()
        print("✅ Sample devices created")
        
        # Create sample metrics for the last 24 hours
        devices = session.query(Device).filter(Device.is_test_device == True).all()
        now = datetime.utcnow()
        
        for device in devices:
            # Generate metrics for the last 24 hours (every 5 minutes)
            for i in range(288):  # 24 hours * 12 (5-minute intervals)
                timestamp = now - timedelta(minutes=i*5)
                
                # Generate realistic metrics based on device type
                if device.device_type == "sensor":
                    uptime = random.uniform(0.85, 1.0)
                    response_time = random.uniform(50, 200)
                    data_throughput = random.uniform(100, 1000)
                elif device.device_type == "camera":
                    uptime = random.uniform(0.7, 0.95)
                    response_time = random.uniform(100, 500)
                    data_throughput = random.uniform(1000, 5000)
                else:
                    uptime = random.uniform(0.8, 1.0)
                    response_time = random.uniform(75, 300)
                    data_throughput = random.uniform(200, 2000)
                
                # Create metrics
                metrics = [
                    DeviceMetric(
                        device_id=device.id,
                        timestamp=timestamp,
                        metric_type="uptime",
                        value=uptime,
                        unit="percentage"
                    ),
                    DeviceMetric(
                        device_id=device.id,
                        timestamp=timestamp,
                        metric_type="response_time",
                        value=response_time,
                        unit="ms"
                    ),
                    DeviceMetric(
                        device_id=device.id,
                        timestamp=timestamp,
                        metric_type="data_throughput",
                        value=data_throughput,
                        unit="bytes/s"
                    ),
                    DeviceMetric(
                        device_id=device.id,
                        timestamp=timestamp,
                        metric_type="error_count",
                        value=random.randint(0, 5),
                        unit="count"
                    ),
                    DeviceMetric(
                        device_id=device.id,
                        timestamp=timestamp,
                        metric_type="request_count",
                        value=random.randint(10, 50),
                        unit="count"
                    )
                ]
                
                for metric in metrics:
                    session.add(metric)
        
        session.commit()
        print("✅ Sample metrics created")
        
        # Create sample status history
        for device in devices:
            # Create status history for the last 24 hours
            statuses = ["active", "inactive", "maintenance"]
            current_time = now - timedelta(hours=24)
            
            while current_time < now:
                status = random.choice(statuses)
                duration = random.randint(30, 180)  # 30 minutes to 3 hours
                end_time = current_time + timedelta(minutes=duration)
                
                if end_time > now:
                    end_time = now
                
                status_history = DeviceStatusHistory(
                    device_id=device.id,
                    status=status,
                    started_at=current_time,
                    ended_at=end_time,
                    duration_seconds=int((end_time - current_time).total_seconds())
                )
                session.add(status_history)
                
                current_time = end_time
        
        session.commit()
        print("✅ Sample status history created")
        
        print("\n🎉 Database initialization complete!")
        print("You can now start the services with: docker-compose up")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    create_sample_data()
