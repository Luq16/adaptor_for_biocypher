#!/usr/bin/env python3
"""
Create relationships using actual node IDs that exist in the database.
"""

from neo4j import GraphDatabase

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def create_relationships():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔗 Creating relationships with actual node IDs...")
            
            # Get some real protein IDs
            result = session.run("MATCH (p) WHERE p.id CONTAINS 'uniprot:' RETURN p.id LIMIT 3")
            protein_ids = [record["p.id"] for record in result]
            
            # Get some real GO term IDs  
            result = session.run("MATCH (g) WHERE g.id CONTAINS 'go:' RETURN g.id LIMIT 3")
            go_ids = [record["g.id"] for record in result]
            
            print(f"Using proteins: {protein_ids}")
            print(f"Using GO terms: {go_ids}")
            
            # Create test relationships
            count = 0
            for protein_id in protein_ids[:2]:  # Use first 2 proteins
                for go_id in go_ids[:2]:       # Use first 2 GO terms
                    query = """
                    MATCH (p {id: $protein_id})
                    MATCH (g {id: $go_id})
                    CREATE (p)-[r:ANNOTATED_WITH {
                        evidence_code: 'IEA',
                        aspect: 'F'
                    }]->(g)
                    """
                    session.run(query, protein_id=protein_id, go_id=go_id)
                    count += 1
                    print(f"   ✓ Created: {protein_id} -[ANNOTATED_WITH]-> {go_id}")
            
            print(f"\n✅ Created {count} test relationships")
            
            # Verify relationships were created
            result = session.run("MATCH ()-[r:ANNOTATED_WITH]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            print(f"🔍 Total ANNOTATED_WITH relationships: {rel_count}")
            
            # Show sample relationship
            result = session.run("""
                MATCH (p)-[r:ANNOTATED_WITH]->(g) 
                RETURN p.id as protein, g.id as go_term, r.evidence_code as evidence
                LIMIT 1
            """)
            record = result.single()
            if record:
                print(f"📋 Sample: {record['protein']} -[{record['evidence']}]-> {record['go_term']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    create_relationships()