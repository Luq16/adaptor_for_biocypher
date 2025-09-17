#!/usr/bin/env python3
"""
Upload only the relationships to Neo4j Aura.
"""

import os
import pandas as pd
from neo4j import GraphDatabase

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

# Path to the relationship file
RELATIONSHIP_FILE = "biocypher-out/20250916222853/ProteinAnnotatedWithGoTerm-part000.csv"
HEADER_FILE = "biocypher-out/20250916222853/ProteinAnnotatedWithGoTerm-header.csv"

def upload_relationships():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔗 Uploading ProteinAnnotatedWithGoTerm relationships...")
            
            # Read header
            with open(HEADER_FILE, 'r') as f:
                headers = f.readline().strip().split('\t')
            print(f"📋 Headers: {headers}")
            
            # Read data with headers
            df = pd.read_csv(RELATIONSHIP_FILE, sep='\t', header=None, names=headers)
            print(f"📊 Found {len(df)} relationships to create")
            
            # Show sample data
            print(f"🔍 Sample relationship:")
            print(f"   {df.iloc[0][':START_ID']} -[ANNOTATED_WITH]-> {df.iloc[0][':END_ID']}")
            
            # Create relationships in batches
            batch_size = 1000
            created_count = 0
            failed_count = 0
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                for _, row in batch.iterrows():
                    edge_query = """
                    MATCH (a {id: $start_id})
                    MATCH (b {id: $end_id})
                    CREATE (a)-[r:ANNOTATED_WITH {
                        evidence_code: $evidence_code,
                        aspect: $aspect
                    }]->(b)
                    """
                    
                    try:
                        session.run(edge_query, 
                                  start_id=row[':START_ID'], 
                                  end_id=row[':END_ID'],
                                  evidence_code=row.get('evidence_code', ''),
                                  aspect=row.get('aspect', ''))
                        created_count += 1
                    except Exception as e:
                        failed_count += 1
                        if failed_count <= 5:  # Show first few errors
                            print(f"  ❌ Could not create edge {row[':START_ID']} -> {row[':END_ID']}: {e}")
                
                print(f"  ✓ Created {min(i+batch_size, len(df))}/{len(df)} relationships")
            
            print(f"\n✅ Upload complete!")
            print(f"   Created: {created_count} relationships")
            print(f"   Failed: {failed_count} relationships")
            
            # Test query
            result = session.run("MATCH ()-[r:ANNOTATED_WITH]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]
            print(f"🔍 Verification: {rel_count} ANNOTATED_WITH relationships in database")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    upload_relationships()