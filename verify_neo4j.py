#!/usr/bin/env python3
"""
Verify the Neo4j upload and debug missing relationships.
"""

from neo4j import GraphDatabase

# Neo4j connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def verify_database():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        print("=== Neo4j Database Verification ===\n")
        
        # 1. Count all nodes
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()["count"]
        print(f"Total nodes: {node_count}")
        
        # 2. Count nodes by label
        print("\nNodes by label:")
        result = session.run("""
            MATCH (n) 
            RETURN labels(n)[0] as label, count(n) as count 
            ORDER BY count DESC
        """)
        for record in result:
            print(f"  {record['label']}: {record['count']}")
        
        # 3. Count all relationships
        print("\nChecking relationships...")
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()["count"]
        print(f"Total relationships: {rel_count}")
        
        # 4. Count relationships by type
        if rel_count > 0:
            print("\nRelationships by type:")
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) as type, count(r) as count 
                ORDER BY count DESC
            """)
            for record in result:
                print(f"  {record['type']}: {record['count']}")
        
        # 5. Sample some protein nodes to check their IDs
        print("\nSample Protein nodes:")
        result = session.run("MATCH (p:Protein) RETURN p.id as id LIMIT 5")
        protein_ids = []
        for record in result:
            protein_ids.append(record['id'])
            print(f"  ID: {record['id']}")
        
        # 6. Check if these proteins have any relationships
        if protein_ids:
            print(f"\nChecking relationships for protein {protein_ids[0]}...")
            result = session.run("""
                MATCH (p:Protein {id: $id})-[r]-() 
                RETURN type(r) as type, count(r) as count
            """, id=protein_ids[0])
            rel_found = False
            for record in result:
                rel_found = True
                print(f"  {record['type']}: {record['count']}")
            if not rel_found:
                print("  No relationships found")
        
        # 7. Try different relationship queries
        print("\nTrying different relationship queries:")
        
        # Direct ProteinInteractsWithProtein query
        result = session.run("MATCH ()-[r:ProteinInteractsWithProtein]->() RETURN count(r) as count")
        print(f"  ProteinInteractsWithProtein relationships: {result.single()['count']}")
        
        # With underscores
        result = session.run("MATCH ()-[r:Protein_Interacts_With_Protein]->() RETURN count(r) as count")
        print(f"  Protein_Interacts_With_Protein relationships: {result.single()['count']}")
        
        # Any relationship between proteins
        result = session.run("MATCH (a:Protein)-[r]-(b:Protein) RETURN count(r) as count")
        print(f"  Any relationships between Protein nodes: {result.single()['count']}")
        
        # 8. Debug: Show all relationship types in the database
        print("\nAll relationship types in database:")
        result = session.run("CALL db.relationshipTypes()")
        for record in result:
            print(f"  {record['relationshipType']}")
        
        # 9. Sample edge check
        print("\nChecking specific edge from CSV...")
        # These IDs are from the CSV sample we saw
        start_id = "uniprot:ENSP00000001146"
        end_id = "uniprot:ENSP00000249750"
        
        result = session.run("""
            MATCH (a {id: $start_id})
            RETURN a, labels(a) as labels
        """, start_id=start_id)
        record = result.single()
        if record:
            print(f"  Start node found: {record['labels']}")
        else:
            print(f"  Start node NOT FOUND: {start_id}")
            
        result = session.run("""
            MATCH (b {id: $end_id})
            RETURN b, labels(b) as labels
        """, end_id=end_id)
        record = result.single()
        if record:
            print(f"  End node found: {record['labels']}")
        else:
            print(f"  End node NOT FOUND: {end_id}")
    
    driver.close()

if __name__ == "__main__":
    verify_database()