#!/usr/bin/env python3
"""
Test runtime import checking for OpenTargets adapter.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_runtime_imports():
    """Test the runtime import checking functions."""
    
    # Import the helper functions directly
    try:
        from template_package.adapters.opentargets_adapter import _check_pandas_available, _check_duckdb_available
        
        print("Testing runtime import checking...")
        
        # Test pandas
        pandas_available, pandas_module = _check_pandas_available()
        print(f"Pandas available: {pandas_available}")
        if pandas_available:
            print(f"   Pandas version: {pandas_module.__version__}")
        
        # Test duckdb  
        duckdb_available, duckdb_module = _check_duckdb_available()
        print(f"DuckDB available: {duckdb_available}")
        if duckdb_available:
            print(f"   DuckDB version: {duckdb_module.__version__}")
        
        # Test parquet reading if pandas is available
        if pandas_available:
            parquet_file = ".cache/opentargets/targets.parquet"
            if os.path.exists(parquet_file):
                print(f"\nTesting parquet reading...")
                df = pandas_module.read_parquet(parquet_file)
                print(f"✅ Successfully read {len(df)} rows, {len(df.columns)} columns")
                print(f"   Sample columns: {list(df.columns)[:5]}")
                return True
            else:
                print("❌ Parquet file not found")
                return False
        else:
            print("❌ Cannot test parquet reading - pandas not available")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing OpenTargets runtime import checking...")
    print("=" * 50)
    
    success = test_runtime_imports()
    
    if success:
        print("\n🎉 Runtime import checking works!")
        print("The OpenTargets adapter should now work with real data.")
    else:
        print("\n❌ Runtime import checking failed.")
        
    sys.exit(0 if success else 1)