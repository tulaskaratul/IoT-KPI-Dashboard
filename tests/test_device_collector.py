import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.collectors.device_collector import DeviceCollector

class TestDeviceCollector(unittest.TestCase):
    """Test cases for real-time device collector"""

    def setUp(self):
        """Set up test fixtures"""
        self.collector = DeviceCollector()
        self.sample_device = {
            'id': 'test-device-001',
            'name': 'Test Device 1',
            'device_type': 'sensor',
            'device_metadata': {'rss_value': -70},
            'last_seen': datetime.utcnow()
        }

    @patch('src.collectors.device_collector.DeviceCollector._simulate_device_data')
    async def test_device_data_collection(self, mock_simulate):
        """Test collection of device data"""
        # Setup mock to return simulated data
        mock_simulate.return_value = {
            'rss': -70,
            'status': 'active',
            'response_time': 100
        }

        # Mock database session
        self.collector.db_session = MagicMock()
        
        # Create mock device
        device = MagicMock()
        device.id = 'test-device-001'
        device.device_type = 'sensor'
        device.device_metadata = {'rss_value': -70}
        
        # Test collection
        await self.collector._collect_device_metrics(device)
        
        # Verify database operations
        self.collector.db_session.add.assert_called()
        self.collector.db_session.commit.assert_called()

    @patch('src.collectors.device_collector.DeviceCollector._collect_device_metrics')
    async def test_concurrent_collection(self, mock_collect):
        """Test concurrent collection of multiple devices"""
        # Setup mock devices
        devices = [MagicMock() for _ in range(5)]
        for i, device in enumerate(devices):
            device.id = f'test-device-{i}'
        
        # Mock database query
        self.collector.db_session = MagicMock()
        self.collector.db_session.query.return_value.filter.return_value.all.return_value = devices
        
        # Test concurrent collection
        await self.collector._collect_device_data()
        
        # Verify all devices were processed
        self.assertEqual(mock_collect.call_count, 5)

    @patch('src.collectors.device_collector.DeviceCollector._simulate_device_data')
    async def test_status_transitions(self, mock_simulate):
        """Test device status transitions"""
        # Mock database session
        self.collector.db_session = MagicMock()
        
        # Create mock device
        device = MagicMock()
        device.id = 'test-device-001'
        device.status = 'inactive'
        
        # Test transition to active
        mock_simulate.return_value = {'status': 'active'}
        await self.collector._update_device_status(device, True, datetime.utcnow())
        
        # Verify status change was recorded
        self.collector.db_session.add.assert_called()
        self.assertEqual(device.status, 'active')

    async def test_error_recovery(self):
        """Test error recovery during collection"""
        # Mock database session with error
        self.collector.db_session = MagicMock()
        self.collector.db_session.commit.side_effect = Exception("Database error")
        
        # Create mock device
        device = MagicMock()
        device.id = 'test-device-001'
        
        # Test collection with error
        try:
            await self.collector._collect_device_metrics(device)
        except Exception:
            pass
        
        # Verify rollback was called
        self.collector.db_session.rollback.assert_called()

def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper

if __name__ == '__main__':
    unittest.main()