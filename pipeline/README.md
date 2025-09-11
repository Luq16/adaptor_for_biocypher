# BioCypher Knowledge Graph Pipeline

## Directory Structure

```
pipeline/
├── adapters/           # Data source adapters (UniProt, ChEMBL, etc.)
├── config/            # Configuration files (BioCypher, schema)
├── data/              # Data storage
│   ├── raw/          # Downloaded raw data
│   └── processed/    # Processed/transformed data
├── logs/             # Pipeline execution logs
├── cache/            # Cached data for faster reruns
├── output/           # Generated knowledge graph outputs
├── scripts/          # Shell scripts and utilities
│   └── docker/       # Docker-related scripts
├── utils/            # Python utility modules
└── workflows/        # Pipeline workflow scripts
    └── main_pipeline.py  # Main orchestration script
```

## Usage

From the project root, run:

```bash
# Test mode (limited data)
python run_pipeline.py --test-mode

# Full pipeline
python run_pipeline.py

# With debug logging
python run_pipeline.py --debug

# Real OpenTargets data
python run_pipeline.py --real-data
```

## Adapters

- **UniProt**: Proteins, genes, organisms
- **ChEMBL**: Drugs, compounds, targets
- **Disease Ontology**: Disease classifications
- **STRING**: Protein-protein interactions
- **Gene Ontology**: GO terms and annotations
- **Reactome**: Biological pathways
- **DisGeNET**: Gene-disease associations
- **OpenTargets**: Target-disease associations