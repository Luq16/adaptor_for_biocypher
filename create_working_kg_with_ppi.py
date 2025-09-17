#!/usr/bin/env python3
"""
Create a working knowledge graph with UniProt proteins and PPI interactions,
then upload to Neo4j to demonstrate the solution.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pipeline'))

from biocypher import BioCypher
from adapters import UniprotAdapter, PPIAdapter
from neo4j import GraphDatabase
import subprocess

# Neo4j connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def create_knowledge_graph():
    """Create knowledge graph with UniProt proteins and PPI interactions."""
    print("=== Creating Knowledge Graph with UniProt + PPI ===\n")
    
    try:
        # Initialize BioCypher
        bc = BioCypher(
            biocypher_config_path="config/biocypher_config.yaml",
            schema_config_path="config/schema_config.yaml"
        )
        
        print("1. Initializing UniProt adapter...")
        uniprot_adapter = UniprotAdapter(test_mode=True)
        uniprot_adapter.download_data()
        
        # Add UniProt proteins
        protein_count = 0
        for node in uniprot_adapter.get_nodes():
            bc.add(node)
            protein_count += 1
        
        print(f"✅ Added {protein_count} UniProt proteins")
        
        print("\n2. Initializing PPI adapter...")
        ppi_adapter = PPIAdapter(test_mode=True, use_real_data=False)  # Use sample data for demo
        ppi_adapter.download_data()
        
        # Add PPI interactions
        edge_count = 0
        for edge in ppi_adapter.get_edges():
            bc.add(edge)
            edge_count += 1
        
        print(f"✅ Added {edge_count} protein-protein interactions")
        
        print("\n3. Writing BioCypher output...")
        bc.write()
        
        # Get the output directory
        output_dir = bc.output_dir
        print(f"✅ BioCypher output written to: {output_dir}")
        
        return output_dir
        
    except Exception as e:
        print(f"❌ Failed to create knowledge graph: {e}")
        import traceback
        traceback.print_exc()
        return None

def clear_and_upload_to_neo4j(output_dir):
    """Clear Neo4j and upload the new data."""
    print(f"\n=== Uploading to Neo4j from {output_dir} ===\n")
    
    try:
        # Clear database first
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            print("Clearing existing data...")
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Database cleared")
        driver.close()
        
        # Update the upload script with the new output directory
        upload_script = "upload_to_neo4j_aura.py"
        
        # Run the upload
        print(f"Uploading data from {output_dir}...")
        result = subprocess.run([
            "poetry", "run", "python", upload_script, output_dir
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Upload completed successfully!")
            return True
        else:
            print(f"❌ Upload failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to upload to Neo4j: {e}")
        return False

def verify_relationships():
    """Verify that relationships were created properly."""
    print("\n=== Verifying Relationships in Neo4j ===\n")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            print(f"Total nodes: {node_count}")
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            print(f"Total relationships: {rel_count}")
            
            # Show relationship types
            if rel_count > 0:
                result = session.run("""
                    MATCH ()-[r]->() 
                    RETURN type(r) as type, count(r) as count 
                    ORDER BY count DESC
                """)
                print("\nRelationship types:")
                for record in result:
                    print(f"  {record['type']}: {record['count']}")
                
                # Show sample relationships
                result = session.run("""
                    MATCH (p1:Protein)-[r:PROTEIN_INTERACTS_WITH_PROTEIN]->(p2:Protein)
                    RETURN p1.id, p2.id, r
                    LIMIT 3
                """)
                print("\nSample protein interactions:")
                for record in result:
                    print(f"  {record['p1.id']} → {record['p2.id']}")
                    
                return rel_count > 0
            else:
                print("❌ No relationships found")
                return False
                
        driver.close()
        
    except Exception as e:
        print(f"❌ Failed to verify relationships: {e}")
        return False

def main():
    print("🧬 BioCypher Knowledge Graph with Protein Interactions")
    print("=" * 60)
    
    # Step 1: Create knowledge graph
    output_dir = create_knowledge_graph()
    if not output_dir:
        print("\n❌ Failed to create knowledge graph")
        return
    
    # Step 2: Upload to Neo4j
    upload_success = clear_and_upload_to_neo4j(output_dir)
    if not upload_success:
        print("\n❌ Failed to upload to Neo4j")
        return
    
    # Step 3: Verify relationships
    verify_success = verify_relationships()
    
    if verify_success:
        print("\n🎉 SUCCESS! Protein interactions are now properly visible in Neo4j!")
        print(f"\n🌐 Open Neo4j Browser: {NEO4J_URI.replace('+s', '').replace('neo4j://', 'https://')}")
        print("\n📊 Try these queries:")
        print("  // Count all relationships")
        print("  MATCH ()-[r]->() RETURN type(r), count(r)")
        print("\n  // Show protein network")
        print("  MATCH (p1:Protein)-[r:PROTEIN_INTERACTS_WITH_PROTEIN]->(p2:Protein)")
        print("  RETURN p1, r, p2 LIMIT 25")
    else:
        print("\n❌ Relationships were not created properly")

if __name__ == "__main__":
    main()