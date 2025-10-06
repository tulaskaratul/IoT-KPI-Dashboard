#!/usr/bin/env python3
import unittest
import sys
import os

def run_tests():
    """Run all test cases"""
    # Add project root to path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)