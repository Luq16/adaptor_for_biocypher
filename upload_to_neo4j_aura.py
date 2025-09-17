#!/usr/bin/env python3
"""
Upload BioCypher data to Neo4j Aura (cloud instance).

Before running this script:
1. Sign up for Neo4j Aura Free at: https://neo4j.com/cloud/aura-free/
2. Create a new instance (takes ~5 minutes)
3. Save your credentials:
   - Connection URI (looks like: neo4j+s://xxxxxxxx.databases.neo4j.io)
   - Password (auto-generated, save it immediately!)
4. Update the credentials below
"""

import os
import sys
import pandas as pd
from neo4j import GraphDatabase
import glob
from datetime import datetime

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES WITH YOUR NEO4J AURA CREDENTIALS
# ============================================================================

# Neo4j Aura connection details


# Path to your BioCypher output (will auto-detect latest if not specified)
BIOCYPHER_OUTPUT = None  # Set to None to auto-detect latest, or specify like "biocypher-out/20250915184645"

# ============================================================================

class Neo4jUploader:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✅ Successfully connected to Neo4j Aura!")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure your Aura instance is running")
            print("2. Check that the URI is correct (should start with neo4j+s://)")
            print("3. Verify your password is correct")
            print("4. Ensure you're connected to the internet")
            raise
    
    def close(self):
        self.driver.close()
    
    def upload_nodes(self, session, node_type, csv_file):
        """Upload nodes from CSV file."""
        print(f"Uploading {node_type} nodes from {os.path.basename(csv_file)}")
        
        # Get the header file
        header_file = csv_file.replace('-part000.csv', '-header.csv')
        
        # Read the CSV with proper headers
        try:
            if os.path.exists(header_file):
                # Read headers from header file
                header_df = pd.read_csv(header_file, sep='\t')
                headers = list(header_df.columns)
                # Read data with these headers
                df = pd.read_csv(csv_file, sep='\t', names=headers)
            else:
                # Fallback to reading normally
                df = pd.read_csv(csv_file, sep='\t')
        except Exception as e:
            print(f"  Warning: Could not read {csv_file}: {e}")
            return
        
        if len(df) == 0:
            print(f"  Skipping empty file")
            return
        
        # Get columns (exclude BioCypher metadata columns)
        columns = [col for col in df.columns if not col.startswith(':')]
        
        batch_size = 500
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Create nodes in this batch
            for _, row in batch.iterrows():
                # Build properties dynamically
                props = {}
                
                # Add ID
                if ':ID' in row:
                    props['id'] = row[':ID']
                
                # Add other properties
                for col in columns:
                    if col in row and pd.notna(row[col]):
                        # Convert lists/arrays to strings for Neo4j
                        val = row[col]
                        if isinstance(val, (list, pd.Series)):
                            val = str(val)
                        props[col.replace(':', '_').replace(' ', '_')] = val
                
                # Create node
                node_query = f"CREATE (n:{node_type.replace('-', '_')} $props)"
                
                try:
                    session.run(node_query, props=props)
                except Exception as e:
                    print(f"  Warning: Could not create node: {e}")
            
            print(f"  Uploaded {min(i+batch_size, len(df))}/{len(df)} {node_type} nodes")
    
    def upload_edges(self, session, edge_type, csv_file):
        """Upload edges from CSV file."""
        print(f"Uploading {edge_type} edges from {os.path.basename(csv_file)}")
        
        # Get the header file
        header_file = csv_file.replace('-part000.csv', '-header.csv')
        
        # Read the CSV with proper headers
        try:
            if os.path.exists(header_file):
                # Read headers from header file
                header_df = pd.read_csv(header_file, sep='\t')
                headers = list(header_df.columns)
                # Read data with these headers
                df = pd.read_csv(csv_file, sep='\t', names=headers)
            else:
                # Fallback to reading normally
                df = pd.read_csv(csv_file, sep='\t')
        except Exception as e:
            print(f"  Warning: Could not read {csv_file}: {e}")
            return
        
        if len(df) == 0:
            print(f"  Skipping empty file")
            return
        
        # Get property columns (exclude BioCypher metadata columns)
        prop_columns = [col for col in df.columns if col not in [':START_ID', ':END_ID', ':TYPE']]
        
        batch_size = 500
        success_count = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Create edges in this batch
            for _, row in batch.iterrows():
                # Build properties
                props = {}
                for col in prop_columns:
                    if col in row and pd.notna(row[col]):
                        val = row[col]
                        if isinstance(val, (list, pd.Series)):
                            val = str(val)
                        props[col.replace(':', '_').replace(' ', '_')] = val
                
                edge_query = f"""
                MATCH (a {{id: $start_id}})
                MATCH (b {{id: $end_id}})
                CREATE (a)-[r:{edge_type.replace('-', '_')} $props]->(b)
                """
                
                try:
                    session.run(edge_query, 
                              start_id=row[':START_ID'], 
                              end_id=row[':END_ID'],
                              props=props)
                    success_count += 1
                except Exception as e:
                    # Print failed edge for debugging
                    print(f"    Failed: {row[':START_ID']} -> {row[':END_ID']}")
                    print(f"      Error: {str(e)}")
                    print(f"      Query: {edge_query}")
                    print(f"      Params: start_id={row[':START_ID']}, end_id={row[':END_ID']}")
                    pass
            
        
        print(f"  ✓ Created {success_count}/{len(df)} {edge_type} edges")
    
    def upload_all(self, biocypher_dir):
        """Upload all nodes and edges from BioCypher output."""
        with self.driver.session() as session:
            # First, clear the database (optional) - COMMENTED OUT
            # print("\nClearing existing data...")
            # session.run("MATCH (n) DETACH DELETE n")
            
            # Get all CSV files
            all_files = glob.glob(f"{biocypher_dir}/*-part000.csv")
            
            # Separate nodes and edges based on file content
            node_files = []
            edge_files = []
            
            for file in all_files:
                # Check if it's an edge file by looking at the corresponding header file
                try:
                    # Get the header file for this data file
                    header_file = file.replace('-part000.csv', '-header.csv')
                    if os.path.exists(header_file):
                        header_df = pd.read_csv(header_file, sep='\t')
                        if ':START_ID' in header_df.columns and ':END_ID' in header_df.columns:
                            edge_files.append(file)
                        else:
                            node_files.append(file)
                    else:
                        # Fallback: try to detect from first row of data file
                        df_sample = pd.read_csv(file, sep='\t', nrows=1)
                        if ':START_ID' in df_sample.columns and ':END_ID' in df_sample.columns:
                            edge_files.append(file)
                        else:
                            node_files.append(file)
                except:
                    continue
            
            # Upload nodes first
            print(f"\n📦 Uploading {len(node_files)} node types...")
            for node_file in sorted(node_files):
                # Extract node type from filename
                node_type = os.path.basename(node_file).replace('-part000.csv', '')
                if os.path.getsize(node_file) > 0:  # Skip empty files
                    self.upload_nodes(session, node_type, node_file)
            
            # Then upload edges
            print(f"\n🔗 Uploading {len(edge_files)} edge types...")
            for edge_file in sorted(edge_files):
                # Get edge type from the data's :TYPE column, not filename
                try:
                    header_file = edge_file.replace('-part000.csv', '-header.csv')
                    if os.path.exists(header_file):
                        header_df = pd.read_csv(header_file, sep='\t')
                        headers = list(header_df.columns)
                        df_sample = pd.read_csv(edge_file, sep='\t', names=headers, nrows=1)
                        if ':TYPE' in df_sample.columns:
                            edge_type = df_sample[':TYPE'].iloc[0]
                            print(f"  Using :TYPE column value: {edge_type}")
                        else:
                            # Fallback to filename
                            edge_type = os.path.basename(edge_file).replace('-part000.csv', '')
                    else:
                        edge_type = os.path.basename(edge_file).replace('-part000.csv', '')
                except:
                    edge_type = os.path.basename(edge_file).replace('-part000.csv', '')
                
                if os.path.getsize(edge_file) > 0:  # Skip empty files
                    self.upload_edges(session, edge_type, edge_file)
            
            # Create indexes for better performance
            print("\n🔍 Creating indexes...")
            try:
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:Protein) ON (n.id)")
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:Drug) ON (n.id)")
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:Disease) ON (n.id)")
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:Gene) ON (n.id)")
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:Phenotype) ON (n.id)")
                session.run("CREATE INDEX IF NOT EXISTS FOR (n:SideEffect) ON (n.id)")
            except:
                pass  # Indexes might already exist
            
            print("\n✅ Upload complete!")

def find_latest_output():
    """Find the latest BioCypher output directory."""
    output_dirs = glob.glob("biocypher-out/*")
    if not output_dirs:
        return None
    
    # Sort by modification time
    latest = max(output_dirs, key=os.path.getmtime)
    return latest

def main():
    import sys
    
    print("BioCypher to Neo4j Aura Uploader")
    print("=================================")
    
    # Allow command line override of output directory
    global BIOCYPHER_OUTPUT
    if len(sys.argv) > 1:
        BIOCYPHER_OUTPUT = sys.argv[1]
        print(f"Using command line directory: {BIOCYPHER_OUTPUT}")
    
    # Check if credentials are set
    if NEO4J_URI == "neo4j+s://YOUR-INSTANCE.databases.neo4j.io":
        print("\n❌ ERROR: Please update the Neo4j Aura connection details in this script!")
        print("\n📋 Step-by-step instructions:")
        print("\n1. Sign up for Neo4j Aura Free:")
        print("   🔗 https://neo4j.com/cloud/aura-free/")
        print("\n2. Create a new instance:")
        print("   - Click 'New Instance'")
        print("   - Choose 'AuraDB Free' tier")
        print("   - Wait ~5 minutes for provisioning")
        print("\n3. Get your credentials:")
        print("   - Connection URI: Shows in the console (neo4j+s://xxxxx.databases.neo4j.io)")
        print("   - Password: Auto-generated, shown ONCE - copy it immediately!")
        print("\n4. Update this script:")
        print("   - Open: upload_to_neo4j_aura.py")
        print("   - Set NEO4J_URI = \"your-connection-uri\"")
        print("   - Set NEO4J_PASSWORD = \"your-password\"")
        print("\n5. Run this script again!")
        return
    
    # Find BioCypher output directory
    if BIOCYPHER_OUTPUT:
        biocypher_dir = BIOCYPHER_OUTPUT
    else:
        biocypher_dir = find_latest_output()
        if not biocypher_dir:
            print("\n❌ ERROR: No BioCypher output found!")
            print("Please run the pipeline first:")
            print("  poetry run python pipeline/workflows/flexible_pipeline.py --test-mode")
            return
    
    print(f"\n📂 Using BioCypher output: {biocypher_dir}")
    
    # Count files
    csv_files = glob.glob(f"{biocypher_dir}/*-part000.csv")
    print(f"📊 Found {len(csv_files)} data files to upload")
    
    # Create uploader and upload data
    try:
        uploader = Neo4jUploader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    except Exception as e:
        print("\n❌ Could not connect to Neo4j Aura")
        return
    
    try:
        uploader.upload_all(biocypher_dir)
        
        print("\n🎉 Success! Your data is now in Neo4j Aura")
        print(f"\n🌐 Open Neo4j Browser: {NEO4J_URI.replace('+s', '').replace('neo4j://', 'https://')}")
        print("\n📊 Example queries to try:")
        print("  // Count all nodes")
        print("  MATCH (n) RETURN count(n)")
        print("\n  // Show sample nodes")
        print("  MATCH (n) RETURN n LIMIT 25")
        print("\n  // Find proteins")
        print("  MATCH (p:Protein) RETURN p LIMIT 10")
        print("\n  // Find drug-target relationships")
        print("  MATCH (d:Drug)-[r]->(t:Target) RETURN d, r, t LIMIT 10")
        print("\n  // Explore phenotypes")
        print("  MATCH (p:Phenotype) RETURN p.name LIMIT 20")
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        uploader.close()

if __name__ == "__main__":
    main()