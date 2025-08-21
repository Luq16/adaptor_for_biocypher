#!/usr/bin/env python3
"""
Setup script for BioCypher Real Data Adapters.

This script helps set up the environment for running the adapters.
"""

import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")
        return True


def check_poetry():
    """Check if Poetry is installed."""
    try:
        result = subprocess.run(['poetry', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Poetry found: {result.stdout.strip()}")
            return True
        else:
            print("❌ Poetry not found")
            return False
    except FileNotFoundError:
        print("❌ Poetry not found")
        return False


def install_dependencies():
    """Install dependencies using Poetry."""
    print("📦 Installing dependencies...")
    try:
        result = subprocess.run(['poetry', 'install'], 
                              cwd=Path(__file__).parent)
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False


def install_poetry():
    """Provide instructions for installing Poetry."""
    print("\n📋 To install Poetry, run:")
    print("   curl -sSL https://install.python-poetry.org | python3 -")
    print("   # or")
    print("   pip install poetry")
    print("\nThen run this setup script again.")


def create_test_script():
    """Create a simple test script."""
    test_content = '''#!/usr/bin/env python3
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
        print("\\n🎉 Setup successful! You can now run the examples:")
        print("   python examples/uniprot_example.py")
        print("   python examples/comprehensive_example.py")
    else:
        print("\\n❌ Setup incomplete. Check the errors above.")
'''
    
    with open('test_setup.py', 'w') as f:
        f.write(test_content)
    
    print("✅ Created test_setup.py")


def main():
    """Main setup function."""
    print("🧬 BioCypher Real Data Adapters Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check Poetry
    if not check_poetry():
        install_poetry()
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n💡 Try running manually:")
        print("   poetry install")
        sys.exit(1)
    
    # Create test script
    create_test_script()
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("   1. Test the setup: python test_setup.py")
    print("   2. Try an example: python examples/uniprot_example.py")
    print("   3. Create full knowledge graph: python create_biological_knowledge_graph.py")
    print("\n💡 For test mode (recommended first run):")
    print("   export BIOCYPHER_TEST_MODE=true")
    print("   python create_biological_knowledge_graph.py")


if __name__ == "__main__":
    main()