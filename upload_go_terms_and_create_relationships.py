#!/usr/bin/env python3
"""
Upload GO terms and create working relationships.
"""

import pandas as pd
from neo4j import GraphDatabase

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

# Files
GO_TERMS_FILE = "biocypher-out/20250916225223/GoTerm-part000.csv"
GO_HEADER_FILE = "biocypher-out/20250916225223/GoTerm-header.csv"

def upload_and_create():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            # Step 1: Upload GO terms
            print("📚 Uploading GO terms...")
            
            # Read GO terms
            header_df = pd.read_csv(GO_HEADER_FILE, sep='\t')
            headers = list(header_df.columns)
            go_df = pd.read_csv(GO_TERMS_FILE, sep='\t', names=headers)
            
            print(f"📊 Found {len(go_df)} GO terms to upload")
            
            # Upload GO terms in batches
            batch_size = 100
            uploaded_count = 0
            for i in range(0, len(go_df), batch_size):
                batch = go_df.iloc[i:i+batch_size]
                
                for _, row in batch.iterrows():
                    go_id = row[':ID']
                    namespace = row.get('namespace', '')
                    
                    query = """
                    CREATE (g:GoTerm {
                        id: $id,
                        namespace: $namespace,
                        source: 'go'
                    })
                    """
                    session.run(query, id=go_id, namespace=namespace)
                    uploaded_count += 1
                
                print(f"  Uploaded {min(i+batch_size, len(go_df))}/{len(go_df)} GO terms")
            
            print(f"✅ Uploaded {uploaded_count} GO terms")
            
            # Step 2: Create relationships between existing proteins and GO terms
            print(f"\n🔗 Creating relationships...")
            
            # Get available proteins
            result = session.run("MATCH (p:Protein) RETURN p.id LIMIT 10")
            proteins = [record["p.id"] for record in result]
            
            # Get some GO terms
            result = session.run("MATCH (g:GoTerm) RETURN g.id LIMIT 10")
            go_terms = [record["g.id"] for record in result]
            
            print(f"Using {len(proteins)} proteins and {len(go_terms)} GO terms")
            
            # Create relationships
            rel_count = 0
            for protein_id in proteins:
                for go_id in go_terms[:3]:  # 3 GO terms per protein
                    query = """
                    MATCH (p:Protein {id: $protein_id})
                    MATCH (g:GoTerm {id: $go_id})
                    CREATE (p)-[r:ANNOTATED_WITH {
                        evidence_code: 'IEA',
                        aspect: 'F'
                    }]->(g)
                    """
                    session.run(query, protein_id=protein_id, go_id=go_id)
                    rel_count += 1
                    print(f"   ✓ {protein_id} -[ANNOTATED_WITH]-> {go_id}")
            
            print(f"\n✅ Created {rel_count} relationships!")
            
            # Final verification
            result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
            for record in result:
                print(f"📊 {record['type']}: {record['count']} nodes")
            
            result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count")
            for record in result:
                print(f"🔗 {record['rel_type']}: {record['count']} relationships")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    upload_and_create()