import os
import json
import logging
import requests
import psycopg2
from time import sleep
from datetime import datetime, timezone
from typing import Dict, List, Optional
from psycopg2.extras import execute_values
from psycopg2.extensions import connection as PgConnection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03dZ [%(levelname)-8s] %(message)s [%(name)s] loc=%(filename)s:%(lineno)d',
    datefmt='%Y-%m-%dT%H:%M:%S'
)

def get_db_connection(max_retries: int = 3, retry_delay: int = 5) -> PgConnection:
    """
    Create a database connection with retry logic.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay in seconds between retries

    Returns:
        A PostgreSQL database connection

    Raises:
        psycopg2.Error: If connection fails after all retries
    """
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database="iot_kpi_db",
                user="iot_user",
                password="iot_password",
                connect_timeout=10
            )
            logger.info(f"Successfully connected to database at {db_host}:{db_port}")
            return conn
        except psycopg2.Error as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s")
            sleep(retry_delay)

def extract_devices(batch_size: int = 1000, since: Optional[str] = None) -> Dict:
    """
    Extract device information from the API with pagination support.

    Args:
        batch_size: Number of devices to fetch per page
        since: ISO format datetime string to filter devices created after this time

    Returns:
        Dict containing device data, total count, and pages processed

    Raises:
        requests.RequestException: If the API request fails
        ValueError: If the since parameter is not a valid ISO datetime string
    """
    url = "https://samasth.io/api/deviceInfos/all"
    token = os.environ.get("SAMASTH_API_KEY") or "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJhdHVsLnR1bGFza2FyQHViaXFlZGdlLmNvbSIsInVzZXJJZCI6IjJlMzg4OGQwLTYxNmEtMTFmMC1hMGZhLTFmMmU0YjRmMTE0OCIsInNjb3BlcyI6WyJURU5BTlRfQURNSU4iXSwic2Vzc2lvbklkIjoiOWZiYmMyOGItZWY0Yy00OTM3LThjYjItN2QxOTIyZDQ2MTFmIiwiZXhwIjoxNzU5NTUyNjcyLCJpc3MiOiJzYW1hc3RoLmlvIiwiZW5hYmxlZCI6dHJ1ZSwiaXNQdWJsaWMiOmZhbHNlLCJ0ZW5hbnRJZCI6IjExMmY0NmYwLTJiZWMtMTFlYy1iNTRhLTUxNzBhYmVhOTQyZCIsImN1c3RvbWVySWQiOiIxMzgxNDAwMC0xZGQyLTExYjItODA4MC04MDgwODA4MDgwODAifQ.vECfr37F9T4g_Bl6TjlRLu6HbsWhZQGJngYroi6vzFHmTZb2r8EKAqtPUDS6ygtzX47J2Awtz6uvoEEWgUbzUQ"
    
    if not token:
        logger.error("SAMASTH_API_KEY environment variable not set")
        return {"data": [], "totalElements": 0, "pagesProcessed": 0}

    headers = {
        "Authorization": f"Bearer {token}"
    }
    all_devices = []
    page = 0
    since_dt = None

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00')).astimezone(timezone.utc)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid since parameter format: {e}")
            raise ValueError(f"Invalid since parameter: {since}. Expected ISO format datetime string.")

    logger.info(f"Starting device extraction with batch size {batch_size}, since {since}")

    while True:
        params = {
            "pageSize": str(batch_size),
            "page": str(page),
            "sortProperty": "createdTime",
            "sortOrder": "DESC",
            "includeCustomers": "true"
        }

        try:
            logger.debug(f"Fetching page {page} from API")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"API Error: {response.status_code} - {response.text[:200]}")
                break

            data = response.json()
            devices = data.get('data', [])
            total_elements = data.get('totalElements', 0)
            total_pages = data.get('totalPages', 0)
            has_next = data.get('hasNext', False)

            logger.info(f"Page {page}: Retrieved {len(devices)} devices (Total: {total_elements}, Pages: {total_pages})")

            if not devices:
                logger.info(f"No more devices found on page {page}")
                break

            if since_dt:
                stop = False
                for device in devices:
                    device_time = device.get('createdTime', '')
                    if not device_time:
                        logger.warning(f"Device {device.get('id', {}).get('id', 'unknown')} missing createdTime")
                        continue
                    
                    try:
                        device_dt = datetime.fromisoformat(device_time.replace('Z', '+00:00')).astimezone(timezone.utc)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid device timestamp format: {e}")
                        continue
                    
                    if device_dt > since_dt:
                        all_devices.append(device)
                    else:
                        logger.info(f"Stopping early: found device from {device_dt} <= {since_dt}")
                        stop = True
                        break
                
                if stop:
                    break
            else:
                all_devices.extend(devices)

            if not has_next or page >= total_pages - 1:
                logger.info(f"Reached end of pagination (page {page}/{total_pages})")
                break

            page += 1

        except requests.Timeout:
            logger.error(f"Request timeout on page {page}")
            break
        except requests.RequestException as e:
            logger.error(f"Request failed on page {page}: {e}")
            break
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error on page {page}: {e}")
            logger.debug(f"Response content: {response.text[:500]}")
            break

    logger.info(f"Extraction complete: {len(all_devices)} devices from {page + 1} pages")
    return {"data": all_devices, "totalElements": len(all_devices), "pagesProcessed": page + 1}

def save_devices_to_file(devices: Dict, filename: str = "devices.json") -> None:
    """
    Save device data to a JSON file.

    Args:
        devices: Dictionary containing device data
        filename: Name of the file to save the data to

    Raises:
        OSError: If file cannot be written
        TypeError: If devices cannot be serialized to JSON
    """
    try:
        logger.info(f"Saving {len(devices.get('data', []))} devices to {filename}")
        with open(filename, "w") as file:
            json.dump(devices, file, indent=4)
        logger.info(f"Successfully saved devices data to {filename}")
    except TypeError as e:
        logger.error(f"Failed to serialize devices data to JSON: {e}")
        raise
    except OSError as e:
        logger.error(f"Failed to write to file {filename}: {e}")
        raise

def save_devices_to_database(devices_data: Dict) -> int:
    """
    Save device data to the database, updating existing entries and inserting new ones.

    Args:
        devices_data: Dictionary containing device data with a 'data' key containing list of devices

    Returns:
        int: Number of new devices inserted

    Raises:
        psycopg2.Error: If there's a database error
        KeyError: If required device data fields are missing
    """
    conn = None
    cursor = None
    inserted_count = 0
    devices = devices_data.get('data', [])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info(f"Processing {len(devices)} devices for database update")
        updated_count = 0

        for device in devices:
            try:
                device_id = device['id']['id']  # This is already a UUID string
                name = device['name']
                device_type = device.get('type', '')
                status = 'active' if device.get('active', False) else 'inactive'
                created_time = device.get('createdTime')
                if created_time and isinstance(created_time, str):
                    try:
                        install_date = datetime.fromisoformat(created_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        install_date = None
                else:
                    install_date = None

                cursor.execute("SELECT device_id FROM devices WHERE device_id = %s", (device_id,))
                existing = cursor.fetchone()

                if existing:
                    cursor.execute("""
                        UPDATE devices
                        SET name = %s, device_type = %s, status = %s, install_date = %s
                        WHERE device_id = %s
                    """, (name, device_type, status, install_date, device_id))
                    updated_count += 1
                else:
                    cursor.execute("""
                        INSERT INTO devices (device_id, name, device_type, status, install_date)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (device_id, name, device_type, status, install_date))
                    inserted_count += 1

            except KeyError as e:
                logger.error(f"Missing required field in device data: {e}")
                continue
            except psycopg2.Error as e:
                logger.error(f"Database error processing device {device.get('id', {}).get('id', 'unknown')}: {e}")
                continue

        conn.commit()
        logger.info(f"Database update complete: {inserted_count} new devices, {updated_count} updated")
        return inserted_count

    except psycopg2.Error as e:
        logger.error(f"Database error during device save operation: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        logger.info("Starting device extraction process")
        devices_data = extract_devices()
        
        if not devices_data.get('data'):
            logger.warning("No devices found to process")
            exit(1)
            
        logger.info(f"Processing {len(devices_data.get('data', []))} devices")
        save_devices_to_file(devices_data)
        logger.info("Saved devices data to file")
        
        new_devices_count = save_devices_to_database(devices_data)
        logger.info(f"Database operation complete - {new_devices_count} new devices added")
        
    except Exception as e:
        logger.error(f"Process failed with error: {e}")
        exit(1)
    else:
        logger.info("Device extraction process completed successfully")
        exit(0)