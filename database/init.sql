-- IoT KPI Dashboard Database Schema
-- This script initializes the database with all necessary tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create devices table
CREATE TABLE IF NOT EXISTS devices (
    device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    install_date TIMESTAMP DEFAULT NOW(),
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
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
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
    device_id UUID NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create kpi_calculations table for storing calculated KPIs
CREATE TABLE IF NOT EXISTS kpi_calculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(device_id) ON DELETE CASCADE,
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

-- telemetry log table (raw)
CREATE TABLE IF NOT EXISTS telemetry_logs (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID REFERENCES devices(device_id),
    timestamp TIMESTAMP NOT NULL,
    rss_value FLOAT,
    raw_payload JSONB
);

-- derived status table (aggregates)
CREATE TABLE IF NOT EXISTS device_status (
    device_id UUID,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    uptime_percentage FLOAT,
    avg_rss FLOAT,
    active_minutes INT,
    inactive_minutes INT,
    PRIMARY KEY (device_id, window_start, window_end)
);

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_telemetry_logs_device_timestamp ON telemetry_logs(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_telemetry_logs_timestamp ON telemetry_logs(timestamp);

CREATE INDEX IF NOT EXISTS idx_device_status_device_window ON device_status(device_id, window_start, window_end);
CREATE INDEX IF NOT EXISTS idx_device_status_window ON device_status(window_start, window_end);


