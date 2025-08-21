#!/usr/bin/env python3
"""
Example: Comprehensive biological knowledge graph creation.

This example demonstrates how to use multiple adapters together to create
a rich biological knowledge graph with functional annotations, pathways,
and disease associations.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biocypher import BioCypher
from template_package.adapters import (
    # Core adapters
    UniprotAdapter,
    UniprotNodeType,
    UniprotNodeField,
    # Functional annotations
    GOAdapter,
    GONodeType,
    GOEdgeType,
    # Pathways
    ReactomeAdapter,
    ReactomeNodeType,
    ReactomeEdgeType,
    # Disease associations
    DisGeNETAdapter,
    DisGeNETEdgeType,
)


def main():
    # Initialize BioCypher
    bc = BioCypher()
    
    print("🧬 Creating comprehensive biological knowledge graph...")
    print("This example combines multiple data sources for rich annotations.")
    
    # 1. UniProt - Core protein data
    print("\n1. Adding proteins from UniProt...")
    uniprot_adapter = UniprotAdapter(
        organism="9606",  # Human
        node_types=[UniprotNodeType.PROTEIN, UniprotNodeType.GENE],
        node_fields=[
            UniprotNodeField.PROTEIN_NAME,
            UniprotNodeField.GENE_NAMES,
            UniprotNodeField.FUNCTION,
            UniprotNodeField.LENGTH,
        ],
        test_mode=True,  # Small dataset for demo
    )
    
    uniprot_adapter.download_data()
    bc.write_nodes(uniprot_adapter.get_nodes())
    bc.write_edges(uniprot_adapter.get_edges())
    print("   ✓ Added proteins and genes")
    
    # 2. Gene Ontology - Functional annotations
    print("\n2. Adding functional annotations from Gene Ontology...")
    go_adapter = GOAdapter(
        organism="9606",  # Human
        node_types=[GONodeType.GO_TERM],
        edge_types=[
            GOEdgeType.PROTEIN_TO_GO_TERM,
            GOEdgeType.GO_TERM_IS_A_GO_TERM,
        ],
        go_aspects=['P', 'F'],  # Process and Function only for demo
        test_mode=True,
    )
    
    go_adapter.download_data()
    bc.write_nodes(go_adapter.get_nodes())
    bc.write_edges(go_adapter.get_edges())
    print("   ✓ Added GO terms and protein annotations")
    
    # 3. Reactome - Biological pathways
    print("\n3. Adding pathways from Reactome...")
    reactome_adapter = ReactomeAdapter(
        organism="9606",  # Human
        node_types=[ReactomeNodeType.PATHWAY],
        edge_types=[
            ReactomeEdgeType.PROTEIN_IN_PATHWAY,
            ReactomeEdgeType.PATHWAY_CHILD_OF_PATHWAY,
        ],
        test_mode=True,
    )
    
    reactome_adapter.download_data()
    bc.write_nodes(reactome_adapter.get_nodes())
    bc.write_edges(reactome_adapter.get_edges())
    print("   ✓ Added pathways and protein-pathway associations")
    
    # 4. DisGeNET - Gene-disease associations
    print("\n4. Adding gene-disease associations from DisGeNET...")
    disgenet_adapter = DisGeNETAdapter(
        edge_types=[DisGeNETEdgeType.GENE_DISEASE_ASSOCIATION],
        score_threshold=0.3,  # Medium confidence associations
        test_mode=True,
    )
    
    disgenet_adapter.download_data()
    bc.write_edges(disgenet_adapter.get_edges())
    print("   ✓ Added gene-disease associations")
    
    # 5. Finalize
    print("\n5. Finalizing knowledge graph...")
    bc.write_import_call()
    bc.summary()
    
    print("\n🎉 Comprehensive knowledge graph created!")
    print("\nThis graph now contains:")
    print("  • Proteins with functional information")
    print("  • GO terms for molecular functions and biological processes")
    print("  • Biological pathways and protein participation")
    print("  • Gene-disease associations with evidence scores")
    print("  • Hierarchical relationships between GO terms and pathways")
    
    print("\n🔍 Example queries you can now run:")
    print("  • Find proteins involved in specific biological processes:")
    print("    MATCH (p:protein)-[:protein_annotated_with_go_term]->(go:go_term)")
    print("    WHERE go.namespace = 'biological_process' AND go.name CONTAINS 'apoptosis'")
    print("    RETURN p.name, go.name")
    print("")
    print("  • Discover pathway co-participation:")
    print("    MATCH (p1:protein)-[:protein_participates_in_pathway]->(pw:pathway)")
    print("    <-[:protein_participates_in_pathway]-(p2:protein)")
    print("    WHERE p1 <> p2 RETURN p1.name, p2.name, pw.name LIMIT 10")
    print("")
    print("  • Find genes associated with diseases through functional similarity:")
    print("    MATCH (g1:gene)-[:gene_associated_with_disease]->(d:disease)")
    print("    <-[:gene_associated_with_disease]-(g2:gene)")
    print("    WHERE g1 <> g2 RETURN g1.symbol, g2.symbol, d.name LIMIT 10")


if __name__ == "__main__":
    main()