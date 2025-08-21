#!/usr/bin/env python3
"""
Combined UniProt + ChEMBL Knowledge Graph Example

This script demonstrates how to create a unified biological knowledge graph
combining protein data from UniProt and drug data from ChEMBL.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from biocypher import BioCypher
from template_package.adapters import (
    # UniProt imports
    UniprotAdapter,
    UniprotNodeType, 
    UniprotNodeField,
    # ChEMBL imports
    ChemblAdapter,
    ChemblNodeType,
    ChemblNodeField,
    ChemblEdgeType,
)

def main():
    print("🧬 Creating Combined UniProt + ChEMBL Knowledge Graph")
    print("=" * 60)
    
    # Initialize BioCypher
    bc = BioCypher()
    print("✅ BioCypher initialized")
    
    # === PART 1: UniProt Proteins ===
    print("\n🧬 STEP 1: Processing UniProt Proteins...")
    
    uniprot_adapter = UniprotAdapter(
        organism="9606",  # Human
        node_types=[UniprotNodeType.PROTEIN, UniprotNodeType.GENE],
        node_fields=[
            UniprotNodeField.PROTEIN_NAME,
            UniprotNodeField.GENE_NAMES, 
            UniprotNodeField.FUNCTION,
            UniprotNodeField.SEQUENCE,
            UniprotNodeField.LENGTH,
        ],
        edge_types=[
            # Skip edges to avoid empty generator issues
        ],
        test_mode=True,
    )
    
    # Download UniProt data
    uniprot_adapter.download_data(cache=True)
    print(f"✅ Downloaded {len(uniprot_adapter.uniprot_ids)} UniProt proteins")
    
    # Write UniProt nodes
    uniprot_nodes = list(uniprot_adapter.get_nodes())
    if uniprot_nodes:
        bc.write_nodes(uniprot_nodes)
        print(f"✅ Wrote {len(uniprot_nodes)} protein/gene nodes")
    
    # === PART 2: ChEMBL Drugs ===
    print("\n💊 STEP 2: Processing ChEMBL Drugs...")
    
    chembl_adapter = ChemblAdapter(
        node_types=[ChemblNodeType.DRUG],
        node_fields=[
            ChemblNodeField.MOLECULE_CHEMBL_ID,
            ChemblNodeField.PREF_NAME,
            ChemblNodeField.MAX_PHASE,
            ChemblNodeField.MOLECULAR_WEIGHT,
        ],
        edge_types=[
            ChemblEdgeType.COMPOUND_TARGETS_PROTEIN,
        ],
        max_phase=None,
        organism="Homo sapiens",
        test_mode=True,
    )
    
    # Download ChEMBL data (molecules only to avoid slow target processing)
    with chembl_adapter.timer("Downloading ChEMBL data"):
        chembl_adapter._download_molecules(30)  # 30 molecules for demo
    
    print(f"✅ Downloaded {len(chembl_adapter.molecules)} ChEMBL molecules")
    
    # Write ChEMBL nodes
    chembl_nodes = list(chembl_adapter.get_nodes())
    if chembl_nodes:
        bc.write_nodes(chembl_nodes)
        print(f"✅ Wrote {len(chembl_nodes)} drug nodes")
    
    # === PART 3: Generate Output Files ===
    print("\n📁 STEP 3: Generating Output Files...")
    
    # Write import script
    bc.write_import_call()
    print("✅ Generated Neo4j import script")
    
    # === PART 4: Summary ===
    print("\n🎉 SUCCESS: Combined Knowledge Graph Created!")
    print("=" * 60)
    
    total_proteins = len(uniprot_adapter.uniprot_ids) if hasattr(uniprot_adapter, 'uniprot_ids') else 0
    total_drugs = len(chembl_adapter.molecules) if hasattr(chembl_adapter, 'molecules') else 0
    total_nodes = len(uniprot_nodes) + len(chembl_nodes) if uniprot_nodes and chembl_nodes else 0
    
    print(f"📊 Knowledge Graph Contents:")
    print(f"   • UniProt Proteins: {total_proteins}")
    print(f"   • ChEMBL Drugs: {total_drugs}")
    print(f"   • Total Nodes: {total_nodes}")
    print(f"   • Output Directory: biocypher-out/")
    
    print(f"\n🚀 Ready for Neo4j Import:")
    print(f"   1. Check the generated files in biocypher-out/")
    print(f"   2. Use the neo4j-admin-import-call.sh script")
    print(f"   3. Or follow the Neo4j import instructions below")
    
    return True

def show_neo4j_import_instructions():
    """Show instructions for importing to Neo4j"""
    print("\n" + "="*60)
    print("📋 NEO4J IMPORT INSTRUCTIONS")
    print("="*60)
    
    print("\n🔧 Option 1: Docker Neo4j (Easiest)")
    print("```bash")
    print("# Start Neo4j with Docker")
    print("docker run \\")
    print("    --name neo4j \\")
    print("    -p 7474:7474 -p 7687:7687 \\")
    print("    -d \\")
    print("    -v $PWD/biocypher-out:/var/lib/neo4j/import \\")
    print("    --env NEO4J_AUTH=neo4j/password \\")
    print("    neo4j:latest")
    print("")
    print("# Access at: http://localhost:7474")
    print("# Login: neo4j / password")
    print("```")
    
    print("\n🔧 Option 2: neo4j-admin import (Local Neo4j)")
    print("```bash")
    print("# Stop Neo4j first")
    print("sudo systemctl stop neo4j")
    print("")
    print("# Run the generated import script")
    print("bash biocypher-out/*/neo4j-admin-import-call.sh")
    print("")
    print("# Start Neo4j")
    print("sudo systemctl start neo4j")
    print("```")
    
    print("\n🔧 Option 3: LOAD CSV (Any Neo4j)")
    print("```cypher") 
    print("// Load proteins")
    print("LOAD CSV WITH HEADERS FROM 'file:///Protein-part000.csv' AS row")
    print("CREATE (p:Protein {")
    print("  id: row.id,")
    print("  name: row.name")
    print("})")
    print("")
    print("// Load drugs")
    print("LOAD CSV WITH HEADERS FROM 'file:///Drug-part000.csv' AS row") 
    print("CREATE (d:Drug {")
    print("  id: row.id,")
    print("  name: row.name")
    print("})")
    print("```")
    
    print("\n🎯 Sample Queries After Import:")
    print("```cypher")
    print("// Count all nodes")
    print("MATCH (n) RETURN labels(n), count(n)")
    print("")
    print("// View proteins")
    print("MATCH (p:Protein) RETURN p LIMIT 10")
    print("") 
    print("// View drugs")
    print("MATCH (d:Drug) RETURN d LIMIT 10")
    print("")
    print("// Find relationships")
    print("MATCH (d:Drug)-[r]-(p:Protein) RETURN d, r, p LIMIT 5")
    print("```")

if __name__ == "__main__":
    success = main()
    if success:
        show_neo4j_import_instructions()