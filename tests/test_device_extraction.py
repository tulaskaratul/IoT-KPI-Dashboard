import unittest
from datetime import datetime, timedelta
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dags.device_extract import extract_devices, save_devices_to_database, get_db_connection

class TestDeviceExtraction(unittest.TestCase):
    """Test cases for device extraction functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_device = {
            'id': {'id': 'test-device-001'},
            'name': 'Test Device 1',
            'type': 'sensor',
            'active': True,
            'createdTime': '2025-10-03T00:00:00.000Z'
        }
        self.mock_response = {
            'data': [self.sample_device],
            'totalElements': 1,
            'totalPages': 1,
            'hasNext': False
        }

    @patch('requests.get')
    def test_pagination_no_duplicates(self, mock_get):
        """Test that pagination doesn't fetch duplicate pages"""
        # Setup mock to return different devices for different pages
        def get_page_response(*args, **kwargs):
            page = int(kwargs['params']['page'])
            mock = MagicMock()
            mock.status_code = 200
            mock.json.return_value = {
                'data': [{'id': {'id': f'device-{page}'}, 'name': f'Device {page}'}],
                'totalElements': 3,
                'totalPages': 3,
                'hasNext': page < 2
            }
            return mock

        mock_get.side_effect = get_page_response
        
        result = extract_devices(batch_size=1)
        
        # Verify we got unique devices
        device_ids = [d['id']['id'] for d in result['data']]
        self.assertEqual(len(device_ids), len(set(device_ids)), "Found duplicate device IDs")
        self.assertEqual(len(device_ids), 3, "Should have fetched all 3 devices")

    @patch('requests.get')
    def test_since_parameter_stops_early(self, mock_get):
        """Test that extraction stops when reaching older devices"""
        current_time = datetime.utcnow()
        old_time = current_time - timedelta(hours=24)
        since_time = current_time - timedelta(hours=12)

        # Setup mock to return mixed devices on first page
        def get_page_response(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 200
            mock.json.return_value = {
                'data': [
                    # First device is new
                    {
                        'id': {'id': 'device-new'},
                        'name': 'New Device',
                        'createdTime': current_time.isoformat()
                    },
                    # Second device is old
                    {
                        'id': {'id': 'device-old'},
                        'name': 'Old Device',
                        'createdTime': old_time.isoformat()
                    }
                ],
                'totalElements': 2,
                'totalPages': 1,
                'hasNext': False
            }
            return mock

        mock_get.return_value = mock_get.side_effect = get_page_response
        
        result = extract_devices(batch_size=2, since=since_time.isoformat())
        
        # Should only have fetched devices newer than since_time
        self.assertEqual(len(result['data']), 1, "Should have only included newer device")
        self.assertEqual(result['data'][0]['id']['id'], 'device-new', "Should have the correct device")

    @patch('requests.get')
    def test_error_handling(self, mock_get):
        """Test handling of API errors"""
        # Mock API returning error
        mock_get.return_value.status_code = 500
        
        result = extract_devices()
        
        # Should return empty data on error
        self.assertEqual(result['data'], [], "Should return empty list on API error")
        self.assertEqual(result['totalElements'], 0)

    @patch('psycopg2.connect')
    def test_database_operations(self, mock_connect):
        """Test database operations"""
        # Setup mock cursor
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        # Test device data
        devices_data = {
            'data': [
                {
                    'id': {'id': 'test-device-001'},
                    'name': 'Test Device 1',
                    'type': 'sensor',
                    'active': True,
                    'createdTime': '2025-10-03T00:00:00.000Z'
                }
            ]
        }
        
        # Mock cursor.fetchone() to simulate device not existing
        mock_cursor.fetchone.return_value = None
        
        # Call function under test
        result = save_devices_to_database(devices_data)
        
        # Verify database operations
        self.assertEqual(result, 1, "Should have inserted 1 new device")
        mock_cursor.execute.assert_called()  # Verify database was called

if __name__ == '__main__':
    unittest.main()