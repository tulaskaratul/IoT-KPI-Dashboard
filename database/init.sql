-- IoT KPI Dashboard Database Schema
-- This script initializes the database with all necessary tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100),
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'unknown', -- active, inactive, maintenance
    is_test_device BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE,
    device_metadata JSONB
);

-- Create device_metrics table for storing time-series data
CREATE TABLE IF NOT EXISTS device_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metric_type VARCHAR(100) NOT NULL, -- uptime, response_time, data_throughput, error_count
    value DECIMAL(15,6),
    unit VARCHAR(50),
    tags JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create device_status_history table for tracking status changes
CREATE TABLE IF NOT EXISTS device_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create kpi_calculations table for storing calculated KPIs
CREATE TABLE IF NOT EXISTS kpi_calculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    calculation_type VARCHAR(100) NOT NULL, -- uptime_percentage, availability, response_time_avg
    time_period VARCHAR(50) NOT NULL, -- hourly, daily, weekly, monthly
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    value DECIMAL(15,6) NOT NULL,
    device_metadata JSONB,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_test ON devices(is_test_device);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);

CREATE INDEX IF NOT EXISTS idx_metrics_device_timestamp ON device_metrics(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_type_timestamp ON device_metrics(metric_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON device_metrics(timestamp);

CREATE INDEX IF NOT EXISTS idx_status_history_device ON device_status_history(device_id);
CREATE INDEX IF NOT EXISTS idx_status_history_started ON device_status_history(started_at);

CREATE INDEX IF NOT EXISTS idx_kpi_device_period ON kpi_calculations(device_id, time_period);
CREATE INDEX IF NOT EXISTS idx_kpi_type_period ON kpi_calculations(calculation_type, time_period);
CREATE INDEX IF NOT EXISTS idx_kpi_period_start ON kpi_calculations(period_start);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for devices table
CREATE TRIGGER update_devices_updated_at 
    BEFORE UPDATE ON devices 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some test devices
INSERT INTO devices (device_id, name, device_type, location, status, is_test_device, device_metadata) VALUES
('TEST_DEVICE_001', 'Temperature Sensor 1', 'sensor', 'Building A - Floor 1', 'active', true, '{"model": "TempSense Pro", "firmware": "1.2.3"}'),
('TEST_DEVICE_002', 'Humidity Monitor 1', 'sensor', 'Building A - Floor 2', 'active', true, '{"model": "HumidityMax", "firmware": "2.1.0"}'),
('TEST_DEVICE_003', 'Motion Detector 1', 'sensor', 'Building B - Entrance', 'inactive', true, '{"model": "MotionPro", "firmware": "1.5.2"}'),
('TEST_DEVICE_004', 'Air Quality Monitor', 'sensor', 'Building A - Lobby', 'active', true, '{"model": "AirQuality Pro", "firmware": "3.0.1"}'),
('TEST_DEVICE_005', 'Smart Camera 1', 'camera', 'Building B - Parking', 'maintenance', true, '{"model": "SmartCam 4K", "firmware": "4.2.1"}')
ON CONFLICT (device_id) DO NOTHING;
