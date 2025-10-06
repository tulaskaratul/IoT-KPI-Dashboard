import unittest
from datetime import datetime, timedelta
import sys
import os
import psycopg2.extras
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dags.iot_kpi_dag import ingest_telemetry, aggregate_status, clean_old_logs

class TestIoTKPIDag(unittest.TestCase):
    """Test cases for IoT KPI DAG functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_telemetry = {
            'device_id': 'test-device-001',
            'rss_value': -70,
            'timestamp': datetime.utcnow().isoformat()
        }

    def mock_db_connect(self, cursor):
        """Helper to create a mock database connection"""
        mock_conn = MagicMock()
        mock_conn.encoding = 'UTF8'
        mock_conn.cursor.return_value = cursor
        return mock_conn



    def test_telemetry_ingestion(self):
        """Test telemetry data ingestion"""
        # Setup mock response for API
        mock_api_resp = MagicMock()
        mock_api_resp.status_code = 200
        mock_api_resp.json.return_value = {'data': [self.mock_telemetry]}

        # Create mock cursor and connection
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch('requests.get', return_value=mock_api_resp), \
             patch('psycopg2.connect', return_value=mock_conn):

            ingest_telemetry()

            # Verify API call
            mock_api_resp.json.assert_called_once()

            # Verify SQL execution and parameters
            mock_cursor.execute.assert_called_once()
            
            # Verify transaction was committed and cursor was closed
            mock_conn.commit.assert_called_once()
            mock_cursor.close.assert_called_once()

    def test_status_aggregation(self):
        """Test device status aggregation"""
        # Setup mock cursor and connection
        mock_cursor = MagicMock()
        mock_conn = self.mock_db_connect(mock_cursor)
        
        with patch('psycopg2.connect', return_value=mock_conn):
            # Test aggregation
            aggregate_status()
            
            # Verify SQL execution
            mock_cursor.execute.assert_called()
            mock_conn.commit.assert_called()

    @patch('psycopg2.connect')
    def test_log_cleanup(self, mock_connect):
        """Test old log cleanup"""
        # Setup mock cursor
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        # Mock cursor to return count of logs to be deleted
        mock_cursor.fetchone.return_value = (100,)
        
        # Test cleanup
        clean_old_logs()
        
        # Verify cleanup operations
        self.assertEqual(mock_cursor.execute.call_count, 2)  # Count query + delete query
        mock_connect.return_value.commit.assert_called()

    @patch('requests.get')
    def test_telemetry_error_handling(self, mock_get):
        """Test error handling in telemetry ingestion"""
        # Setup mock to simulate API error
        mock_get.return_value.status_code = 500
        
        # Mock database connection
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_connect.return_value.cursor.return_value = mock_cursor
            
            # Test ingestion with error
            ingest_telemetry()
            
            # Verify no database operations were performed
            mock_cursor.execute.assert_not_called()
            mock_connect.return_value.commit.assert_not_called()

    @patch('psycopg2.connect')
    def test_status_aggregation_empty(self, mock_connect):
        """Test status aggregation with no data"""
        # Setup mock cursor
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 0
        
        # Test aggregation
        aggregate_status()
        
        # Verify operation completed successfully
        mock_connect.return_value.commit.assert_called()

if __name__ == '__main__':
    unittest.main()