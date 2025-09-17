#!/usr/bin/env python3
"""
Clear database, create all required nodes, then upload edges
"""

import pandas as pd
from neo4j import GraphDatabase
import os

# Neo4j connection
NEO4J_URI = "neo4j+s://bf06e3e0.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "2igSbh2Yo-UEYB5CJCVNGwaevVRZLhvrGtKd1D27XJU"

def clear_and_setup():
    """Clear database and create all required nodes in one session"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # Clear everything first
        print("🗑️ Clearing database...")
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create Drug nodes
        print("🔧 Creating Drug nodes...")
        session.run("CREATE (d:Drug {id: 'drugbank:DB00316', name: 'Drug DB00316'})")
        session.run("CREATE (d:Drug {id: 'drugbank:DB00945', name: 'Drug DB00945'})")
        print("  Created 2 Drug nodes")
        
        # Create Gene nodes
        print("🔧 Creating Gene nodes...")
        gene_ids = ['ncbigene:3845', 'ncbigene:16653', 'ncbigene:22059', 'ncbigene:672', 
                   'ncbigene:12189', 'ncbigene:12190', 'ncbigene:7157', 'ncbigene:675']
        for gene_id in gene_ids:
            session.run("CREATE (g:Gene {id: $gene_id, symbol: $symbol})", 
                       gene_id=gene_id, symbol=f"Gene_{gene_id.split(':')[-1]}")
        print(f"  Created {len(gene_ids)} Gene nodes")
        
        # Create Protein nodes  
        print("🔧 Creating Protein nodes...")
        protein_ids = ['uniprot:P24941', 'uniprot:P38936', 'uniprot:P06400', 'uniprot:P04637', 'uniprot:P53350']
        for protein_id in protein_ids:
            session.run("CREATE (p:Protein {id: $protein_id, name: $name})", 
                       protein_id=protein_id, name=f"Protein {protein_id}")
        print(f"  Created {len(protein_ids)} Protein nodes")
        
        print("✅ All required nodes created!")
    
    driver.close()

if __name__ == "__main__":
    clear_and_setup()