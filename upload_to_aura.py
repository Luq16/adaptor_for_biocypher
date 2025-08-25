#!/usr/bin/env python3
"""
Upload BioCypher data to Neo4j Aura (cloud instance).
"""

import os
import pandas as pd
from neo4j import GraphDatabase
import glob

# Neo4j Aura connection details
# The URI should look like: neo4j+s://xxxxxxxx.databases.neo4j.io
# You can find this in your Aura console under "Connection URI"
NEO4J_URI = "neo4j+s://YOUR-INSTANCE.databases.neo4j.io"  # ⚠️ UPDATE THIS with your Connection URI from Aura console
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = ""  # Your password looks correct


# Path to your BioCypher output
BIOCYPHER_OUTPUT = "biocypher-out/20250821002412"  # Update with your latest output directory

class Neo4jUploader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def upload_nodes(self, session, node_type, csv_file):
        """Upload nodes from CSV file."""
        print(f"Uploading {node_type} nodes from {csv_file}")
        
        # Read CSV to get column names
        df = pd.read_csv(csv_file, sep='\t', nrows=1)
        columns = df.columns.tolist()
        
        # Create Cypher query
        query = f"""
        LOAD CSV WITH HEADERS FROM 'file:///{csv_file}' AS row
        FIELDTERMINATOR '\t'
        CREATE (n:{node_type} {{
            id: row.`:ID`,
            source: row.source
        }})
        """
        
        # For local files, we need to use a different approach
        # Read the CSV and create nodes in batches
        df = pd.read_csv(csv_file, sep='\t')
        
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Create nodes in this batch
            for _, row in batch.iterrows():
                node_query = f"""
                CREATE (n:{node_type} {{
                    id: $id,
                    source: $source
                }})
                """
                session.run(node_query, id=row[':ID'], source=row.get('source', ''))
            
            print(f"  Uploaded {min(i+batch_size, len(df))}/{len(df)} {node_type} nodes")
    
    def upload_edges(self, session, edge_type, csv_file):
        """Upload edges from CSV file."""
        print(f"Uploading {edge_type} edges from {csv_file}")
        
        # Read the CSV
        df = pd.read_csv(csv_file, sep='\t')
        
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Create edges in this batch
            for _, row in batch.iterrows():
                edge_query = f"""
                MATCH (a {{id: $start_id}})
                MATCH (b {{id: $end_id}})
                CREATE (a)-[r:{edge_type}]->(b)
                """
                
                try:
                    session.run(edge_query, 
                              start_id=row[':START_ID'], 
                              end_id=row[':END_ID'])
                except Exception as e:
                    print(f"  Warning: Could not create edge {row[':START_ID']} -> {row[':END_ID']}: {e}")
            
            print(f"  Uploaded {min(i+batch_size, len(df))}/{len(df)} {edge_type} edges")
    
    def upload_all(self):
        """Upload all nodes and edges from BioCypher output."""
        with self.driver.session() as session:
            # First, clear the database (optional)
            print("Clearing existing data...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Upload nodes
            node_files = glob.glob(f"{BIOCYPHER_OUTPUT}/*-part*.csv")
            node_files = [f for f in node_files if not any(edge in f for edge in ['CompoundTargets', 'IsSubtypeOf', 'AssociatedWith'])]
            
            for node_file in node_files:
                # Extract node type from filename
                node_type = os.path.basename(node_file).split('-')[0]
                if os.path.getsize(node_file) > 0:  # Skip empty files
                    self.upload_nodes(session, node_type, node_file)
            
            # Upload edges
            edge_files = glob.glob(f"{BIOCYPHER_OUTPUT}/*-part*.csv")
            edge_files = [f for f in edge_files if any(edge in f for edge in ['CompoundTargets', 'IsSubtypeOf', 'AssociatedWith'])]
            
            for edge_file in edge_files:
                # Extract edge type from filename
                filename = os.path.basename(edge_file)
                if 'CompoundTargets' in filename:
                    edge_type = 'TARGETS'
                elif 'IsSubtypeOf' in filename:
                    edge_type = 'IS_SUBTYPE_OF'
                elif 'AssociatedWith' in filename:
                    edge_type = 'ASSOCIATED_WITH'
                else:
                    edge_type = 'RELATES_TO'
                
                if os.path.getsize(edge_file) > 0:  # Skip empty files
                    self.upload_edges(session, edge_type, edge_file)
            
            print("\n✅ Upload complete!")

def main():
    print("BioCypher to Neo4j Aura Uploader")
    print("=================================")
    
    # Check if credentials are set
    if NEO4J_URI == "neo4j+s://YOUR-INSTANCE.databases.neo4j.io":
        print("\n❌ ERROR: Please update the Neo4j Aura connection details in this script!")
        print("\n1. Sign up for Neo4j Aura Free at: https://neo4j.com/cloud/aura-free/")
        print("2. Create a free instance")
        print("3. Copy your connection URI and password")
        print("4. Update NEO4J_URI and NEO4J_PASSWORD in this script")
        return
    
    # Create uploader and upload data
    uploader = Neo4jUploader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        uploader.upload_all()
        
        print("\n📊 Example queries to try in Neo4j Browser:")
        print("MATCH (n) RETURN n LIMIT 25")
        print("MATCH (p:Protein) RETURN p LIMIT 10")
        print("MATCH (c:Compound) RETURN c LIMIT 10")
        print("MATCH (d:Disease) RETURN d LIMIT 10")
        
    finally:
        uploader.close()

if __name__ == "__main__":
    main()