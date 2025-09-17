#!/usr/bin/env python3
"""
Debug node IDs in Neo4j to understand the data format.
"""

from neo4j import GraphDatabase

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def debug_nodes():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔍 Debugging node IDs...")
            
            # Check some protein node IDs
            print("\n🧬 Sample Protein nodes:")
            result = session.run("MATCH (p) WHERE p.id CONTAINS 'uniprot:' RETURN p.id LIMIT 5")
            protein_ids = [record["p.id"] for record in result]
            for pid in protein_ids:
                print(f"   {pid}")
            
            # Check if the specific protein exists
            target_protein = "uniprot:A0A023I7F4"
            result = session.run("MATCH (p {id: $id}) RETURN p", id=target_protein)
            if result.single():
                print(f"   ✓ Found target protein: {target_protein}")
            else:
                print(f"   ❌ Target protein not found: {target_protein}")
                # Check if it exists with quotes
                target_protein_quoted = f"'{target_protein}'"
                result = session.run("MATCH (p {id: $id}) RETURN p", id=target_protein_quoted)
                if result.single():
                    print(f"   ✓ Found with quotes: {target_protein_quoted}")
            
            # Check some GO term node IDs
            print("\n🎯 Sample GO term nodes:")
            result = session.run("MATCH (g) WHERE g.id CONTAINS 'go:' RETURN g.id LIMIT 5")
            go_ids = [record["g.id"] for record in result]
            for gid in go_ids:
                print(f"   {gid}")
            
            # Check if the specific GO term exists
            target_go = "go:0016020"
            result = session.run("MATCH (g {id: $id}) RETURN g", id=target_go)
            if result.single():
                print(f"   ✓ Found target GO term: {target_go}")
            else:
                print(f"   ❌ Target GO term not found: {target_go}")
                # Check if it exists with quotes
                target_go_quoted = f"'{target_go}'"
                result = session.run("MATCH (g {id: $id}) RETURN g", id=target_go_quoted)
                if result.single():
                    print(f"   ✓ Found with quotes: {target_go_quoted}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    debug_nodes()