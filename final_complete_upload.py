#!/usr/bin/env python3
"""
Final complete upload: Ensure GO terms exist, then create working relationships.
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
RELATIONSHIP_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-part000.csv"
REL_HEADER_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-header.csv"

def complete_upload():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🔄 Complete upload: GO terms + proteins + relationships")
            
            # Step 1: Ensure GO terms exist
            print("\n📚 Checking GO terms...")
            result = session.run("MATCH (g:GoTerm) RETURN count(g) as count")
            go_count = result.single()["count"]
            
            if go_count == 0:
                print("   Re-uploading GO terms...")
                # Upload GO terms
                header_df = pd.read_csv(GO_HEADER_FILE, sep='\t')
                headers = list(header_df.columns)
                go_df = pd.read_csv(GO_TERMS_FILE, sep='\t', names=headers)
                
                for i, row in go_df.iterrows():
                    go_id = row[':ID']
                    namespace = row.get('namespace', '')
                    session.run("CREATE (:GoTerm {id: $id, namespace: $ns, source: 'go'})", 
                              id=go_id, ns=namespace)
                    if i % 100 == 0:
                        print(f"     Uploaded {i+1}/{len(go_df)} GO terms")
                
                print(f"   ✅ Uploaded {len(go_df)} GO terms")
            else:
                print(f"   ✅ {go_count} GO terms already exist")
            
            # Step 2: Check proteins
            result = session.run("MATCH (p:Protein) RETURN count(p) as count")
            protein_count = result.single()["count"]
            print(f"🧬 Found {protein_count} existing proteins")
            
            # Step 3: Create relationships with first 500 for testing
            print("\n🔗 Creating test relationships (first 500)...")
            
            # Read relationship data
            header_df = pd.read_csv(REL_HEADER_FILE, sep='\t')
            headers = list(header_df.columns)
            df = pd.read_csv(RELATIONSHIP_FILE, sep='\t', names=headers, nrows=500)
            
            print(f"📊 Processing {len(df)} relationships")
            
            created_count = 0
            failed_count = 0
            
            for i, row in df.iterrows():
                protein_id = row[':START_ID']
                go_id = row[':END_ID']
                
                # Check if both nodes exist
                protein_exists = session.run("MATCH (p:Protein {id: $id}) RETURN p", id=protein_id).single()
                go_exists = session.run("MATCH (g:GoTerm {id: $id}) RETURN g", id=go_id).single()
                
                if not protein_exists:
                    # Create missing protein
                    session.run("CREATE (:Protein {id: $id, source: 'uniprot'})", id=protein_id)
                
                if protein_exists and go_exists:
                    # Create relationship
                    try:
                        session.run("""
                            MATCH (p:Protein {id: $protein_id})
                            MATCH (g:GoTerm {id: $go_id})
                            CREATE (p)-[:ANNOTATED_WITH {
                                evidence_code: $evidence,
                                aspect: $aspect
                            }]->(g)
                        """, protein_id=protein_id, go_id=go_id,
                            evidence=row.get('evidence_code', 'IEA'),
                            aspect=row.get('aspect', ''))
                        created_count += 1
                    except Exception as e:
                        failed_count += 1
                        if failed_count <= 3:
                            print(f"     ❌ Failed: {protein_id} -> {go_id}")
                
                if (i + 1) % 50 == 0:
                    print(f"     Processed {i+1}/{len(df)} relationships")
            
            print(f"\n✅ Relationship creation complete!")
            print(f"   Created: {created_count}")
            print(f"   Failed: {failed_count}")
            
            # Final verification
            result = session.run("MATCH ()-[r:ANNOTATED_WITH]->() RETURN count(r) as count")
            total_rels = result.single()["count"]
            print(f"🔍 Total ANNOTATED_WITH relationships: {total_rels}")
            
            if total_rels > 0:
                result = session.run("""
                    MATCH (p:Protein)-[r:ANNOTATED_WITH]->(g:GoTerm) 
                    RETURN p.id as protein, g.id as go_term 
                    LIMIT 3
                """)
                print("📋 Sample relationships:")
                for record in result:
                    print(f"   {record['protein']} -> {record['go_term']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    complete_upload()