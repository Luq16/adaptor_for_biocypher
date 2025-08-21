// 🧬 Import Combined UniProt + ChEMBL Knowledge Graph to Neo4j
// Run these commands in Neo4j Browser after starting Docker container

// Clear existing data (optional)
MATCH (n) DETACH DELETE n;

// Import Proteins from UniProt
LOAD CSV WITH HEADERS FROM 'file:///20250820232122/Protein-part000.csv' AS row
FIELDTERMINATOR '\t'
CREATE (p:Protein {
  id: row.`:ID`,
  source: 'uniprot',
  biolink_type: row.`:LABEL`
});

// Check import success
MATCH (p:Protein) RETURN count(p) as protein_count;

// View sample proteins
MATCH (p:Protein) RETURN p LIMIT 5;

// Get statistics
MATCH (n) 
RETURN labels(n) as node_type, count(n) as count
ORDER BY count DESC;