#!/usr/bin/env python3
"""
Example: Using the STRING adapter to create protein interaction networks.

This example demonstrates how to use the STRING adapter to download and process
protein-protein interaction data.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biocypher import BioCypher
from template_package.adapters import (
    StringAdapter,
    StringEdgeType,
    StringEdgeField,
    # Also use UniProt for protein nodes
    UniprotAdapter,
    UniprotNodeType,
    UniprotNodeField,
)


def main():
    # Initialize BioCypher
    bc = BioCypher()
    
    # First, create protein nodes from UniProt (recommended)
    print("Creating protein nodes from UniProt...")
    uniprot_adapter = UniprotAdapter(
        organism="9606",  # Human
        node_types=[UniprotNodeType.PROTEIN],
        node_fields=[
            UniprotNodeField.PROTEIN_NAME,
            UniprotNodeField.GENE_NAMES,
            UniprotNodeField.LENGTH,
        ],
        test_mode=True,  # Limit to 100 proteins for testing
    )
    
    uniprot_adapter.download_data()
    bc.write_nodes(uniprot_adapter.get_nodes())
    
    # Now add protein interactions from STRING
    print("\nAdding protein interactions from STRING...")
    string_adapter = StringAdapter(
        organism="9606",  # Human
        edge_types=[
            StringEdgeType.PROTEIN_PROTEIN_INTERACTION,
            StringEdgeType.PHYSICAL_INTERACTION,
        ],
        edge_fields=[
            StringEdgeField.COMBINED_SCORE,
            StringEdgeField.PHYSICAL_SCORE,
            StringEdgeField.EXPERIMENTAL_SCORE,
            StringEdgeField.DATABASE_SCORE,
        ],
        score_threshold=0.7,  # High confidence interactions only
        test_mode=True,  # Limit data for testing
    )
    
    # Download interaction data
    string_adapter.download_data()
    
    # Write interaction edges
    bc.write_edges(string_adapter.get_edges())
    
    # Finalize
    bc.write_import_call()
    bc.summary()
    
    print("\nDone! You now have a protein interaction network.")
    print("\nExample queries:")
    print("- Find highly connected proteins: MATCH (p:protein)-[r:protein_protein_interaction]-(q:protein) RETURN p.name, COUNT(r) as connections ORDER BY connections DESC LIMIT 10")
    print("- Find physical interactions: MATCH (p1:protein)-[r:protein_physical_interaction]-(p2:protein) WHERE r.combined_score > 0.8 RETURN p1.name, p2.name, r.combined_score")


if __name__ == "__main__":
    main()