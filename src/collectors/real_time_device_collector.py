import time
import requests
import json
import os
import sys
import psycopg2

# Add the project directory to the system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../../')

from device_extract import extract_devices, save_devices_to_file, save_devices_to_database

def get_db_connection():
    # Use environment variable or default to localhost for external connections
    db_host = os.getenv("DB_HOST", "localhost")
    return psycopg2.connect(
        host=db_host,
        database="iot_kpi_db",
        user="iot_user",
password=os.getenv("DB_PASSWORD", "iot_password")
    )

def get_last_updated():
    # Get the last updated timestamp from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(install_date) FROM devices")
    last_updated = cursor.fetchone()[0]
    conn.close()
    return last_updated

def real_time_device_collection(interval=300):  # 5 minutes
    while True:
        try:
            last_updated = get_last_updated()
            devices_data = extract_devices(since=last_updated)
            if devices_data:
                save_devices_to_file(devices_data)
                new_devices_count = save_devices_to_database(devices_data)
                print(f" Real-time update: {len(devices_data.get('data', []))} devices processed, {new_devices_count} new devices added")
            else:
                print("No new devices data received")
        except Exception as e:
            print(f"Real-time collection error: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    real_time_device_collection()
