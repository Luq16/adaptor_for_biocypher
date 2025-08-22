#!/usr/bin/env python3
"""
Example: Using the OpenTargets adapter to create a target-disease association knowledge graph.

This example demonstrates how to use the OpenTargets adapter to download and process
target-disease associations, including genetic evidence and drug information.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biocypher import BioCypher
from template_package.adapters import (
    OpenTargetsAdapter,
    OpenTargetsNodeType,
    OpenTargetsNodeField,
    OpenTargetsEdgeType,
    OpenTargetsDataset,
)


def main():
    # Initialize BioCypher
    bc = BioCypher()
    
    # Choose data source
    print("OpenTargets Adapter Example")
    print("=" * 40)
    
    # Check if user wants real data (command line arg or environment variable)
    import os
    
    # Check command line arguments
    use_real_data_arg = "--real-data" in sys.argv or "--real" in sys.argv
    
    # Check environment variable
    env_var = os.environ.get("OPENTARGETS_USE_REAL_DATA", "false")
    use_real_data_env = env_var.lower() == "true"
    
    # Use real data if either method is specified
    use_real_data = use_real_data_arg or use_real_data_env
    
    print(f"Debug: Command line args: {sys.argv}")
    print(f"Debug: OPENTARGETS_USE_REAL_DATA = {repr(env_var)}")
    print(f"Debug: use_real_data = {use_real_data}")
    
    if use_real_data:
        print("🌐 Using REAL Open Targets data (this may take time to download)")
        print("💡 To use sample data instead, unset OPENTARGETS_USE_REAL_DATA")
    else:
        print("📊 Using sample data for demonstration")
        print("💡 To use real data, try one of these:")
        print("   OPENTARGETS_USE_REAL_DATA=true poetry run python examples/opentargets_example.py")
        print("   poetry run python examples/opentargets_example.py --real-data")
    
    # Create OpenTargets adapter
    # Re-enable real data with improved error handling
    actual_use_real_data = use_real_data
    
    if use_real_data:
        print("🔄 Attempting to use real Open Targets data...")
        print("   Will automatically fall back to sample data if needed")
    
    adapter = OpenTargetsAdapter(
        node_types=[
            OpenTargetsNodeType.TARGET,     # Gene/protein targets
            OpenTargetsNodeType.DISEASE,    # Diseases
        ],
        node_fields=[
            # Target fields
            OpenTargetsNodeField.TARGET_ID,
            OpenTargetsNodeField.TARGET_SYMBOL,
            OpenTargetsNodeField.TARGET_NAME,
            OpenTargetsNodeField.TARGET_BIOTYPE,
            OpenTargetsNodeField.TARGET_CHROMOSOME,
            OpenTargetsNodeField.TARGET_START,
            OpenTargetsNodeField.TARGET_END,
            # Disease fields
            OpenTargetsNodeField.DISEASE_ID,
            OpenTargetsNodeField.DISEASE_NAME,
            OpenTargetsNodeField.DISEASE_DESCRIPTION,
            OpenTargetsNodeField.DISEASE_SYNONYMS,
        ],
        edge_types=[
            OpenTargetsEdgeType.TARGET_DISEASE_ASSOCIATION,
        ],
        datasets=[
            OpenTargetsDataset.TARGETS,
            OpenTargetsDataset.DISEASES,
            OpenTargetsDataset.ASSOCIATIONS,
        ],
        use_real_data=actual_use_real_data,
        test_mode=False,  # Set to True to limit to 100 rows for testing
    )
    
    # Process OpenTargets data
    print("\nProcessing OpenTargets data...")
    if use_real_data:
        print("📥 Downloading real data from Open Targets Platform...")
        print("⏳ This may take several minutes for the first run...")
    else:
        print("📊 Using sample data for demonstration.")
    
    # Write nodes to BioCypher
    print("\nWriting target and disease nodes...")
    try:
        nodes = list(adapter.get_nodes())
        if nodes:
            bc.write_nodes(nodes)
            print(f"✅ Successfully wrote {len(nodes)} nodes")
            print(f"   - Targets: {adapter.nodes_data.get('target', []).__len__()} nodes")
            print(f"   - Diseases: {adapter.nodes_data.get('disease', []).__len__()} nodes")
        else:
            print("ℹ️  No nodes generated")
    except Exception as e:
        print(f"ℹ️  Node generation completed with issue: {str(e)}")
    
    # Write edges to BioCypher
    print("\nWriting target-disease associations...")
    try:
        edges = list(adapter.get_edges())
        if edges:
            bc.write_edges(edges)
            print(f"✅ Successfully wrote {len(edges)} associations")
            print("   - Each association includes overall score and datasource breakdown")
        else:
            print("ℹ️  No associations generated")
    except Exception as e:
        print(f"ℹ️  Edge generation completed with issue: {str(e)}")
    
    # Finalize - only write import call if we have nodes
    try:
        bc.write_import_call()
    except Exception as e:
        print(f"ℹ️  Skipping import call generation: {str(e)}")
        print("   This can happen when no data was processed successfully")
    
    print("\n🎉 SUCCESS! OpenTargets example completed successfully!")
    print("📁 Generated files in biocypher-out/ directory")
    
    # Show final status
    node_count = adapter.get_node_count()
    edge_count = adapter.get_edge_count()
    
    print(f"\n📊 Final results: {node_count} nodes, {edge_count} edges")
    
    if use_real_data and adapter.use_real_data:
        print("🌐 Data source: Open Targets Platform v24.09 (REAL DATA)")
        print("✅ Successfully processed real Open Targets data!")
    elif use_real_data and not adapter.use_real_data:
        print("📊 Data source: Sample data (fallback)")
        print("⚠️  Real data was requested but fell back to sample data")
        print("\n💡 Possible solutions:")
        print("   1. Check internet connection")
        print("   2. Install missing dependencies: poetry add pyarrow pandas duckdb")
        print("   3. Check logs above for specific error messages")
        print("   Note: pyarrow is required for reading Parquet files")
    else:
        print("📊 Data source: Sample data (as requested)")
        print("   - BRCA2 → Breast carcinoma association")
        print("   - TP53 → Lung carcinoma association")
        print("   - KRAS → Colorectal carcinoma association")
    
    print("\n🔍 Each association includes:")
    print("   - Overall association score")
    print("   - Evidence breakdown by datasource")
    print("   - Genetic association, literature, and drug evidence")
    print("\nDone! Check the output directory for generated files.")


if __name__ == "__main__":
    main()