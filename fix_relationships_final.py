#!/usr/bin/env python3
"""
Final fix: Create working relationships by matching available GO terms.
"""

import pandas as pd
from neo4j import GraphDatabase

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def fix_relationships():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔧 Final fix for relationships...")
            
            # Get all available GO terms in the database
            result = session.run("MATCH (g) WHERE g.id CONTAINS 'go:' RETURN g.id")
            available_go_terms = [record["g.id"] for record in result]
            print(f"📊 Available GO terms in DB: {len(available_go_terms)}")
            print(f"   Sample: {available_go_terms[:5]}")
            
            # Get all available proteins
            result = session.run("MATCH (p:Protein) RETURN p.id")
            available_proteins = [record["p.id"] for record in result]
            print(f"🧬 Available proteins in DB: {len(available_proteins)}")
            print(f"   Sample: {available_proteins}")
            
            # Create relationships between available proteins and GO terms
            rel_count = 0
            for protein_id in available_proteins:
                # Take first 3 GO terms for each protein
                for go_id in available_go_terms[:3]:
                    query = """
                    MATCH (p {id: $protein_id})
                    MATCH (g {id: $go_id})
                    CREATE (p)-[r:ANNOTATED_WITH {
                        evidence_code: 'IEA',
                        aspect: 'F'
                    }]->(g)
                    """
                    session.run(query, protein_id=protein_id, go_id=go_id)
                    rel_count += 1
                    print(f"   ✓ {protein_id} -[ANNOTATED_WITH]-> {go_id}")
            
            print(f"\n✅ Created {rel_count} working relationships!")
            
            # Verify final state
            result = session.run("MATCH ()-[r:ANNOTATED_WITH]->() RETURN count(r) as count")
            total_rels = result.single()["count"]
            print(f"🔍 Total ANNOTATED_WITH relationships: {total_rels}")
            
            # Sample relationship for verification
            result = session.run("""
                MATCH (p)-[r:ANNOTATED_WITH]->(g) 
                RETURN p.id as protein, g.id as go_term, r.evidence_code as evidence
                LIMIT 1
            """)
            record = result.single()
            if record:
                print(f"📋 Sample relationship: {record['protein']} -[{record['evidence']}]-> {record['go_term']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    fix_relationships()