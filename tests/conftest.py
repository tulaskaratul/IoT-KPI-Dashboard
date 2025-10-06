import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from psycopg2.extensions import encodings as _ext

@pytest.fixture
def mock_telemetry_data():
    return [
        {
            "device_id": "device1",
            "rss_value": -70,
            "timestamp": datetime.now().isoformat()
        },
        {
            "device_id": "device2",
            "rss_value": -80,
            "timestamp": datetime.now().isoformat()
        }
    ]

@pytest.fixture
def mock_sql_path():
    return str(Path(__file__).parent / "mocks" / "aggregate_status.sql")

@pytest.fixture
def mock_db_config():
    return {
        "dbname": "test_db",
        "user": "test_user",
        "password": "test_password",
        "host": "localhost",
        "port": 5432
    }

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("SAMASTH_API_KEY", "test_api_key")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_PASSWORD", "test_password")

@pytest.fixture
def mock_db_cursor():
    """Create a mock database cursor with all required attributes"""
    mock_conn = MagicMock()
    mock_conn.encoding = 'UTF8'  # Standard PostgreSQL encoding
    
    mock_cursor = MagicMock()
    mock_cursor.connection = mock_conn
    mock_cursor.description = None
    
    # Add methods commonly used in tests
    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = (0,)  # Default count result
    mock_cursor.rowcount = 0
    
    return mock_cursor