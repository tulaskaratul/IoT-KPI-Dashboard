from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import os
import sys

# Add the project root directory to the Python path
# In Airflow container, DAGs are in /opt/airflow/dags/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up from dags/ to project root
sys.path.insert(0, project_root)

from device_extract import extract_devices, save_devices_to_file, save_devices_to_database

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_device_extraction():
    devices_data = extract_devices()
    save_devices_to_file(devices_data)
    new_count = save_devices_to_database(devices_data)
    print(f"DAG: Extracted {len(devices_data.get('data', []))} devices, {new_count} new")

dag = DAG(
    'device_extraction_dag',
    default_args=default_args,
    description='A DAG to extract devices from samasth.io',
    schedule_interval=timedelta(hours=12),
)

extract_devices_task = PythonOperator(
    task_id='extract_devices_task',
    python_callable=run_device_extraction,
    dag=dag,
)
