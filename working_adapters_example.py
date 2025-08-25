#!/usr/bin/env python
"""
Example using only the working adapters with Python 3.12.
"""

from biocypher import BioCypher

# First check which adapters are available
from template_package.adapters import get_available_adapters

def main():
    """Run example with available adapters only."""
    
    print("BioCypher Working Adapters Example")
    print("=" * 50)
    
    # Check available adapters
    available = get_available_adapters()
    print("Checking adapter availability:")
    for name, status in available.items():
        status_emoji = "✅" if status else "❌"
        print(f"  {status_emoji} {name}")
    
    print()
    
    # Configure BioCypher
    print("Initializing BioCypher...")
    bcy = BioCypher(
        schema_config_path="config/schema_config.yaml",
        biocypher_config_path="config/biocypher_config.yaml",
    )
    
    total_nodes = 0
    total_edges = 0
    
    # Use OpenTargets if available
    if available.get('opentargets', False):
        print("\n1. Loading OpenTargets data...")
        from template_package.adapters import (
            OpenTargetsAdapter,
            OpenTargetsNodeType,
            OpenTargetsEdgeType,
        )
        
        adapter = OpenTargetsAdapter(
            node_types=[
                OpenTargetsNodeType.TARGET,
                OpenTargetsNodeType.DISEASE,
            ],
            edge_types=[
                OpenTargetsEdgeType.TARGET_DISEASE_ASSOCIATION,
            ],
            test_mode=True,
        )
        
        # Write nodes and edges
        bcy.write_nodes(adapter.get_nodes())
        bcy.write_edges(adapter.get_edges())
        
        node_count = adapter.get_node_count()
        edge_count = adapter.get_edge_count()
        total_nodes += node_count
        total_edges += edge_count
        
        print(f"   ✅ Loaded {node_count} nodes and {edge_count} edges from OpenTargets")
    
    # Use ChEMBL if available
    if available.get('chembl', False):
        print("\n2. Loading ChEMBL data...")
        try:
            from template_package.adapters import (
                ChemblAdapter,
                ChemblNodeType,
                ChemblEdgeType,
            )
            
            chembl_adapter = ChemblAdapter(
                organism="Homo sapiens",
                node_types=[ChemblNodeType.COMPOUND],
                edge_types=[ChemblEdgeType.COMPOUND_TARGETS_PROTEIN],
                test_mode=True,
            )
            
            bcy.write_nodes(chembl_adapter.get_nodes())
            bcy.write_edges(chembl_adapter.get_edges())
            
            node_count = chembl_adapter.get_node_count()
            edge_count = chembl_adapter.get_edge_count()
            total_nodes += node_count
            total_edges += edge_count
            
            print(f"   ✅ Loaded {node_count} nodes and {edge_count} edges from ChEMBL")
        except Exception as e:
            print(f"   ❌ ChEMBL adapter failed: {e}")
    
    # Use UniProt if available
    if available.get('uniprot', False):
        print("\n3. Loading UniProt data...")
        try:
            from template_package.adapters import (
                UniprotAdapter,
                UniprotNodeType,
            )
            
            uniprot_adapter = UniprotAdapter(
                organism="9606",  # Human
                reviewed=True,
                node_types=[UniprotNodeType.PROTEIN],
                test_mode=True,
            )
            
            bcy.write_nodes(uniprot_adapter.get_nodes())
            
            node_count = len(list(uniprot_adapter.get_nodes()))
            total_nodes += node_count
            
            print(f"   ✅ Loaded {node_count} nodes from UniProt")
        except Exception as e:
            print(f"   ❌ UniProt adapter failed: {e}")
    
    # Generate import script
    print("\n4. Generating Neo4j import script...")
    bcy.write_import_call()
    print("   ✅ Import script created")
    
    # Summary
    print(f"\nFinal Summary:")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Total edges: {total_edges}")
    print("\nData has been written to the 'biocypher-out' directory.")
    print("Use the generated import script to load data into Neo4j.")


if __name__ == "__main__":
    main()