# 🚀 Quick Start Guide - IoT KPI Dashboard

Get your production-grade IoT KPI pipeline running in 5 minutes!

## Prerequisites

- Docker & Docker Compose installed
- 4GB RAM minimum
- Python 3.8 or higher (for local development)
- Git
- Ports available: 5432, 3000, 8000, 8080, 6379 (Redis)
- PostgreSQL client (optional, for direct database access)

## Step 1: Clone & Configure (1 min)

```bash
# Clone the repository
git clone https://github.com/tulaskaratul/IoT-KPI-Dashboard.git
cd IoT-KPI-Dashboard

# Create and configure environment file
cp env.example .env

# Set Airflow UID (Linux/Mac only)
echo "AIRFLOW_UID=$(id -u)" >> .env

# For Windows, use:
echo AIRFLOW_UID=50000 >> .env

# Update environment variables in .env:
# - Set your SAMASTH_API_KEY
# - Configure database credentials if needed
# - Set appropriate log levels
```

## Step 2: Start Services (2 min)

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# Check logs if needed
docker-compose logs -f postgres
```

## Step 3: Create Test Data (30 sec)

```bash
# Insert test devices
# For Windows PowerShell:
docker exec iot_kpi_postgres psql -U iot_user -d iot_kpi_db -c ^
"INSERT INTO devices (device_id, name, is_test_device, status) VALUES ^
  (gen_random_uuid(), 'Test Device 1', true, 'active'), ^
  (gen_random_uuid(), 'Test Device 2', true, 'active'), ^
  (gen_random_uuid(), 'Test Device 3', true, 'active');"

# For Windows CMD:
docker exec iot_kpi_postgres psql -U iot_user -d iot_kpi_db -c "INSERT INTO devices (device_id, name, is_test_device, status) VALUES (gen_random_uuid(), 'Test Device 1', true, 'active'), (gen_random_uuid(), 'Test Device 2', true, 'active'), (gen_random_uuid(), 'Test Device 3', true, 'active');"

# For Linux/Mac (original command):
docker exec -it iot_kpi_postgres psql -U iot_user -d iot_kpi_db << 'EOF'
INSERT INTO devices (device_id, name, is_test_device, status)
VALUES
  (gen_random_uuid(), 'Test Device 1', true, 'active'),
  (gen_random_uuid(), 'Test Device 2', true, 'active'),
  (gen_random_uuid(), 'Test Device 3', true, 'active');
EOF
```

## Step 4: Create Airflow Admin User (1 min)

```bash
# Create initial admin user (run this once after first startup)
docker exec -it iot_kpi_airflow_webserver airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Access Airflow UI
open http://localhost:8080
# Username: admin, Password: admin

# Steps in UI:
1. Find "iot_kpi_dashboard" DAG
2. Toggle it ON (switch on left)
3. Click "Trigger DAG" (play button)
4. Wait ~30 seconds for completion
```

## Step 5: View Dashboard (1 min)

```bash
# Access Grafana
open http://localhost:3000
# Username: admin, Password: admin123

# Configure PostgreSQL Datasource (if not auto-detected):
1. Go to Configuration → Data Sources
2. Click "Add data source"
3. Select "PostgreSQL"
4. Configure:
   - Name: PostgreSQL
   - Host: postgres:5432
   - Database: iot_kpi_db
   - Username: iot_user
   - Password: iot_password
   - SSL Mode: disable
5. Click "Save & Test"

# Import Dashboard:
1. Click "+" → Import
2. Upload file: grafana/dashboards/iot-kpi-production.json
3. Select "PostgreSQL" datasource
4. Click "Import"
```

## ✅ Verify Setup

After 5 minutes, you should see:

### Airflow (http://localhost:8080)
- ✅ DAG `iot_kpi_dashboard` is green
- ✅ Last run successful
- ✅ 3 tasks completed (ingest → aggregate → clean)

### Grafana (http://localhost:3000)
- ✅ Panel 1: Active vs Inactive devices (pie chart)
- ✅ Panel 2: Uptime % trend (time series)
- ✅ Panel 3: Signal strength distribution (bar chart)
- ✅ Panel 4: Device details (table)

### Database Check
```bash
# Check data (Windows PowerShell):
docker exec iot_kpi_postgres psql -U iot_user -d iot_kpi_db -c "SELECT (SELECT COUNT(*) FROM devices) as devices, (SELECT COUNT(*) FROM telemetry_logs) as telemetry_records, (SELECT COUNT(*) FROM device_status) as aggregated_records;"

# Check data (Windows CMD):
docker exec iot_kpi_postgres psql -U iot_user -d iot_kpi_db -c "SELECT (SELECT COUNT(*) FROM devices) as devices, (SELECT COUNT(*) FROM telemetry_logs) as telemetry_records, (SELECT COUNT(*) FROM device_status) as aggregated_records;"

# Check data (Linux/Mac):
docker exec -it iot_kpi_postgres psql -U iot_user -d iot_kpi_db -c "
SELECT
  (SELECT COUNT(*) FROM devices) as devices,
  (SELECT COUNT(*) FROM telemetry_logs) as telemetry_records,
  (SELECT COUNT(*) FROM device_status) as aggregated_records;
"
```

Expected output after first DAG run:
```
 devices | telemetry_records | aggregated_records 
---------+-------------------+--------------------
       3 |                 3 |                  3
```

## 🎯 What Just Happened?

1. **Postgres** initialized with schema (devices, telemetry_logs, device_status)
2. **Airflow DAG** runs every 5 minutes:
   - Ingests telemetry from test devices
   - Aggregates data into device_status table
   - Cleans old logs (30+ days)
3. **Grafana** displays:
   - Real-time status from telemetry_logs
   - Historical trends from device_status (pre-aggregated for speed!)

## 📊 Architecture Flow

```
Test Devices (Mock Data)
    ↓
Airflow DAG (Every 5 min)
├─ Task 1: Ingest → telemetry_logs
├─ Task 2: Aggregate → device_status  
└─ Task 3: Clean old data
    ↓
Grafana Dashboard
├─ Panel 1: Real-time (telemetry_logs)
└─ Panels 2-4: Batch KPIs (device_status)
```

## 🔧 Common Issues

### Airflow Login Issues?
```bash
# If you get "Invalid login" error, create admin user:
# Windows PowerShell:
docker exec iot_kpi_airflow_webserver airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com

# Linux/Mac:
docker exec -it iot_kpi_airflow_webserver airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Then try logging in with: admin / admin
```

### Airflow DAG Not Running?
```bash
# Check scheduler logs (Windows PowerShell):
docker logs iot_kpi_airflow_scheduler

# Check scheduler logs (Linux/Mac):
docker logs iot_kpi_airflow_scheduler

# Restart if needed
docker-compose restart airflow-scheduler
```

### Grafana "Datasource postgres was not found"?
```bash
# Restart Grafana to reload datasource provisioning
docker-compose restart grafana

# Wait 30 seconds, then refresh the dashboard
# The datasource should now be available as "PostgreSQL"

# Alternative: Check if datasource provisioning worked
docker logs iot_kpi_grafana | grep -i postgres

# If still not working, manually add PostgreSQL datasource:
1. Grafana → Configuration → Data Sources → "Add data source"
2. Select "PostgreSQL"
3. Configure:
   - Name: PostgreSQL
   - Host: postgres:5432
   - Database: iot_kpi_db
   - Username: iot_user
   - Password: iot_password
   - SSL Mode: disable
4. Save & Test
```

### Grafana Shows No Data?
```bash
# Verify PostgreSQL datasource
1. Grafana → Configuration → Data Sources
2. Check "PostgreSQL" connection
3. Test & Save

# Manually trigger DAG in Airflow UI
```

### Port Conflicts?
```bash
# Check what's using ports
netstat -ano | findstr :8080  # Windows
lsof -i :8080                 # Mac/Linux

# Change ports in docker-compose.yml if needed
```

### Python Environment Issues?
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify Python path
python -c "import sys; print(sys.executable)"
```

### Database Connection Issues?
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Verify connection settings
docker compose logs postgres

# Test connection manually
psql -h localhost -U iot_user -d iot_kpi_db
```

### Redis Connection Issues?
```bash
# Check Redis status
docker compose ps redis
docker compose logs redis

# Test Redis connection
docker exec -it iot_kpi_redis redis-cli ping
```

## 🎓 Next Steps

1. **Production Data**: Replace mock data with real MQTT/API sources
   - See `dags/iot_kpi_dag.py` → `ingest_telemetry()` function
   
2. **Customize Dashboard**: Edit Grafana panels for your metrics
   - See `docs/PRODUCTION_PIPELINE_GUIDE.md` for SQL queries
   
3. **Scale Up**: Enable CeleryExecutor for distributed processing
   - See docker-compose.yml comments

4. **Monitoring**: Set up alerts in Grafana
   - Alert when uptime < 80%
   - Alert when device offline > 10 min

## 📚 Documentation

- **Full Guide**: [docs/PRODUCTION_PIPELINE_GUIDE.md](docs/PRODUCTION_PIPELINE_GUIDE.md)
- **API Reference**: [docs/API_GUIDE.md](docs/API_GUIDE.md)
- **Database Schema**: [database/init.sql](database/init.sql)
- **Airflow DAG**: [dags/iot_kpi_dag.py](dags/iot_kpi_dag.py)

## Production Deployment

For production deployment, follow these additional steps:

1. **Create Production Environment**
```bash
cp env.example .env.prod
```

2. **Update Production Settings**
- Set secure passwords
- Configure production endpoints
- Set appropriate log levels
- Enable SSL/TLS
- Configure backup settings

3. **Start Production Services**
```bash
export COMPOSE_FILE=docker-compose.yml
docker compose --env-file .env.prod up -d
```

4. **Monitor Deployment**
```bash
# Check service status
docker compose ps

# Monitor logs
docker compose logs -f

# Check specific service
docker compose logs -f [service_name]
```

## 🎉 You're Ready!

Your production-grade IoT KPI pipeline is now running. The system provides:

### Core Features
- ✅ Automated device data collection
- ✅ Real-time KPI calculations
- ✅ Comprehensive error handling and retries
- ✅ Scalable data processing with Airflow
- ✅ High-performance data visualization
- ✅ Secure API endpoints

### Monitoring & Management
- ✅ Ingest telemetry every 5 minutes
- ✅ Compute KPIs automatically
- ✅ Keep your Grafana dashboard blazing fast
- ✅ Automatic error recovery
- ✅ Comprehensive logging
- ✅ Data persistence and backups

**Access Points:**
- Grafana: http://localhost:3000 (Dashboards & Monitoring)
- Airflow: http://localhost:8080 (Pipeline Management)
- API: http://localhost:8000 (Data Access)
- Database: localhost:5432 (Direct Data Access)
- Redis: localhost:6379 (Cache & Queue)

For detailed usage and customization, refer to:
- [Production Pipeline Guide](docs/PRODUCTION_PIPELINE_GUIDE.md)
- [API Documentation](docs/API_GUIDE.md)
- [Database Schema](database/init.sql)

Happy monitoring! 🚀
