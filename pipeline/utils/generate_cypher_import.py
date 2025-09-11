#!/usr/bin/env python3
"""
Generate Cypher queries to paste into Neo4j Browser.
"""

import glob
import os
import csv

# Path to your BioCypher output
BIOCYPHER_OUTPUT = "biocypher-out/20250821002412"  # Update with your latest output directory

def generate_node_queries(csv_file, node_type, limit=100):
    """Generate CREATE queries for nodes."""
    print(f"\n// Creating {node_type} nodes from {os.path.basename(csv_file)}")
    
    # Look for header file
    header_file = csv_file.replace('-part000.csv', '-header.csv').replace('-part001.csv', '-header.csv')
    
    if os.path.exists(header_file):
        # Read header
        with open(header_file, 'r') as f:
            headers = f.readline().strip().split('\t')
        
        # Read data with headers
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t', fieldnames=headers)
            rows = [row for i, row in enumerate(reader) if i < limit]
    else:
        # Try to read with default headers
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            headers = reader.fieldnames
            if ':ID' not in headers:
                headers = [':ID'] + headers[1:] if len(headers) > 1 else [':ID']
            rows = [row for i, row in enumerate(reader) if i < limit]
    
    queries = []
    for row in rows:
        # Create a simple query
        props = {
            'id': row.get(':ID', list(row.values())[0] if row else '')
        }
        
        # Add other non-null properties (limit to avoid too long queries)
        prop_count = 0
        for col, value in row.items():
            if prop_count >= 5:  # Limit properties to keep queries manageable
                break
            if col not in [':ID', ':LABEL', 'id', 'preferred_id'] and value and value.strip():
                value_str = str(value).replace("'", "\\'")  # Escape quotes
                if len(value_str) < 100:  # Skip very long values
                    # Clean property name - remove special characters and type annotations
                    clean_col = col.split(':')[0]  # Remove :type[] annotations
                    clean_col = clean_col.replace('[', '').replace(']', '').replace('.', '_').replace(':', '_')
                    props[clean_col] = value_str
                    prop_count += 1
        
        # Build property string
        prop_str = ', '.join([f"{k}: '{v}'" for k, v in props.items()])
        query = f"CREATE (:{node_type} {{{prop_str}}})"
        queries.append(query)
    
    return queries

def generate_edge_queries(csv_file, edge_type, limit=100):
    """Generate CREATE queries for edges."""
    print(f"\n// Creating {edge_type} relationships from {os.path.basename(csv_file)}")
    
    # Look for header file
    header_file = csv_file.replace('-part000.csv', '-header.csv').replace('-part001.csv', '-header.csv')
    
    if os.path.exists(header_file):
        # Read header
        with open(header_file, 'r') as f:
            headers = f.readline().strip().split('\t')
        
        # Read data with headers
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t', fieldnames=headers)
            rows = [row for i, row in enumerate(reader) if i < limit]
    else:
        # Try to read with default headers
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            rows = [row for i, row in enumerate(reader) if i < limit]
    
    queries = []
    for row in rows:
        start_id = row.get(':START_ID', list(row.values())[0] if row else '')
        end_id = row.get(':END_ID', list(row.values())[1] if len(row.values()) > 1 else '')
        
        query = f"""
MATCH (a {{id: '{start_id}'}})
MATCH (b {{id: '{end_id}'}})
CREATE (a)-[:{edge_type}]->(b)"""
        queries.append(query.strip())
    
    return queries

def main():
    print("BioCypher Cypher Query Generator")
    print("================================")
    print(f"Reading from: {BIOCYPHER_OUTPUT}")
    
    all_queries = []
    
    # Generate node queries
    node_files = glob.glob(f"{BIOCYPHER_OUTPUT}/*-part*.csv")
    node_files = [f for f in node_files if not any(edge in f for edge in ['CompoundTargets', 'IsSubtypeOf', 'AssociatedWith', 'GeneAssociated'])]
    
    for node_file in node_files:
        if os.path.getsize(node_file) > 0:
            node_type = os.path.basename(node_file).split('-')[0]
            queries = generate_node_queries(node_file, node_type, limit=50)
            all_queries.extend(queries)
    
    # Generate edge queries
    edge_mapping = {
        'CompoundTargets': 'TARGETS',
        'IsSubtypeOf': 'IS_SUBTYPE_OF',
        'AssociatedWith': 'ASSOCIATED_WITH',
        'GeneAssociated': 'ASSOCIATED_WITH'
    }
    
    edge_files = glob.glob(f"{BIOCYPHER_OUTPUT}/*-part*.csv")
    edge_files = [f for f in edge_files if any(edge in f for edge in edge_mapping.keys())]
    
    for edge_file in edge_files:
        if os.path.getsize(edge_file) > 0:
            filename = os.path.basename(edge_file)
            for key, edge_type in edge_mapping.items():
                if key in filename:
                    # Use different limits for different relationship types
                    if 'CompoundTargets' in filename:
                        limit = 30  # Drug-target relationships
                    elif 'GeneAssociated' in filename:
                        limit = 10  # Gene-disease associations (only 4 in file)
                    else:
                        limit = 30  # Disease hierarchy
                    queries = generate_edge_queries(edge_file, edge_type, limit=limit)
                    all_queries.extend(queries)
                    break
    
    # Write queries to file
    output_file = "neo4j_import_queries.cypher"
    with open(output_file, 'w') as f:
        f.write("// BioCypher Import Queries\n")
        f.write("// Copy and paste these into Neo4j Browser\n\n")
        
        # Write in batches
        batch_size = 50
        for i in range(0, len(all_queries), batch_size):
            f.write(f"\n// Batch {i//batch_size + 1}\n")
            batch = all_queries[i:i+batch_size]
            f.write(';\n'.join(batch))
            f.write(';\n')
    
    print(f"\n✅ Generated {len(all_queries)} queries")
    print(f"📄 Saved to: {output_file}")
    print("\n📋 Instructions:")
    print("1. Open Neo4j Browser (from Aura, Desktop, or Sandbox)")
    print("2. Copy queries from neo4j_import_queries.cypher")
    print("3. Paste into Neo4j Browser query window")
    print("4. Click Run")
    print("\n⚠️  Note: This creates a sample with first 50 entries of each type")
    print("For full data import, use Neo4j Desktop or the upload_to_aura.py script")

if __name__ == "__main__":
    main()