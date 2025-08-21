#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all imports work."""
    try:
        from template_package.adapters import (
            UniprotAdapter, ChemblAdapter, DiseaseOntologyAdapter,
            StringAdapter, GOAdapter, ReactomeAdapter, DisGeNETAdapter
        )
        print("✅ All adapters imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_biocypher():
    """Test BioCypher import."""
    try:
        from biocypher import BioCypher
        print("✅ BioCypher imported successfully")
        return True
    except ImportError as e:
        print(f"❌ BioCypher import error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing imports...")
    success = True
    success &= test_biocypher()
    success &= test_imports()
    
    if success:
        print("\n🎉 Setup successful! You can now run the examples:")
        print("   python examples/uniprot_example.py")
        print("   python examples/comprehensive_example.py")
    else:
        print("\n❌ Setup incomplete. Check the errors above.")
