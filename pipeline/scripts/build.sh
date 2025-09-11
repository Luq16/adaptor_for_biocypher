#!/bin/bash -c
cd /usr/app/
cp -r /src/* .
cp config/biocypher_docker_config.yaml config/biocypher_config.yaml
poetry install
BIOCYPHER_TEST_MODE=true python3 create_biological_knowledge_graph.py
chmod -R 777 biocypher-log