import requests
import json
import psycopg2
from psycopg2.extras import execute_values
import os

def get_db_connection():
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    return psycopg2.connect(
        host=db_host,
        port=db_port,
        database="iot_kpi_db",
        user="iot_user",
        password="iot_password"
    )


def extract_devices(batch_size=1000, since=None):
    url = "https://samasth.io/api/deviceInfos/all"
    token = os.environ.get("SAMASTH_API_KEY") or "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJhdHVsLnR1bGFza2FyQHViaXFlZGdlLmNvbSIsInVzZXJJZCI6IjJlMzg4OGQwLTYxNmEtMTFmMC1hMGZhLTFmMmU0YjRmMTE0OCIsInNjb3BlcyI6WyJURU5BTlRfQURNSU4iXSwic2Vzc2lvbklkIjoiOWZiYmMyOGItZWY0Yy00OTM3LThjYjItN2QxOTIyZDQ2MTFmIiwiZXhwIjoxNzU5NTUyNjcyLCJpc3MiOiJzYW1hc3RoLmlvIiwiaWF0IjoxNzU5NDY2MjcyLCJlbmFibGVkIjp0cnVlLCJpc1B1YmxpYyI6ZmFsc2UsInRlbmFudElkIjoiMTEyZjQ2ZjAtMmJlYy0xMWVjLWI1NGEtNTE3MGFiZWE5NDJkIiwiY3VzdG9tZXJJZCI6IjEzODE0MDAwLTFkZDItMTFiMi04MDgwLTgwODA4MDgwODA4MCJ9.vECfr37F9T4g_Bl6TjlRLu6HbsWhZQGJngYroi6vzFHmTZb2r8EKAqtPUDS6ygtzX47J2Awtz6uvoEEWgUbzUQ"
    if not token:
        print("Error: SAMASTH_API_KEY environment variable not set. Please set SAMASTH_API_KEY environment variable.")
        return {"data": []}

    headers = {
        "Authorization": f"Bearer {token}"
    }
    all_devices = []
    page = 0
    print(f"Starting device extraction with batch size {batch_size}, since {since}")
    while True:
        params = {
            "pageSize": str(batch_size),
            "page": str(page),
            "sortProperty": "createdTime",
            "sortOrder": "DESC",
            "includeCustomers": "true"
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"Page {page}: HTTP {response.status_code}")

            if response.status_code != 200:
                print(f"API Error: {response.status_code} - {response.text[:200]}")
                break

            data = response.json()
            devices = data.get('data', [])
            total_elements = data.get('totalElements', 0)
            total_pages = data.get('totalPages', 0)
            has_next = data.get('hasNext', False)

            print(f"Page {page}: {len(devices)} devices retrieved")
            print(f"Total pages: {total_pages}, Has next: {has_next}, Total devices: {total_elements}")

            if not devices:
                print(f"No more devices found on page {page}")
                break

            # If since is provided, only include newer devices
            if since:
                new_devices = [d for d in devices if d.get('createdTime', '') > since]
                if len(new_devices) < len(devices):
                    print(f"Filtered out {len(devices) - len(new_devices)} devices older than {since}")
                    all_devices.extend(new_devices)
                    break  # Stop early since we've hit old devices
                all_devices.extend(new_devices)
            else:
                all_devices.extend(devices)

            if not has_next or page >= total_pages - 1:
                print(f"Reached end of pagination (page {page}/{total_pages})")
                break

            if not has_next or page >= total_pages - 1:
                print(f"Reached end of pagination (page {page}/{total_pages})")
                break

            page += 1

        except requests.RequestException as e:
            print(f"Request failed on page {page}: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"JSON decode error on page {page}: {e}")
            print(f"Response content: {response.text[:500]}")
            break

    print(f"Extraction complete: {len(all_devices)} devices from {page + 1} pages")
    return {"data": all_devices, "totalElements": len(all_devices), "pagesProcessed": page + 1}

def save_devices_to_file(devices, filename="devices.json"):
    with open(filename, "w") as file:
        json.dump(devices, file, indent=4)

def save_devices_to_database(devices_data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        devices = devices_data.get('data', [])
        inserted_count = 0

        for device in devices:
            device_id = device['id']['id']
            name = device['name']
            device_type = device.get('type', '')
            status = 'active' if device.get('active', False) else 'inactive'
            install_date = device.get('createdTime')

            cursor.execute("SELECT device_id FROM devices WHERE device_id = %s", (device_id,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE devices
                    SET name = %s, device_type = %s, status = %s, install_date = %s
                    WHERE device_id = %s
                """, (name, device_type, status, install_date, device_id))
            else:
                cursor.execute("""
                    INSERT INTO devices (device_id, name, device_type, status, install_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (device_id, name, device_type, status, install_date))
                inserted_count += 1

        conn.commit()
        cursor.close()
        conn.close()

        print(f"Database updated: {inserted_count} new devices, {len(devices) - inserted_count} updated")
        return inserted_count

    except Exception as e:
        print(f"Database error: {e}")
        return 0

if __name__ == "__main__":
    devices_data = extract_devices()
    if devices_data:
        save_devices_to_file(devices_data)
        new_devices_count = save_devices_to_database(devices_data)
        print(f"Total devices processed: {len(devices_data.get('data', []))}")
        print(f"New devices added to database: {new_devices_count}")
