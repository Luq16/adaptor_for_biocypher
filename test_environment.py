#!/usr/bin/env python3
"""
Test script to verify the environment is set up correctly.
This script should be run with: poetry run python test_environment.py
"""

def test_biocypher_import():
    """Test if BioCypher can be imported."""
    try:
        from biocypher import BioCypher
        print("✅ BioCypher imported successfully")
        return True
    except ImportError as e:
        print(f"❌ BioCypher import failed: {e}")
        print("💡 Solution: Make sure you ran 'poetry install' and use 'poetry run python'")
        return False

def test_biocypher_creation():
    """Test if BioCypher instance can be created."""
    try:
        from biocypher import BioCypher
        bc = BioCypher()
        print("✅ BioCypher instance created successfully")
        return True
    except Exception as e:
        print(f"❌ BioCypher creation failed: {e}")
        return False

def test_simple_example():
    """Test if the simple example works."""
    try:
        import sys
        from pathlib import Path
        
        # Add project root to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Import directly to avoid __init__.py issues
        sys.path.append(str(Path(__file__).parent / "template_package" / "adapters"))
        from example_adapter import ExampleAdapter
        
        print("✅ Example adapter imported successfully")
        return True
    except Exception as e:
        print(f"❌ Example adapter import failed: {e}")
        return False

def main():
    print("🧪 Testing BioCypher Environment")
    print("=" * 40)
    
    all_passed = True
    all_passed &= test_biocypher_import()
    all_passed &= test_biocypher_creation() 
    all_passed &= test_simple_example()
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 Environment test PASSED!")
        print("\n✅ You can now run:")
        print("   poetry run python simple_example.py")
        print("   poetry run python examples/uniprot_example.py")
    else:
        print("❌ Environment test FAILED!")
        print("\n💡 Common solutions:")
        print("   1. Run: poetry install")
        print("   2. Always use: poetry run python <script>")
        print("   3. Never use: python3 <script> directly")
        print("   4. Check: poetry --version")

if __name__ == "__main__":
    main()