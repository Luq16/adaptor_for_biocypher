#!/usr/bin/env python3
"""
Debug edge creation more thoroughly
"""

from neo4j import GraphDatabase

# Neo4j connection
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def debug_thorough():
    """Debug edge creation thoroughly"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Check if specific nodes exist
        print("🔍 Checking specific nodes...")
        
        result = session.run("MATCH (d:Drug {id: 'drugbank:DB00316'}) RETURN d")
        drug_exists = result.single() is not None
        print(f"Drug drugbank:DB00316 exists: {drug_exists}")
        
        result = session.run("MATCH (s:SideEffect {id: 'meddra:10019211'}) RETURN s")
        se_exists = result.single() is not None
        print(f"SideEffect meddra:10019211 exists: {se_exists}")
        
        # Check what all relationship types exist
        print("\n🔗 All relationship types:")
        result = session.run("CALL db.relationshipTypes()")
        for record in result:
            print(f"  - {record[0]}")
        
        # Try step by step
        print("\n🧪 Testing edge creation step by step...")
        
        # First, find the drug node
        result = session.run("MATCH (d:Drug {id: 'drugbank:DB00316'}) RETURN d.id as id")
        drug_record = result.single()
        print(f"Found drug: {drug_record['id'] if drug_record else 'None'}")
        
        # Find the side effect node
        result = session.run("MATCH (s:SideEffect {id: 'meddra:10019211'}) RETURN s.id as id")
        se_record = result.single()
        print(f"Found side effect: {se_record['id'] if se_record else 'None'}")
        
        # Now try to create the relationship
        if drug_record and se_record:
            print("\n✨ Creating relationship...")
            result = session.run("""
            MATCH (d:Drug {id: 'drugbank:DB00316'})
            MATCH (s:SideEffect {id: 'meddra:10019211'})
            CREATE (d)-[r:TEST_DRUG_SIDE_EFFECT]->(s)
            RETURN r
            """)
            rel_record = result.single()
            print(f"Created relationship: {rel_record is not None}")
            
            # Verify it was created
            result = session.run("MATCH ()-[r:TEST_DRUG_SIDE_EFFECT]->() RETURN count(r) as count")
            count = result.single()["count"]
            print(f"TEST_DRUG_SIDE_EFFECT count: {count}")
        else:
            print("❌ Missing required nodes for relationship creation")
    
    driver.close()

if __name__ == "__main__":
    debug_thorough()