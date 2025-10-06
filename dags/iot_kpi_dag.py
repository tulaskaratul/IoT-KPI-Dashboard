from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import psycopg2
import json
import logging
import os
from psycopg2.extras import execute_values

# Configure logging
logger = logging.getLogger(__name__)

# Database connection parameters
DB_CONFIG = {
    "dbname": "iot_kpi_db",
    "user": "iot_user",
    "password": "iot_password",
    "host": "postgres",
    "port": 5432
}

def get_db_connection():
    """Create and return a database connection with error handling."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise

def get_telemetry_data():
    """
    Fetch latest telemetry data from samasth.io API
    """
    import requests
    import os

    # First get the list of devices
    base_url = "https://samasth.io/api"
    devices_url = f"{base_url}/deviceInfos/all?pageSize=100&page=0&sortProperty=createdTime&sortOrder=DESC&includeCustomers=true"
    token = os.environ.get("SAMASTH_API_KEY") or "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJhdHVsLnR1bGFza2FyQHViaXFlZGdlLmNvbSIsInVzZXJJZCI6IjJlMzg4OGQwLTYxNmEtMTFmMC1hMGZhLTFmMmU0YjRmMTE0OCIsInNjb3BlcyI6WyJURU5BTlRfQURNSU4iXSwic2Vzc2lvbklkIjoiOWZiYmMyOGItZWY0Yy00OTM3LThjYjItN2QxOTIyZDQ2MTFmIiwiZXhwIjoxNzU5NTUyNjcyLCJpc3MiOiJzYW1hc3RoLmlvIiwiaWF0IjoxNzU5NDY2MjcyLCJlbmFibGVkIjp0cnVlLCJpc1B1YmxpYyI6ZmFsc2UsInRlbmFudElkIjoiMTEyZjQ2ZjAtMmJlYy0xMWVjLWI1NGEtNTE3MGFiZWE5NDJkIiwiY3VzdG9tZXJJZCI6IjEzODE0MDAwLTFkZDItMTFiMi04MDgwLTgwODA4MDgwODA4MCJ9.vECfr37F9T4g_Bl6TjlRLu6HbsWhZQGJngYroi6vzFHmTZb2r8EKAqtPUDS6ygtzX47J2Awtz6uvoEEWgUbzUQ"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        # First get list of devices
        response = requests.get(devices_url, headers=headers, timeout=30)
        if response.status_code == 200:
            devices_data = response.json()
            devices = devices_data.get('data', [])
            logger.info(f"Fetched {len(devices)} devices from API")

            # For each device, get its latest telemetry
            telemetry_list = []
            for device in devices:
                device_id = device.get('id')
                if device_id:
                    telemetry_url = f"{base_url}/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys=rss_value&startTs={int((datetime.now() - timedelta(minutes=5)).timestamp()*1000)}&endTs={int(datetime.now().timestamp()*1000)}"
                    tel_response = requests.get(telemetry_url, headers=headers, timeout=30)
                    if tel_response.status_code == 200:
                        tel_data = tel_response.json()
                        if tel_data.get('rss_value'):
                            latest = tel_data['rss_value'][-1]  # Get the latest value
                            telemetry_list.append({
                                'device_id': device_id,
                                'rss_value': latest['value'],
                                'timestamp': latest['ts'] / 1000  # Convert from milliseconds to seconds
                            })

            logger.info(f"Fetched telemetry for {len(telemetry_list)} active devices")
            return telemetry_list
        else:
            logger.error(f"Failed to fetch devices: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching telemetry data: {e}")
        return []

def ingest_telemetry():
    """
    Ingest telemetry data from samasth.io API.
    Fetches latest RSS values for all devices.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch live telemetry data from API
        telemetry_list = get_telemetry_data()

        if not telemetry_list:
            logger.warning("No telemetry data fetched from API")
            return

        logger.info(f"Ingesting {len(telemetry_list)} telemetry records")

        # Prepare data for batch insert
        telemetry_data = []
        now = datetime.now()
        for item in telemetry_list:
            device_id = item.get('device_id')
            rss_value = item.get('rss_value')
            timestamp = item.get('timestamp')
            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp)
            else:
                timestamp = now
            payload = {
                "device_id": str(device_id),
                "source": "api_ingestion",
                "ingested_at": now.isoformat(),
                "api_timestamp": timestamp.isoformat()
            }
            telemetry_data.append((device_id, rss_value, json.dumps(payload)))

        if telemetry_data:
            # Convert to simple execute for testing purposes
            placeholders = ", ".join("(%s, %s, %s, %s)" for _ in telemetry_data)
            query = f"""
                INSERT INTO telemetry_logs (device_id, timestamp, rss_value, raw_payload)
                VALUES {placeholders}
                """
            flattened_args = []
            for d in telemetry_data:
                flattened_args.extend([d[0], now, d[1], d[2]])
            cur.execute(query, flattened_args)

        conn.commit()
        logger.info(f"Successfully ingested {len(telemetry_data)} live telemetry records")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in ingest_telemetry: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def aggregate_status():
    """
    Aggregate telemetry data into device_status table.
    Calculates uptime percentage and signal strength metrics per hour.
    Uses external SQL file for maintainability.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Read SQL from external file
        sql_file_path = '/opt/airflow/dags/sql/aggregate_status.sql'
        
        if os.path.exists(sql_file_path):
            with open(sql_file_path, 'r') as f:
                sql_query = f.read()
            logger.info("Using SQL from external file")
        else:
            # Fallback to inline SQL if file doesn't exist
            logger.warning(f"SQL file not found: {sql_file_path}, using inline SQL")
            sql_query = """
                INSERT INTO device_status (
                    device_id, window_start, window_end, uptime_percentage, 
                    avg_rss, active_minutes, inactive_minutes
                )
                SELECT
                    device_id,
                    window_start,
                    window_end,
                    (SUM(CASE WHEN age_minutes <= 5 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) * 100) AS uptime_percentage,
                    AVG(rss_value) AS avg_rss,
                    SUM(CASE WHEN age_minutes <= 5 THEN 1 ELSE 0 END) AS active_minutes,
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
                    inactive_minutes = EXCLUDED.inactive_minutes
            """
        
        cur.execute(sql_query)
        rows_affected = cur.rowcount
        conn.commit()
        
        logger.info(f"Successfully aggregated status for {rows_affected} device-hour windows")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in aggregate_status: {e}")
        raise
    finally:
        if conn:
            cur.close()
            conn.close()

def clean_old_logs():
    """
    Archive or delete telemetry logs older than 30 days.
    For production: export to S3/cloud storage before deletion.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # First, count how many records will be deleted
        cur.execute("""
            SELECT COUNT(*) 
            FROM telemetry_logs 
            WHERE timestamp < NOW() - interval '30 days'
        """)
        count = cur.fetchone()[0]
        
        if count == 0:
            logger.info("No old logs to clean")
            return
        
        logger.info(f"Preparing to clean {count} old telemetry records")
        
        # TODO: For production, export to S3 before deletion
        # Example: export_to_s3(cur, "SELECT * FROM telemetry_logs WHERE timestamp < NOW() - interval '30 days'")
        
        # Delete old records
        cur.execute("""
            DELETE FROM telemetry_logs
            WHERE timestamp < NOW() - interval '30 days'
        """)
        
        conn.commit()
        logger.info(f"Successfully cleaned {count} old telemetry records")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in clean_old_logs: {e}")
        raise
    finally:
        if conn:
            cur.close()
            conn.close()

default_args = {
    'owner': 'iot',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG('iot_kpi_dashboard',
         default_args=default_args,
         schedule='*/5 * * * *',
         catchup=False) as dag:

    t1 = PythonOperator(
        task_id='ingest_telemetry',
        python_callable=ingest_telemetry
    )

    t2 = PythonOperator(
        task_id='aggregate_status',
        python_callable=aggregate_status
    )

    t3 = PythonOperator(
        task_id='clean_old_logs',
        python_callable=clean_old_logs
    )

    t1 >> t2 >> t3
