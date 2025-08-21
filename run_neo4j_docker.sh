#!/bin/bash
echo "🐳 Starting Neo4j with your knowledge graph data..."

# Stop any existing neo4j container
docker stop neo4j 2>/dev/null || true
docker rm neo4j 2>/dev/null || true

# Start Neo4j with your data mounted
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -v "$PWD/biocypher-out:/var/lib/neo4j/import" \
    -e NEO4J_AUTH=neo4j/password \
    -e NEO4J_PLUGINS='["apoc"]' \
    neo4j:latest

echo "✅ Neo4j started!"
echo ""
echo "🌐 Access Neo4j Browser:"
echo "   URL: http://localhost:7474"
echo "   Username: neo4j"
echo "   Password: password"
echo ""
echo "⏳ Wait 30 seconds for Neo4j to start, then run the import commands..."