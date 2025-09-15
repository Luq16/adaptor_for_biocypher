#!/usr/bin/env python3
"""
Drug-Target-Disease pipeline combining ChEMBL, UniProt, and OpenTargets.
Creates a comprehensive view of drug-target-disease relationships.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biocypher import BioCypher
from adapters import (
    # ChEMBL for drugs
    ChemblAdapter,
    ChemblNodeType,
    ChemblNodeField,
    ChemblEdgeType,
    # UniProt for targets/proteins
    UniprotAdapter,
    UniprotNodeType,
    UniprotNodeField,
    # OpenTargets for target-disease associations
    OpenTargetsAdapter,
    OpenTargetsNodeType,
    OpenTargetsNodeField,
    OpenTargetsEdgeType,
)


def main():
    print("Running Drug-Target-Disease Pipeline")
    print("(ChEMBL + UniProt + OpenTargets)")
    print("=" * 50)
    
    # Initialize BioCypher
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
    bc = BioCypher(
        biocypher_config_path=os.path.join(config_dir, "biocypher_config.yaml"),
        schema_config_path=os.path.join(config_dir, "schema_config.yaml"),
    )
    
    # Check test mode
    test_mode = os.environ.get("BIOCYPHER_TEST_MODE", "false").lower() == "true"
    use_real_data = os.environ.get('OPENTARGETS_USE_REAL_DATA', 'false').lower() == 'true'\n    \n    print(f"Test mode: {test_mode}")
    print(f"OpenTargets real data: {use_real_data}")
    
    # Step 1: Process drugs and compounds from ChEMBL
    print("\n1. Processing ChEMBL drugs and compounds...")
    chembl_adapter = ChemblAdapter(
        node_types=[
            ChemblNodeType.DRUG,
            ChemblNodeType.COMPOUND,
            ChemblNodeType.TARGET,
        ],
        node_fields=[
            ChemblNodeField.MOLECULE_CHEMBL_ID,
            ChemblNodeField.PREF_NAME,
            ChemblNodeField.MOLECULE_TYPE,
            ChemblNodeField.MAX_PHASE,
            ChemblNodeField.THERAPEUTIC_FLAG,
            ChemblNodeField.TARGET_CHEMBL_ID,
            ChemblNodeField.TARGET_TYPE,
        ],
        edge_types=[
            ChemblEdgeType.COMPOUND_TARGETS_PROTEIN,
            ChemblEdgeType.DRUG_TREATS_DISEASE,
        ],
        test_mode=test_mode,
    )
    
    print("   Downloading ChEMBL data...")
    chembl_adapter.download_data()
    
    print("   Writing drug and compound nodes...")
    bc.write_nodes(chembl_adapter.get_nodes())
    
    print("   Writing drug-target edges...")
    bc.write_edges(chembl_adapter.get_edges())
    
    # Step 2: Add detailed protein/target information from UniProt
    print("\n2. Processing UniProt target proteins...")
    uniprot_adapter = UniprotAdapter(
        organism="9606",  # Human
        node_types=[
            UniprotNodeType.PROTEIN,
            UniprotNodeType.GENE,
        ],
        node_fields=[
            UniprotNodeField.PROTEIN_NAME,
            UniprotNodeField.GENE_NAMES,
            UniprotNodeField.ORGANISM_NAME,
            UniprotNodeField.FUNCTION,
            UniprotNodeField.SUBCELLULAR_LOCATION,
            # UniprotNodeField.PATHWAY,  # Field not available
        ],
        test_mode=test_mode,
    )
    
    print("   Downloading UniProt data...")
    uniprot_adapter.download_data()
    
    print("   Writing protein nodes...")
    bc.write_nodes(uniprot_adapter.get_nodes())
    
    # Step 3: Add target-disease associations from OpenTargets
    print("\n3. Processing OpenTargets associations...")
    opentargets_adapter = OpenTargetsAdapter(
        node_types=[
            OpenTargetsNodeType.TARGET,
            OpenTargetsNodeType.DISEASE,
        ],
        node_fields=[
            OpenTargetsNodeField.TARGET_ID,
            OpenTargetsNodeField.TARGET_SYMBOL,
            OpenTargetsNodeField.DISEASE_ID,
            OpenTargetsNodeField.DISEASE_NAME,
        ],
        edge_types=[OpenTargetsEdgeType.TARGET_DISEASE_ASSOCIATION],
        test_mode=test_mode,
        use_real_data=use_real_data,
    )
    
    print("   Downloading OpenTargets data...")
    opentargets_adapter.download_data()
    
    print("   Writing target and disease nodes...")
    bc.write_nodes(opentargets_adapter.get_nodes())
    
    print("   Writing target-disease associations...")
    bc.write_edges(opentargets_adapter.get_edges())
    
    # Finalize
    print("\n4. Finalizing knowledge graph...")
    bc.write_import_call()
    bc.summary()
    
    print("\n" + "="*50)
    print("Drug-Target-Disease Knowledge Graph completed!")
    print("Output location:", bc.get_output_directory())
    print("\nExample queries:")
    print("1. Find drugs targeting a specific disease:")
    print("   MATCH (drug)-[:targets]->(target)-[:associated_with]->(disease)")
    print("   WHERE disease.name CONTAINS 'cancer'")
    print("   RETURN drug.name, target.symbol, disease.name")
    print("\n2. Find targets with both drugs and disease associations:")
    print("   MATCH (drug)-[:targets]->(target)-[:associated_with]->(disease)")
    print("   RETURN target.symbol, COUNT(DISTINCT drug) as drugs, COUNT(DISTINCT disease) as diseases")
    print("   ORDER BY drugs DESC, diseases DESC")
    print("="*50)


if __name__ == "__main__":
    main()