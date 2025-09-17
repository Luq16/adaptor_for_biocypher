#!/usr/bin/env python3
"""
Create missing protein nodes that are referenced in relationships.
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

def create_missing_proteins():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            print("🧬 Creating missing protein nodes...")
            
            # Read the relationship data to find all protein IDs
            header_df = pd.read_csv(HEADER_FILE, sep='\t')
            headers = list(header_df.columns)
            df = pd.read_csv(RELATIONSHIP_FILE, sep='\t', names=headers)
            
            # Get unique protein IDs
            protein_ids = df[':START_ID'].unique()
            print(f"📊 Found {len(protein_ids)} unique protein IDs")
            
            # Sample a few for testing
            test_proteins = protein_ids[:5]  # Just test with first 5
            print(f"🧪 Creating test proteins: {test_proteins}")
            
            # Create protein nodes
            created_count = 0
            for protein_id in test_proteins:
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
                    created_count += 1
                    print(f"   ✓ Created protein: {protein_id}")
                else:
                    print(f"   - Already exists: {protein_id}")
            
            print(f"\n✅ Created {created_count} protein nodes")
            
            # Verify protein nodes exist
            result = session.run("MATCH (p:Protein) RETURN count(p) as count")
            protein_count = result.single()["count"]
            print(f"🔍 Total proteins in database: {protein_count}")
            
            # Now try to create some relationships
            print(f"\n🔗 Creating test relationships...")
            rel_count = 0
            for protein_id in test_proteins[:3]:  # Use first 3 proteins
                # Get some GO terms this protein should connect to
                protein_rels = df[df[':START_ID'] == protein_id].head(2)  # First 2 relationships for this protein
                
                for _, row in protein_rels.iterrows():
                    go_id = row[':END_ID']
                    
                    # Check if GO term exists (without quotes first, then with quotes)
                    result = session.run("MATCH (g {id: $id}) RETURN g", id=go_id)
                    if not result.single():
                        # Try with quotes
                        result = session.run("MATCH (g {id: $id}) RETURN g", id=f"'{go_id}'")
                        if result.single():
                            go_id = f"'{go_id}'"  # Use the quoted version
                        else:
                            print(f"   ❌ GO term not found: {go_id}")
                            continue
                    
                    # Create relationship
                    query = """
                    MATCH (p {id: $protein_id})
                    MATCH (g {id: $go_id})
                    CREATE (p)-[r:ANNOTATED_WITH {
                        evidence_code: $evidence,
                        aspect: $aspect
                    }]->(g)
                    """
                    session.run(query, 
                              protein_id=protein_id,
                              go_id=go_id,
                              evidence=row.get('evidence_code', 'IEA'),
                              aspect=row.get('aspect', ''))
                    rel_count += 1
                    print(f"   ✓ Created: {protein_id} -[ANNOTATED_WITH]-> {go_id}")
            
            print(f"\n✅ Created {rel_count} relationships")
            
            # Final verification
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            total_rels = result.single()["count"]
            print(f"🔍 Total relationships in database: {total_rels}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    create_missing_proteins()