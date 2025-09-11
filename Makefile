.PHONY: help install test clean run-test run-full list-adapters run-chembl run-protein-network run-drug-target-disease docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install              - Install dependencies with Poetry"
	@echo "  make list-adapters        - List available adapters"
	@echo "  make test                 - Run all adapters in test mode"
	@echo "  make run-full             - Run all adapters with full data"
	@echo "  make run-chembl           - Run ChEMBL adapter only"
	@echo "  make run-protein-network  - Run UniProt + STRING (protein network)"
	@echo "  make run-drug-target-disease - Run ChEMBL + UniProt + OpenTargets"
	@echo "  make clean                - Clean generated outputs and logs"
	@echo "  make docker-up            - Start Neo4j with Docker"
	@echo "  make docker-down          - Stop Neo4j containers"

install:
	poetry install

list-adapters:
	python run_pipeline.py --list

test:
	python run_pipeline.py --test-mode

run-full:
	python run_pipeline.py

run-chembl:
	python run_pipeline.py --adapters chembl --test-mode

run-protein-network:
	BIOCYPHER_TEST_MODE=true poetry run python pipeline/workflows/protein_network.py

run-drug-target-disease:
	BIOCYPHER_TEST_MODE=true poetry run python pipeline/workflows/drug_target_disease.py

run-real-data:
	OPENTARGETS_USE_REAL_DATA=true python run_pipeline.py

clean:
	rm -rf pipeline/output/*
	rm -rf pipeline/logs/*
	rm -rf pipeline/cache/*
	rm -rf biocypher-out/
	rm -rf biocypher-log/
	rm -rf pypath_log/

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down