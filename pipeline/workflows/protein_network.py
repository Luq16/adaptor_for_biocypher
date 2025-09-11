#!/usr/bin/env python3
"""
Protein network pipeline combining UniProt and STRING data.
Creates a comprehensive protein-protein interaction network.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biocypher import BioCypher
from adapters import (
    # UniProt for protein nodes
    UniprotAdapter,
    UniprotNodeType,
    UniprotNodeField,
    # STRING for interactions
    StringAdapter,
    StringEdgeType,
    StringEdgeField,
)


def main():
    print("Running Protein Network Pipeline (UniProt + STRING)")
    print("=" * 50)
    
    # Initialize BioCypher
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
    bc = BioCypher(
        biocypher_config_path=os.path.join(config_dir, "biocypher_config.yaml"),
        schema_config_path=os.path.join(config_dir, "schema_config.yaml"),
    )
    
    # Check test mode
    test_mode = os.environ.get("BIOCYPHER_TEST_MODE", "false").lower() == "true"
    print(f"Test mode: {test_mode}")
    
    # Step 1: Create protein nodes from UniProt
    print("\n1. Processing UniProt proteins...")
    uniprot_adapter = UniprotAdapter(
        organism="9606",  # Human
        node_types=[
            UniprotNodeType.PROTEIN,
            UniprotNodeType.GENE,
        ],
        node_fields=[
            UniprotNodeField.PROTEIN_NAME,
            UniprotNodeField.GENE_NAMES,
            UniprotNodeField.ORGANISM,
            UniprotNodeField.LENGTH,
            UniprotNodeField.FUNCTION,
            UniprotNodeField.SUBCELLULAR_LOCATION,
            UniprotNodeField.GO_TERMS,
        ],
        test_mode=test_mode,
    )
    
    print("   Downloading UniProt data...")
    uniprot_adapter.download_data()
    
    print("   Writing protein and gene nodes...")
    bc.write_nodes(uniprot_adapter.get_nodes())
    
    # Step 2: Add protein interactions from STRING
    print("\n2. Processing STRING interactions...")
    string_adapter = StringAdapter(
        organism="9606",  # Human
        edge_types=[
            StringEdgeType.PROTEIN_PROTEIN_INTERACTION,
        ],
        edge_fields=[
            StringEdgeField.COMBINED_SCORE,
            StringEdgeField.EXPERIMENTAL_SCORE,
            StringEdgeField.DATABASE_SCORE,
            StringEdgeField.TEXTMINING_SCORE,
            StringEdgeField.COEXPRESSION_SCORE,
        ],
        score_threshold=0.7,  # High confidence interactions
        test_mode=test_mode,
    )
    
    print("   Downloading STRING data...")
    string_adapter.download_data()
    
    print("   Writing protein interactions...")
    bc.write_edges(string_adapter.get_edges())
    
    # Finalize
    print("\n3. Finalizing knowledge graph...")
    bc.write_import_call()
    bc.summary()
    
    print("\n" + "="*50)
    print("Protein Network Knowledge Graph completed!")
    print("Output location:", bc.get_output_directory())
    print("\nExample queries:")
    print("1. Find hub proteins:")
    print("   MATCH (p:protein)-[r:protein_protein_interaction]-()")
    print("   RETURN p.name, COUNT(r) as degree")
    print("   ORDER BY degree DESC LIMIT 10")
    print("\n2. Find proteins interacting with a specific protein:")
    print("   MATCH (p1:protein {name: 'TP53'})-[r:protein_protein_interaction]-(p2:protein)")
    print("   WHERE r.combined_score > 0.8")
    print("   RETURN p2.name, r.combined_score")
    print("="*50)


if __name__ == "__main__":
    main()