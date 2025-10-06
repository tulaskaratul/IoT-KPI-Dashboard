-- Aggregation SQL for device_status table
-- This computes uptime percentage, avg RSS, and active/inactive minutes
-- Run every 5 minutes by Airflow to keep device_status up-to-date

INSERT INTO device_status (
    device_id, 
    window_start, 
    window_end, 
    uptime_percentage, 
    avg_rss, 
    active_minutes, 
    inactive_minutes
)
SELECT
    device_id,
    window_start,
    window_end,
    -- Calculate uptime as percentage of records within 5 min threshold
    (SUM(CASE WHEN age_minutes <= 5 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100) AS uptime_percentage,
    AVG(rss_value) AS avg_rss,
    -- Count active minutes (telemetry within 5 min)
    SUM(CASE WHEN age_minutes <= 5 THEN 1 ELSE 0 END) AS active_minutes,
    -- Count inactive minutes (telemetry older than 5 min)
    SUM(CASE WHEN age_minutes > 5 THEN 1 ELSE 0 END) AS inactive_minutes
FROM (
    SELECT 
        device_id,
        rss_value,
        date_trunc('hour', timestamp) AS window_start,
        date_trunc('hour', timestamp) + interval '1 hour' AS window_end,
        EXTRACT(EPOCH FROM (NOW() - timestamp)) / 60 AS age_minutes
    FROM telemetry_logs
    WHERE timestamp >= NOW() - interval '1 hour'
      AND timestamp < NOW()
) sub
GROUP BY device_id, window_start, window_end
ON CONFLICT (device_id, window_start, window_end) 
DO UPDATE SET
    uptime_percentage = EXCLUDED.uptime_percentage,
    avg_rss = EXCLUDED.avg_rss,
    active_minutes = EXCLUDED.active_minutes,
    inactive_minutes = EXCLUDED.inactive_minutes;
