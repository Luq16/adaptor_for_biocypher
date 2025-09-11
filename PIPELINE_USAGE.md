# BioCypher Flexible Pipeline Usage Guide

## Overview

The BioCypher pipeline now supports flexible adapter selection, allowing you to create knowledge graphs from single adapters, multiple adapters, or all available adapters based on your research needs.

## Quick Start Commands

### List Available Adapters
```bash
python run_pipeline.py --list
# or
make list-adapters
```

### Single Adapter Usage

#### ChEMBL Only (Drug Discovery)
```bash
# Test mode (recommended first run)
python run_pipeline.py --adapters chembl --test-mode
make run-chembl

# Full data
python run_pipeline.py --adapters chembl
```
**Creates**: Drugs, compounds, targets, and drug-target relationships

#### STRING Only (Protein Interactions)
```bash
python run_pipeline.py --adapters string --test-mode
```
**Creates**: Protein-protein interaction network

#### OpenTargets Only (Target-Disease)
```bash
python run_pipeline.py --adapters opentargets --test-mode

# With real data (large download)
OPENTARGETS_USE_REAL_DATA=true python run_pipeline.py --adapters opentargets
```
**Creates**: Target-disease associations with evidence

### Multiple Adapter Combinations

#### Protein Network (UniProt + STRING)
```bash
python run_pipeline.py --adapters uniprot string --test-mode
make run-protein-network
```
**Creates**: Detailed proteins + their interactions

#### Drug-Target Analysis (ChEMBL + UniProt)
```bash
python run_pipeline.py --adapters chembl uniprot --test-mode
```
**Creates**: Drugs with detailed target information

#### Drug-Target-Disease Triangle
```bash
python run_pipeline.py --adapters chembl uniprot opentargets --test-mode
make run-drug-target-disease
```
**Creates**: Complete drug → target → disease pathway

### All Adapters (Complete Knowledge Graph)
```bash
# Test mode (recommended first run)
python run_pipeline.py --test-mode

# Full pipeline (can take hours)
python run_pipeline.py
```

## Available Adapters

| Adapter | Description | Data Types |
|---------|-------------|------------|
| `uniprot` | UniProt proteins and genes | Proteins, genes, organisms |
| `chembl` | ChEMBL drugs and compounds | Drugs, compounds, targets |
| `string` | STRING protein interactions | Protein-protein interactions |
| `opentargets` | Target-disease associations | Targets, diseases, associations |
| `disease` | Disease Ontology | Disease classifications |
| `go` | Gene Ontology | GO terms, annotations |
| `reactome` | Reactome pathways | Biological pathways |
| `disgenet` | Gene-disease associations | Gene-disease links |

## Command Reference

### Main Pipeline
```bash
# Basic usage
python run_pipeline.py --adapters <adapter1> <adapter2> --test-mode

# Options
--adapters      # Specify which adapters to run
--test-mode     # Use limited data for testing
--real-data     # Use real OpenTargets data (large)
--debug         # Enable debug logging
--list          # List available adapters
```

### Makefile Shortcuts
```bash
make install              # Install dependencies
make list-adapters        # List available adapters
make test                 # Run all adapters in test mode
make run-full             # Run all adapters with full data
make run-chembl           # ChEMBL only
make run-protein-network  # UniProt + STRING
make run-drug-target-disease # ChEMBL + UniProt + OpenTargets
make clean                # Clean outputs
make docker-up            # Start Neo4j
make docker-down          # Stop Neo4j
```

## Research Use Cases

### Drug Discovery
```bash
# Focus on drugs and their targets
make run-drug-target-disease
```

### Systems Biology
```bash
# Focus on protein networks
make run-protein-network
```

### Disease Research
```bash
# Focus on disease associations
python run_pipeline.py --adapters opentargets disgenet --test-mode
```

### Pharmacovigilance
```bash
# Focus on drug safety
python run_pipeline.py --adapters chembl opentargets --test-mode
```

## Performance Guidelines

### Data Sizes (Approximate)

#### Test Mode (~100 records each)
- Total runtime: 5-15 minutes
- Output size: <100MB
- Memory usage: <4GB

#### Full Mode
- **UniProt**: ~20K human proteins
- **ChEMBL**: ~2M compounds
- **STRING**: ~11M interactions  
- **OpenTargets**: ~100K associations
- Total runtime: 1-4 hours
- Output size: 10-50GB
- Memory usage: 8-16GB

### Recommendations

1. **Start with test mode** to validate your setup
2. **Use specific adapter combinations** for focused analysis
3. **Run full pipeline overnight** for complete datasets
4. **Use SSD storage** for better I/O performance
5. **Ensure adequate RAM** (16GB+ recommended for full data)

## Output Structure

```
biocypher-out/YYYYMMDDHHMMSS/
├── *-header.csv           # CSV headers for Neo4j import
├── *-part000.csv          # Data files
└── neo4j-admin-import-call.sh  # Neo4j import script
```

## Troubleshooting

### Common Issues

1. **Import errors**: Some adapters may not be available due to dependency issues
2. **Memory errors**: Use test mode or increase system memory
3. **Network timeouts**: Large downloads may timeout on slow connections
4. **Disk space**: Ensure sufficient space for outputs

### Solutions

- Check available adapters with `--list`
- Use `--test-mode` for development and testing
- Run adapters individually to isolate issues
- Check logs in `biocypher-log/` directory

## Examples Repository

See `examples/adapter_combinations.md` for detailed examples of different adapter combinations for various research scenarios.