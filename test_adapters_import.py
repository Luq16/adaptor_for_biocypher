#!/usr/bin/env python3
"""
Test adapter imports with graceful error handling.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_adapters_import():
    """Test importing the adapters package."""
    try:
        print("Attempting to import adapters package...")
        import template_package.adapters as adapters
        print("✅ Adapters package imported successfully")
        
        # Show available adapters
        adapters.list_available_adapters()
        
        return True
    except Exception as e:
        print(f"❌ Error importing adapters: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing adapter imports...")
    test_adapters_import()