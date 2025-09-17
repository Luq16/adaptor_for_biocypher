#!/usr/bin/env python3
"""
Quick version - create relationships in optimized batches.
"""

import pandas as pd
from neo4j import GraphDatabase
import time

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

# Files
RELATIONSHIP_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-part000.csv"
HEADER_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-header.csv"

def quick_create():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("⚡ Quick protein and relationship creation...")
            
            # Read first 1000 relationships for testing
            header_df = pd.read_csv(HEADER_FILE, sep='\t')
            headers = list(header_df.columns)
            df = pd.read_csv(RELATIONSHIP_FILE, sep='\t', names=headers, nrows=1000)
            
            print(f"📊 Processing first {len(df)} relationships for testing")
            
            # Get unique proteins from this subset
            unique_proteins = df[':START_ID'].unique()
            print(f"🧬 Creating {len(unique_proteins)} proteins")
            
            # Create proteins in one batch query
            start_time = time.time()
            protein_queries = []
            for protein_id in unique_proteins:
                protein_queries.append(f"CREATE (:Protein {{id: '{protein_id}', source: 'uniprot'}})")
            
            # Execute all protein creations
            batch_query = "; ".join(protein_queries)
            try:
                session.run(batch_query)
                print(f"✅ Created {len(unique_proteins)} proteins in {time.time() - start_time:.2f}s")
            except Exception as e:
                print(f"Using individual creates due to: {str(e)[:50]}")
                # Fallback to individual creates
                for protein_id in unique_proteins:
                    try:
                        session.run("CREATE (:Protein {id: $id, source: 'uniprot'})", id=protein_id)
                    except:
                        pass  # Protein might already exist
            
            # Create relationships in optimized batches
            print(f"🔗 Creating relationships...")
            created_count = 0
            
            # Use UNWIND for batch relationship creation
            batch_size = 100
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                # Prepare batch data
                relationships = []
                for _, row in batch.iterrows():
                    relationships.append({
                        'protein_id': row[':START_ID'],
                        'go_id': row[':END_ID'],
                        'evidence': row.get('evidence_code', 'IEA'),
                        'aspect': row.get('aspect', '')
                    })
                
                # Use UNWIND for efficient batch processing
                batch_query = """
                UNWIND $relationships AS rel
                MATCH (p:Protein {id: rel.protein_id})
                MATCH (g:GoTerm {id: rel.go_id})
                CREATE (p)-[:ANNOTATED_WITH {
                    evidence_code: rel.evidence,
                    aspect: rel.aspect
                }]->(g)
                """
                
                try:
                    result = session.run(batch_query, relationships=relationships)
                    created_count += len(relationships)
                    print(f"  ✓ Batch {i//batch_size + 1}: {created_count}/{len(df)} relationships")
                except Exception as e:
                    print(f"  ❌ Batch failed: {str(e)[:50]}")
            
            print(f"\n✅ Quick creation complete!")
            print(f"   Created relationships: {created_count}")
            
            # Verify
            result = session.run("MATCH ()-[r:ANNOTATED_WITH]->() RETURN count(r) as count")
            total_rels = result.single()["count"]
            print(f"🔍 Total ANNOTATED_WITH relationships in DB: {total_rels}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    quick_create()