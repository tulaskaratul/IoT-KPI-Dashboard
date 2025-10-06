#!/usr/bin/env python3
"""
Load production devices from CSV into the database
Replaces test devices with production data from prod_batch_uptime_results.csv
Calculates initial uptime based on last_telemetry_time and RSS value
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Add project root to path to import src
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

from src.database.connection import engine
from src.models.device import Device
from src.models.metrics import DeviceMetric
from src.models.kpi import KPICalculation
from src.core.config import settings  # Assuming settings has DB URL if needed

def calculate_uptime(last_telemetry_time: datetime, current_time: datetime, rss_value: float = None, threshold_hours: int = 24) -> float:
    """
    Calculate uptime percentage based on last telemetry time.
    If within threshold, 100%. Else, decreases linearly to 0%.
    RSS value can influence: if RSS < -80, reduce uptime by 20%.
    """
    age_hours = (current_time - last_telemetry_time).total_seconds() / 3600
    if age_hours < 0:  # Future timestamp, treat as recent
        age_hours = 0
    base_uptime = max(0, 100 * (1 - (age_hours / threshold_hours)))
    # Adjust for RSS (assuming RSS is dBm, better signal = higher uptime)
    # Example: RSS > -50: no penalty, RSS < -80: 20% penalty
    rss_penalty = 0
    if rss_value is not None:
        if rss_value < -80:
            rss_penalty = 20
        elif rss_value > -50:
            rss_penalty = -10  # Bonus for strong signal
    return max(0, min(100, base_uptime - rss_penalty))

def load_production_devices():
    """Load production devices from CSV"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Read CSV
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'prod_batch_uptime_results.csv')
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} devices from CSV")
        
        current_time = datetime.utcnow()
        devices_loaded = 0
        metrics_created = 0
        
        for _, row in df.iterrows():
            device_id = str(row['device_id'])
            name = row['name']
            last_telemetry_str = row['last_telemetry_time']
            rss_value = float(row['rss_value'])
            
            # Parse timestamp
            try:
                last_telemetry = pd.to_datetime(last_telemetry_str)
            except:
                last_telemetry = current_time  # Fallback
            
            # Calculate uptime
            uptime_pct = calculate_uptime(last_telemetry, current_time, rss_value)
            
            # Check if device exists
            existing_device = session.query(Device).filter(Device.device_id == device_id).first()
            
            if existing_device:
                # Update existing (could be test device)
                existing_device.name = name
                existing_device.is_test_device = False
                existing_device.last_seen = last_telemetry
                existing_device.status = "active" if uptime_pct > 50 else "inactive"
                existing_device.device_metadata = {
                    "rss_value": rss_value,
                    "last_telemetry": last_telemetry.isoformat()
                }
                existing_device.updated_at = current_time
            else:
                # Create new device
                new_device = Device(
                    device_id=device_id,
                    name=name,
                    device_type="iot_device",  # Default, can be adjusted
                    status="active" if uptime_pct > 50 else "inactive",
                    is_test_device=False,
                    last_seen=last_telemetry,
                    device_metadata={
                        "rss_value": rss_value,
                        "last_telemetry": last_telemetry.isoformat()
                    }
                )
                session.add(new_device)
                existing_device = new_device
            
            session.commit()
            devices_loaded += 1
            
            # Create initial metrics
            initial_metrics = [
                DeviceMetric(
                    device_id=existing_device.id,
                    timestamp=current_time,
                    metric_type="uptime",
                    value=uptime_pct,
                    unit="percentage"
                ),
                DeviceMetric(
                    device_id=existing_device.id,
                    timestamp=current_time,
                    metric_type="rss_signal",
                    value=rss_value,
                    unit="dBm"
                ),
                DeviceMetric(
                    device_id=existing_device.id,
                    timestamp=current_time,
                    metric_type="telemetry_age_hours",
                    value=(current_time - last_telemetry).total_seconds() / 3600,
                    unit="hours"
                )
            ]
            for metric in initial_metrics:
                session.add(metric)
            session.commit()
            metrics_created += len(initial_metrics)
            
            # Create initial KPI calculation (daily)
            kpi = KPICalculation(
                device_id=existing_device.id,
                calculation_type="uptime_percentage",
                time_period="daily",
                period_start=current_time - timedelta(days=1),
                period_end=current_time,
                value=uptime_pct,
                device_metadata={"source": "batch_load", "rss_adjusted": True}
            )
            session.add(kpi)
            session.commit()
        
        # Optional: Deactivate test devices
        test_devices = session.query(Device).filter(Device.is_test_device == True).all()
        for device in test_devices:
            device.status = "inactive"
            device.is_test_device = False  # Or keep as test but inactive
        session.commit()
        
        print(f"✅ Loaded {devices_loaded} production devices")
        print(f"✅ Created {metrics_created} initial metrics")
        print(f"✅ Deactivated {len(test_devices)} test devices")
        
    except Exception as e:
        print(f"❌ Error loading devices: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    load_production_devices()
