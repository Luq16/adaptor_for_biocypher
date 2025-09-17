#!/usr/bin/env python3
"""
Demonstrate the fixed STRING adapter approach and create proper Neo4j upload.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pipeline'))

from biocypher import BioCypher
from adapters import StringAdapter, StringEdgeType

def test_fixed_string_adapter():
    print("=== Testing Fixed STRING Adapter ===\n")
    
    # Initialize BioCypher
    bc = BioCypher(
        biocypher_config_path="config/biocypher_config.yaml",
        schema_config_path="config/schema_config.yaml"
    )
    
    # Initialize STRING adapter in test mode
    string_adapter = StringAdapter(
        test_mode=True,
        edge_types=[StringEdgeType.PROTEIN_PROTEIN_INTERACTION]
    )
    
    print("1. Testing STRING adapter...")
    try:
        string_adapter.download_data()
        print(f"✅ Downloaded {len(string_adapter.interactions)} interactions")
        
        # Check what type of approach was used
        if hasattr(string_adapter, 'use_simple_mapping') and string_adapter.use_simple_mapping:
            print("   📝 Using simplified approach (fallback)")
        else:
            print("   📝 Using CROssBARv2 approach")
            print(f"   📊 STRING to UniProt mappings: {len(string_adapter.string_to_uniprot)}")
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    print("\n2. Testing edge generation...")
    try:
        edges = list(string_adapter.get_edges())
        print(f"✅ Generated {len(edges)} edges")
        
        if edges:
            # Show sample edges
            print("   Sample edges:")
            for i, (edge_id, source_id, target_id, edge_label, properties) in enumerate(edges[:3]):
                print(f"      {i+1}. {source_id} → {target_id}")
                
        return True
        
    except Exception as e:
        print(f"❌ Failed to generate edges: {e}")
        return False

def create_simple_demo():
    """Create a simple demonstration using UniProt proteins and STRING interactions."""
    print("\n3. Creating simple knowledge graph with STRING interactions...")
    
    try:
        # Initialize BioCypher
        bc = BioCypher(
            biocypher_config_path="config/biocypher_config.yaml",
            schema_config_path="config/schema_config.yaml"
        )
        
        # Create some sample UniProt proteins
        sample_proteins = [
            ("uniprot:P04637", "protein", {"name": "TP53", "source": "demo"}),
            ("uniprot:P38936", "protein", {"name": "CDKN1A", "source": "demo"}),
            ("uniprot:P24941", "protein", {"name": "CDK2", "source": "demo"}),
        ]
        
        # Create sample protein interactions using UniProt IDs
        sample_interactions = [
            (None, "uniprot:P04637", "uniprot:P38936", "protein_interacts_with_protein", 
             {"source": "string", "combined_score": 950}),
            (None, "uniprot:P38936", "uniprot:P24941", "protein_interacts_with_protein", 
             {"source": "string", "combined_score": 800}),
        ]
        
        # Add to BioCypher
        for protein in sample_proteins:
            bc.add_node(protein)
            
        for interaction in sample_interactions:
            bc.add_edge(interaction)
        
        # Write output
        bc.write()
        print("✅ Created demo knowledge graph with proper UniProt protein interactions")
        print("   📁 Output written to biocypher-out/")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create demo: {e}")
        return False

if __name__ == "__main__":
    success1 = test_fixed_string_adapter()
    success2 = create_simple_demo()
    
    if success1 and success2:
        print("\n✅ All tests passed!")
        print("\nNext steps:")
        print("1. Use the demo output to test Neo4j upload")
        print("2. Verify that relationships are properly created")
        print("3. If successful, run full pipeline with updated STRING adapter")
    else:
        print("\n❌ Some tests failed - check error messages above")