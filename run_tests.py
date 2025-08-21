#!/usr/bin/env python3
"""
Test runner for BioCypher adapters.

This script runs the test suite for all adapters to verify they work correctly.
"""

import sys
import unittest
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests():
    """Run all adapter tests."""
    
    # Discover and run tests
    loader = unittest.TestLoader()
    test_suite = loader.discover('tests', pattern='test_*.py')
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return success/failure
    return result.wasSuccessful()


def run_specific_test(test_name):
    """Run a specific test class or method."""
    
    loader = unittest.TestLoader()
    
    try:
        # Try to load the specific test
        test_suite = loader.loadTestsFromName(f'tests.{test_name}')
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(test_suite)
        return result.wasSuccessful()
    except Exception as e:
        print(f"Error loading test '{test_name}': {e}")
        return False


if __name__ == '__main__':
    print("BioCypher Adapters Test Suite")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        print(f"Running specific test: {test_name}")
        success = run_specific_test(test_name)
    else:
        # Run all tests
        print("Running all tests...")
        success = run_tests()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)