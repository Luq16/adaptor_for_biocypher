#!/usr/bin/env python3
"""
Verify that nodes and relationships were actually created in Neo4j Aura
"""

from neo4j import GraphDatabase

# Neo4j connection
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def verify_data():
    """Check what's actually in the database"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Count all nodes
        result = session.run("MATCH (n) RETURN count(n) as node_count")
        node_count = result.single()["node_count"]
        print(f"📊 Total nodes: {node_count}")
        
        # Count all relationships
        result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
        rel_count = result.single()["rel_count"]
        print(f"🔗 Total relationships: {rel_count}")
        
        # Show node type distribution
        result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count ORDER BY count DESC")
        print("\n📦 Node types:")
        for record in result:
            labels = record["labels"]
            count = record["count"]
            print(f"  {labels}: {count}")
        
        # Show relationship type distribution
        result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC")
        print("\n🔗 Relationship types:")
        for record in result:
            rel_type = record["rel_type"]
            count = record["count"]
            print(f"  {rel_type}: {count}")
        
        # Show sample relationships
        result = session.run("""
        MATCH (a)-[r]->(b) 
        RETURN labels(a) as start_labels, a.id as start_id, 
               type(r) as rel_type, 
               labels(b) as end_labels, b.id as end_id
        LIMIT 5
        """)
        print("\n🔍 Sample relationships:")
        for record in result:
            print(f"  ({record['start_labels'][0]}: {record['start_id']}) -[{record['rel_type']}]-> ({record['end_labels'][0]}: {record['end_id']})")
    
    driver.close()

if __name__ == "__main__":
    verify_data()