#!/usr/bin/env python3
"""
Basic setup test without external data dependencies.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_biocypher():
    """Test BioCypher import."""
    try:
        from biocypher import BioCypher
        print("✅ BioCypher imported successfully")
        return True
    except ImportError as e:
        print(f"❌ BioCypher import error: {e}")
        return False

def test_basic_imports():
    """Test basic imports without external dependencies."""
    try:
        from template_package.adapters.base_adapter import BaseAdapter
        print("✅ Base adapter imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Base adapter import error: {e}")
        return False

def test_biocypher_functionality():
    """Test basic BioCypher functionality."""
    try:
        from biocypher import BioCypher
        bc = BioCypher()
        print("✅ BioCypher instance created successfully")
        return True
    except Exception as e:
        print(f"❌ BioCypher functionality error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing basic setup...")
    success = True
    success &= test_biocypher()
    success &= test_basic_imports()
    success &= test_biocypher_functionality()
    
    if success:
        print("\n🎉 Basic setup successful!")
        print("BioCypher is working correctly.")
    else:
        print("\n❌ Setup incomplete. Check the errors above.")