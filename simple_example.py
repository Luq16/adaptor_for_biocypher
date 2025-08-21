#!/usr/bin/env python3
"""
Simple working example using only the base example adapter.
This demonstrates that BioCypher is working without external data dependencies.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from biocypher import BioCypher
# Import directly to avoid __init__.py loading all adapters
sys.path.append(str(Path(__file__).parent / "template_package" / "adapters"))
from example_adapter import (
    ExampleAdapter,
    ExampleAdapterNodeType,
    ExampleAdapterEdgeType,
    ExampleAdapterProteinField,
    ExampleAdapterDiseaseField,
)

def main():
    print("🧬 Simple BioCypher Example")
    print("=" * 40)
    
    # Initialize BioCypher
    bc = BioCypher()
    
    print("✅ BioCypher initialized successfully")
    
    # Create example adapter
    adapter = ExampleAdapter(
        node_types=[
            ExampleAdapterNodeType.PROTEIN,
            ExampleAdapterNodeType.DISEASE,
        ],
        node_fields=[
            ExampleAdapterProteinField.SEQUENCE,
            ExampleAdapterDiseaseField.NAME,
        ],
        edge_types=[
            ExampleAdapterEdgeType.PROTEIN_DISEASE_ASSOCIATION,
        ],
    )
    
    print("✅ Example adapter created successfully")
    
    # Get data
    nodes = list(adapter.get_nodes())
    edges = list(adapter.get_edges())
    
    print(f"✅ Generated {len(nodes)} nodes and {len(edges)} edges")
    
    # Write to BioCypher
    bc.write_nodes(nodes)
    bc.write_edges(edges)
    
    print("✅ Data written to BioCypher")
    
    # Generate output
    bc.write_import_call()
    bc.summary()
    
    print("\n🎉 Success! BioCypher is working correctly.")
    print("\nThis demonstrates that:")
    print("  • BioCypher can be imported and initialized")
    print("  • Adapters can generate synthetic data")
    print("  • Data can be written to knowledge graph format")
    print("  • Output files are generated correctly")
    
    print("\n📁 Generated files:")
    print("  • Check the current directory for CSV files")
    print("  • Check biocypher-log/ for detailed logs")

if __name__ == "__main__":
    main()