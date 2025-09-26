# IoT KPI Platform - API and KPI Guide

This document explains how to use the API, what data is collected, how metrics are produced, and how KPIs are computed and retrieved. All examples assume the stack is running via `docker-compose`.

- API base URL: `http://localhost:8000/api/v1`
- Interactive docs (OpenAPI): `http://localhost:8000/docs`

## Authentication
No authentication is required in this test setup. For production, add proper auth before exposing externally.

## Devices

### What devices are available?
Seeded test devices are inserted on first run via `database/init.sql`:
- `TEST_DEVICE_001` Temperature Sensor 1
- `TEST_DEVICE_002` Humidity Monitor 1
- `TEST_DEVICE_003` Motion Detector 1
- `TEST_DEVICE_004` Air Quality Monitor
- `TEST_DEVICE_005` Smart Camera 1

All seeded devices have `is_test_device = true`.

### Device fields (table `devices`)
- `device_id` (string, unique)
- `name`, `device_type`, `location`, `status`
- `is_test_device` (bool)
- `last_seen` (timestamp)
- `device_metadata` (JSONB)

### List devices
```
curl "http://localhost:8000/api/v1/devices?skip=0&limit=50&test_devices_only=true"
```
Response includes `devices[]`, `total`, `skip`, `limit`.

### Get device by id
```
curl "http://localhost:8000/api/v1/devices/TEST_DEVICE_001"
```

### Create a device
```
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_id":"MY_DEVICE_001",
    "name":"My Device",
    "device_type":"sensor",
    "location":"Lab",
    "status":"active",
    "is_test_device":true,
    "device_metadata":{"model":"X","fw":"1.0"}
  }'
```

### Update a device
```
curl -X PUT http://localhost:8000/api/v1/devices/MY_DEVICE_001 \
  -H "Content-Type: application/json" \
  -d '{"status":"inactive"}'
```

### Delete a device
```
curl -X DELETE http://localhost:8000/api/v1/devices/MY_DEVICE_001
```

### Device status and basic uptime check
```
curl "http://localhost:8000/api/v1/devices/TEST_DEVICE_001/status"
```
- `is_online` is derived from `last_seen` within the last 5 minutes.

## Metrics

### How metrics are collected (logic)
- Service: `src/collectors/device_collector.py`
- Runs every `COLLECTION_INTERVAL` seconds (default 60).
- For test devices, data is simulated to mimic realistic behavior by `device_type`.
- For each device cycle, the collector:
  - Updates `devices.last_seen`.
  - Writes time-series rows into `device_metrics` for:
    - `uptime` (0.0–1.0, later shown as percentage)
    - `response_time` (ms)
    - `data_throughput` (bytes/s)
    - `error_count` (count)
    - `request_count` (count)
  - Updates `device_status_history` when status changes.

### Metric fields (table `device_metrics`)
- `device_id` (UUID FK to `devices.id`)
- `timestamp`
- `metric_type` (e.g. `uptime`, `response_time`)
- `value`, `unit`, `tags`

### Get metrics for a device
```
curl "http://localhost:8000/api/v1/devices/TEST_DEVICE_001/metrics?metric_type=uptime&limit=1000"
```
Query params:
- `metric_type` optional filter
- `start_time`, `end_time` ISO timestamps
- `limit` (default 1000)

### Metrics summary (all devices)
```
curl "http://localhost:8000/api/v1/metrics/summary?time_period=24h"
```
Returns counts and basic stats per metric type in the period.

## KPIs

### KPI definitions (implemented)
- `uptime_percentage`: Percentage of time a device was in `active` status within the period (calculated from `device_status_history`).
- `availability`: Average of `uptime` metric values within the period (0–1).
- `response_time_avg`: Mean of `response_time` within the period.
- `error_rate`: `error_count` / `request_count` within the period, as percentage.

Code: `src/api/routes/kpis.py`

### Calculate KPIs for a device (on-demand)
```
curl -X POST "http://localhost:8000/api/v1/devices/TEST_DEVICE_001/kpis/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "calculation_types":["uptime_percentage","availability","response_time_avg","error_rate"],
    "time_period":"daily",
    "period_start":"2025-09-25T00:00:00Z",
    "period_end":"2025-09-26T00:00:00Z",
    "kpi_metadata":{"note":"manual calc"}
  }'
```
- Stores results in `kpi_calculations` and returns a summary of values.

### Get saved KPIs for a device
```
curl "http://localhost:8000/api/v1/devices/TEST_DEVICE_001/kpis?calculation_type=uptime_percentage&time_period=daily&limit=50"
```

### KPI summary across devices
```
curl "http://localhost:8000/api/v1/kpis/summary?time_period=daily&limit=100"
```

## Health and Troubleshooting

### Health
```
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/detailed
```

### Common issues
- 500 errors on `/devices`: database schema out of sync. Run `docker-compose down -v && docker-compose up -d` to recreate with latest schema.
- No metrics displayed: wait for collector (runs every minute) or run `scripts/init_db.py` locally to seed historic data.
- Grafana panels empty: confirm datasource points to `postgres` and use a time range that includes data.

## Postman Collection (optional)
You can import the OpenAPI spec from `http://localhost:8000/openapi.json` into Postman.
