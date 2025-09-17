#!/usr/bin/env python3
"""
Debug why relationships aren't being created.
"""

import pandas as pd
from neo4j import GraphDatabase

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

# Files
RELATIONSHIP_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-part000.csv"
HEADER_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-header.csv"

def debug_upload():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔍 Debugging relationship upload...")
            
            # Read the data exactly like the upload script does
            header_df = pd.read_csv(HEADER_FILE, sep='\t')
            headers = list(header_df.columns)
            df = pd.read_csv(RELATIONSHIP_FILE, sep='\t', names=headers)
            
            print(f"📋 Headers: {headers}")
            print(f"📊 Total rows: {len(df)}")
            
            # Show sample data
            print(f"\n🔍 Sample rows:")
            for i in range(min(3, len(df))):
                row = df.iloc[i]
                print(f"   Row {i}: START={row[':START_ID']}, END={row[':END_ID']}")
            
            # Test first few relationships
            print(f"\n🧪 Testing first 3 relationships...")
            for i in range(min(3, len(df))):
                row = df.iloc[i]
                start_id = row[':START_ID']
                end_id = row[':END_ID']
                
                print(f"\n--- Testing relationship {i+1} ---")
                print(f"Start ID: '{start_id}' (type: {type(start_id)})")
                print(f"End ID: '{end_id}' (type: {type(end_id)})")
                
                # Check if start node exists
                result = session.run("MATCH (n {id: $id}) RETURN n", id=start_id)
                start_exists = result.single() is not None
                print(f"Start node exists: {start_exists}")
                
                # Check if end node exists
                result = session.run("MATCH (n {id: $id}) RETURN n", id=end_id)
                end_exists = result.single() is not None
                print(f"End node exists: {end_exists}")
                
                if not start_exists:
                    # Try to find similar nodes
                    result = session.run("MATCH (n) WHERE n.id CONTAINS $partial RETURN n.id LIMIT 3", 
                                       partial=start_id.split(':')[0] if ':' in start_id else start_id)
                    similar = [r["n.id"] for r in result]
                    print(f"  Similar start nodes: {similar}")
                
                if not end_exists:
                    # Try to find similar nodes
                    result = session.run("MATCH (n) WHERE n.id CONTAINS $partial RETURN n.id LIMIT 3", 
                                       partial=end_id.split(':')[0] if ':' in end_id else end_id)
                    similar = [r["n.id"] for r in result]
                    print(f"  Similar end nodes: {similar}")
                
                # Try to create the relationship anyway to see the exact error
                if start_exists and end_exists:
                    try:
                        edge_query = """
                        MATCH (a {id: $start_id})
                        MATCH (b {id: $end_id})
                        CREATE (a)-[r:ANNOTATED_WITH]->(b)
                        """
                        session.run(edge_query, start_id=start_id, end_id=end_id)
                        print(f"✅ Successfully created relationship!")
                    except Exception as e:
                        print(f"❌ Failed to create relationship: {e}")
                else:
                    print(f"❌ Cannot create - missing nodes")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    debug_upload()