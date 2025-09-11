#!/usr/bin/env python3
"""
ChEMBL-only pipeline for drug and compound data.
Creates a knowledge graph with drugs, compounds, and their targets.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biocypher import BioCypher
from adapters import (
    ChemblAdapter,
    ChemblNodeType,
    ChemblNodeField,
    ChemblEdgeType,
)


def main():
    print("Running ChEMBL-only Knowledge Graph Pipeline")
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
    
    # Configure ChEMBL adapter
    print("\nConfiguring ChEMBL adapter...")
    chembl_adapter = ChemblAdapter(
        node_types=[
            ChemblNodeType.DRUG,      # Approved drugs
            ChemblNodeType.COMPOUND,  # Bioactive compounds
            ChemblNodeType.TARGET,    # Drug targets
        ],
        node_fields=[
            # Molecule fields
            ChemblNodeField.MOLECULE_CHEMBL_ID,
            ChemblNodeField.PREF_NAME,
            ChemblNodeField.MOLECULE_TYPE,
            ChemblNodeField.MAX_PHASE,
            ChemblNodeField.THERAPEUTIC_FLAG,
            ChemblNodeField.FIRST_APPROVAL,
            ChemblNodeField.MOLECULAR_WEIGHT,
            ChemblNodeField.ALOGP,
            ChemblNodeField.HBA,
            ChemblNodeField.HBD,
            ChemblNodeField.PSA,
            ChemblNodeField.RTB,
            ChemblNodeField.SMILES,
            ChemblNodeField.INCHI_KEY,
            # Target fields
            ChemblNodeField.TARGET_CHEMBL_ID,
            ChemblNodeField.TARGET_TYPE,
            ChemblNodeField.ORGANISM,
        ],
        edge_types=[
            ChemblEdgeType.DRUG_TARGETS,
            ChemblEdgeType.COMPOUND_TARGETS,
        ],
        test_mode=test_mode,
    )
    
    # Download data
    print("\nDownloading ChEMBL data...")
    chembl_adapter.download_data()
    
    # Process nodes
    print("\nProcessing ChEMBL nodes...")
    bc.write_nodes(chembl_adapter.get_nodes())
    
    # Process edges
    print("\nProcessing ChEMBL edges...")
    bc.write_edges(chembl_adapter.get_edges())
    
    # Finalize
    print("\nFinalizing knowledge graph...")
    bc.write_import_call()
    bc.summary()
    
    print("\n" + "="*50)
    print("ChEMBL Knowledge Graph completed!")
    print("Output location:", bc.get_output_directory())
    print("="*50)


if __name__ == "__main__":
    main()