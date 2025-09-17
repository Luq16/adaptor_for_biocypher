#!/usr/bin/env python3
"""
Create ALL missing protein nodes and their relationships from the CSV file.
This will give you the full 9,967 relationships.
"""

import pandas as pd
from neo4j import GraphDatabase

# Neo4j Aura connection details
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

# Files
RELATIONSHIP_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-part000.csv"
HEADER_FILE = "biocypher-out/20250916225223/ProteinAnnotatedWithGoTerm-header.csv"

def create_all_proteins_and_relationships():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🧬 Creating ALL missing proteins and relationships...")
            
            # Read the relationship data
            header_df = pd.read_csv(HEADER_FILE, sep='\t')
            headers = list(header_df.columns)
            df = pd.read_csv(RELATIONSHIP_FILE, sep='\t', names=headers)
            
            print(f"📊 Total relationships to process: {len(df)}")
            
            # Get unique protein IDs
            unique_proteins = df[':START_ID'].unique()
            print(f"🧬 Unique proteins to create: {len(unique_proteins)}")
            
            # Step 1: Create all missing protein nodes
            print(f"\n📦 Creating protein nodes...")
            created_proteins = 0
            batch_size = 100
            
            for i in range(0, len(unique_proteins), batch_size):
                batch_proteins = unique_proteins[i:i+batch_size]
                
                for protein_id in batch_proteins:
                    # Check if it already exists
                    result = session.run("MATCH (p {id: $id}) RETURN p", id=protein_id)
                    if not result.single():
                        # Create the protein node
                        query = """
                        CREATE (p:Protein {
                            id: $id,
                            source: 'uniprot'
                        })
                        """
                        session.run(query, id=protein_id)
                        created_proteins += 1
                
                print(f"  Created {min(i+batch_size, len(unique_proteins))}/{len(unique_proteins)} proteins")
            
            print(f"✅ Created {created_proteins} new protein nodes")
            
            # Step 2: Create ALL relationships
            print(f"\n🔗 Creating all {len(df)} relationships...")
            created_relationships = 0
            failed_relationships = 0
            batch_size = 500
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                for _, row in batch.iterrows():
                    protein_id = row[':START_ID']
                    go_id = row[':END_ID']
                    
                    # Create relationship
                    query = """
                    MATCH (p:Protein {id: $protein_id})
                    MATCH (g:GoTerm {id: $go_id})
                    CREATE (p)-[r:ANNOTATED_WITH {
                        evidence_code: $evidence,
                        aspect: $aspect,
                        qualifier: $qualifier
                    }]->(g)
                    """
                    
                    try:
                        session.run(query, 
                                  protein_id=protein_id,
                                  go_id=go_id,
                                  evidence=row.get('evidence_code', ''),
                                  aspect=row.get('aspect', ''),
                                  qualifier=row.get('qualifier', ''))
                        created_relationships += 1
                    except Exception as e:
                        failed_relationships += 1
                        if failed_relationships <= 5:  # Show first few errors
                            print(f"    ❌ Failed: {protein_id} -> {go_id}: {str(e)[:100]}")
                
                print(f"  Processed {min(i+batch_size, len(df))}/{len(df)} relationships")
            
            print(f"\n✅ Results:")
            print(f"   Created proteins: {created_proteins}")
            print(f"   Created relationships: {created_relationships}")
            print(f"   Failed relationships: {failed_relationships}")
            
            # Final verification
            result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(n) as count")
            for record in result:
                print(f"📊 {record['type']}: {record['count']} nodes")
            
            result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count")
            for record in result:
                print(f"🔗 {record['rel_type']}: {record['count']} relationships")
            
            if created_relationships > 0:
                # Sample relationship
                result = session.run("""
                    MATCH (p:Protein)-[r:ANNOTATED_WITH]->(g:GoTerm) 
                    RETURN p.id as protein, g.id as go_term, r.evidence_code as evidence
                    LIMIT 1
                """)
                record = result.single()
                if record:
                    print(f"📋 Sample: {record['protein']} -[{record['evidence']}]-> {record['go_term']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    create_all_proteins_and_relationships()