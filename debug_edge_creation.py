#!/usr/bin/env python3
"""
Debug edge creation for DrugHasSideEffect
"""

import pandas as pd
from neo4j import GraphDatabase

# Neo4j connection
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def debug_edge_creation():
    """Debug DrugHasSideEffect edge creation"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Check what nodes exist
        print("🔍 Checking existing nodes...")
        
        result = session.run("MATCH (d:Drug) RETURN d.id LIMIT 5")
        drug_ids = [record["d.id"] for record in result]
        print(f"Drug nodes: {drug_ids}")
        
        result = session.run("MATCH (s:SideEffect) RETURN s.id LIMIT 5")
        side_effect_ids = [record["s.id"] for record in result]
        print(f"SideEffect nodes: {side_effect_ids}")
        
        # Read one DrugHasSideEffect edge
        header_file = "biocypher-out/20250912141939/DrugHasSideEffect-header.csv"
        edge_file = "biocypher-out/20250912141939/DrugHasSideEffect-part000.csv"
        
        header_df = pd.read_csv(header_file, sep='\t')
        headers = list(header_df.columns)
        df = pd.read_csv(edge_file, sep='\t', names=headers)
        
        # Get first row
        row = df.iloc[0]
        print(f"\n🔗 Testing first edge:")
        print(f"START_ID: {row[':START_ID']}")
        print(f"END_ID: {row[':END_ID']}")
        print(f"TYPE: {row[':TYPE']}")
        
        # Try to create the edge manually
        edge_query = f"""
        MATCH (a {{id: $start_id}})
        MATCH (b {{id: $end_id}})
        CREATE (a)-[r:DrugHasSideEffect]->(b)
        """
        
        try:
            result = session.run(edge_query, 
                               start_id=row[':START_ID'], 
                               end_id=row[':END_ID'])
            print("✅ Edge created successfully!")
            
            # Verify it exists
            verify_query = """
            MATCH (a)-[r:DrugHasSideEffect]->(b) 
            RETURN count(r) as count
            """
            result = session.run(verify_query)
            count = result.single()["count"]
            print(f"   DrugHasSideEffect relationships in DB: {count}")
            
        except Exception as e:
            print(f"❌ Edge creation failed: {e}")
    
    driver.close()

if __name__ == "__main__":
    debug_edge_creation()