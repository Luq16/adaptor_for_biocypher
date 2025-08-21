#!/usr/bin/env python3
"""
Demo script showing the BioCypher real data adapters in action.

This script demonstrates the capabilities of each adapter with small datasets
and shows how they work together to create a knowledge graph.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from template_package.adapters import (
    UniprotAdapter,
    UniprotNodeType,
    UniprotNodeField,
    ChemblAdapter,
    ChemblNodeType,
    StringAdapter,
    StringEdgeType,
    DiseaseOntologyAdapter,
    DiseaseNodeType,
)


def demo_uniprot():
    """Demonstrate UniProt adapter."""
    print("\n" + "="*50)
    print("🧬 UNIPROT ADAPTER DEMO")
    print("="*50)
    
    adapter = UniprotAdapter(
        organism="9606",  # Human
        node_types=[UniprotNodeType.PROTEIN],
        node_fields=[
            UniprotNodeField.PROTEIN_NAME,
            UniprotNodeField.LENGTH,
            UniprotNodeField.FUNCTION,
        ],
        test_mode=True,  # Just a few proteins
        add_prefix=True,
    )
    
    print("📥 Downloading sample UniProt data...")
    
    # Mock some data for demo (in real usage, this would download from UniProt)
    adapter.uniprot_ids = {'P04637', 'P53350'}  # TP53 and PLK1
    adapter.data = {
        'protein_name': {
            'P04637': 'Tumor protein p53',
            'P53350': 'Serine/threonine-protein kinase PLK1'
        },
        'length': {
            'P04637': 393,
            'P53350': 603
        },
        'organism_id': {
            'P04637': 9606,
            'P53350': 9606
        }
    }
    
    print("🔍 Generated proteins:")
    for i, (node_id, label, props) in enumerate(adapter.get_nodes()):
        if i >= 2:  # Show only first 2
            break
        print(f"  • {node_id} ({label}): {props.get('name', 'N/A')}")
    
    print(f"✅ UniProt adapter can provide {len(adapter.uniprot_ids)} proteins")


def demo_chembl():
    """Demonstrate ChEMBL adapter."""
    print("\n" + "="*50)
    print("💊 CHEMBL ADAPTER DEMO")
    print("="*50)
    
    adapter = ChemblAdapter(
        node_types=[ChemblNodeType.DRUG],
        test_mode=True,
    )
    
    print("📥 Simulating ChEMBL data download...")
    
    # Mock some drug data for demo
    adapter.molecules = [
        {
            'molecule_chembl_id': 'CHEMBL25',
            'pref_name': 'ASPIRIN',
            'max_phase': 4,
            'molecular_weight': 180.16,
        },
        {
            'molecule_chembl_id': 'CHEMBL1201585',
            'pref_name': 'IMATINIB',
            'max_phase': 4,
            'molecular_weight': 493.60,
        }
    ]
    
    print("🔍 Generated drugs:")
    for i, (node_id, label, props) in enumerate(adapter.get_nodes()):
        if i >= 2:  # Show only first 2
            break
        print(f"  • {node_id} ({label}): {props.get('pref_name', 'N/A')} (MW: {props.get('molecular_weight', 'N/A')})")
    
    print(f"✅ ChEMBL adapter can provide {len(adapter.molecules)} drugs")


def demo_disease_ontology():
    """Demonstrate Disease Ontology adapter."""
    print("\n" + "="*50)
    print("🦠 DISEASE ONTOLOGY ADAPTER DEMO")
    print("="*50)
    
    adapter = DiseaseOntologyAdapter(
        ontology="DO",
        node_types=[DiseaseNodeType.DISEASE],
        test_mode=True,
    )
    
    print("📥 Simulating Disease Ontology data...")
    
    # Mock some disease data for demo
    adapter.diseases = [
        {
            'id': 'DOID:162',
            'name': 'cancer',
            'definition': 'A disease of cellular proliferation...',
            'synonyms': ['malignant tumor', 'malignant neoplasm'],
        },
        {
            'id': 'DOID:1612',
            'name': 'breast cancer',
            'definition': 'A thoracic cancer that originates in the mammary gland.',
            'synonyms': ['mammary cancer'],
        }
    ]
    
    print("🔍 Generated diseases:")
    for i, (node_id, label, props) in enumerate(adapter.get_nodes()):
        if i >= 2:  # Show only first 2
            break
        synonyms = props.get('synonyms', [])
        synonym_text = f" (aka: {', '.join(synonyms[:2])})" if synonyms else ""
        print(f"  • {node_id} ({label}): {props.get('name', 'N/A')}{synonym_text}")
    
    print(f"✅ Disease Ontology adapter can provide {len(adapter.diseases)} diseases")


def demo_string():
    """Demonstrate STRING adapter."""
    print("\n" + "="*50)
    print("🔗 STRING ADAPTER DEMO")
    print("="*50)
    
    import pandas as pd
    
    adapter = StringAdapter(
        organism="9606",
        edge_types=[StringEdgeType.PROTEIN_PROTEIN_INTERACTION],
        test_mode=True,
    )
    
    print("📥 Simulating STRING interaction data...")
    
    # Mock some interaction data for demo
    adapter.interactions = pd.DataFrame({
        'protein1': ['9606.ENSP00000000233', '9606.ENSP00000000412'],
        'protein2': ['9606.ENSP00000000412', '9606.ENSP00000269305'],
        'combined_score': [850, 600],
        'experimental': [300, 200],
        'database': [400, 300],
        'textmining': [150, 100],
        'physical': [500, 400],
        'functional': [300, 200],
    })
    
    print("🔍 Generated interactions:")
    for i, (edge_id, source, target, label, props) in enumerate(adapter.get_edges()):
        if i >= 2:  # Show only first 2
            break
        score = props.get('combined_score', 0)
        print(f"  • {source} ↔ {target} (score: {score:.2f})")
    
    print(f"✅ STRING adapter can provide {len(adapter.interactions)} interactions")


def demo_integration():
    """Show how adapters work together."""
    print("\n" + "="*50)
    print("🔄 INTEGRATION DEMO")
    print("="*50)
    
    print("🎯 Knowledge Graph Components:")
    print("  • Proteins from UniProt (with sequences, functions)")
    print("  • Drugs from ChEMBL (with chemical properties)")  
    print("  • Diseases from Disease Ontology (with definitions)")
    print("  • Protein interactions from STRING (with confidence scores)")
    
    print("\n🔗 Possible Relationships:")
    print("  • Gene → Protein (from UniProt)")
    print("  • Protein → Organism (from UniProt)")
    print("  • Drug → Target (from ChEMBL)")
    print("  • Disease → Disease (from Disease Ontology hierarchies)")
    print("  • Protein ↔ Protein (from STRING)")
    
    print("\n📊 Example Queries:")
    print("  • Find all drugs targeting a specific protein")
    print("  • Discover protein interaction networks")
    print("  • Explore disease hierarchies and classifications")
    print("  • Map genes to their encoded proteins")
    
    print("\n🚀 To create the full knowledge graph:")
    print("     python create_biological_knowledge_graph.py")


def main():
    """Run all demos."""
    print("🧬 BioCypher Real Data Adapters Demo")
    print("Demonstrating real biological data integration")
    
    # Run individual adapter demos
    demo_uniprot()
    demo_chembl()
    demo_disease_ontology()
    demo_string()
    
    # Show integration capabilities
    demo_integration()
    
    print("\n" + "="*50)
    print("✨ DEMO COMPLETE")
    print("="*50)
    print("\nThis demo showed simplified examples of each adapter.")
    print("The real adapters download live data from:")
    print("  • UniProt/SwissProt for proteins")
    print("  • ChEMBL for drugs and compounds")
    print("  • Disease Ontology for disease classifications")
    print("  • STRING for protein interactions")
    print("\nNext steps:")
    print("  1. Run: python examples/uniprot_example.py")
    print("  2. Run: python create_biological_knowledge_graph.py")
    print("  3. Check the generated output files")
    print("  4. Import into Neo4j using docker-compose up -d")


if __name__ == "__main__":
    main()