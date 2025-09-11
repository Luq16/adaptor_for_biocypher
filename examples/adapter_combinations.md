# Adapter Combination Examples

This document provides examples of different adapter combinations for creating specialized knowledge graphs.

## Single Adapter Examples

### 1. ChEMBL Only - Drug Discovery Focus
```bash
# Run ChEMBL adapter only
python run_pipeline.py --adapters chembl --test-mode

# Or use the dedicated script
BIOCYPHER_TEST_MODE=true poetry run python pipeline/workflows/chembl_only.py
```

**Use case**: Drug discovery, pharmaceutical research, compound analysis
**Data**: Drugs, compounds, targets, drug-target relationships

### 2. STRING Only - Protein Interactions
```bash
# Run STRING adapter only
python run_pipeline.py --adapters string --test-mode
```

**Use case**: Protein-protein interaction analysis, network biology
**Data**: Protein-protein interactions with confidence scores

### 3. OpenTargets Only - Target-Disease Associations
```bash
# Run OpenTargets adapter only
python run_pipeline.py --adapters opentargets --test-mode

# With real data (large download)
OPENTARGETS_USE_REAL_DATA=true python run_pipeline.py --adapters opentargets
```

**Use case**: Target identification, disease research, therapeutic hypothesis
**Data**: Target-disease associations with evidence scores

## Two-Adapter Combinations

### 1. Protein Network (UniProt + STRING)
```bash
# Create comprehensive protein interaction network
BIOCYPHER_TEST_MODE=true poetry run python pipeline/workflows/protein_network.py

# Or via main pipeline
python run_pipeline.py --adapters uniprot string --test-mode
```

**Use case**: Systems biology, protein function analysis, pathway analysis
**Data**: Proteins with detailed annotations + their interactions

### 2. Drug-Target Analysis (ChEMBL + UniProt)
```bash
# Combine drug data with detailed target information
python run_pipeline.py --adapters chembl uniprot --test-mode
```

**Use case**: Drug mechanism research, target validation
**Data**: Drugs/compounds + detailed target protein information

### 3. Target-Disease Focus (UniProt + OpenTargets)
```bash
# Focus on target-disease relationships
python run_pipeline.py --adapters uniprot opentargets --test-mode
```

**Use case**: Target prioritization, disease mechanism research
**Data**: Detailed protein data + disease associations

## Three-Adapter Combinations

### 1. Drug-Target-Disease Triangle (ChEMBL + UniProt + OpenTargets)
```bash
# Complete drug discovery pipeline
BIOCYPHER_TEST_MODE=true poetry run python pipeline/workflows/drug_target_disease.py

# Or via main pipeline
python run_pipeline.py --adapters chembl uniprot opentargets --test-mode
```

**Use case**: Comprehensive drug discovery, repurposing analysis
**Data**: Complete drug → target → disease pathway

### 2. Protein Network with Diseases (UniProt + STRING + OpenTargets)
```bash
# Protein networks with disease context
python run_pipeline.py --adapters uniprot string opentargets --test-mode
```

**Use case**: Disease pathway analysis, biomarker discovery
**Data**: Protein interactions + disease associations

### 3. Chemical-Protein-Disease (ChEMBL + STRING + OpenTargets)
```bash
# Focus on chemical-biological-disease relationships
python run_pipeline.py --adapters chembl string opentargets --test-mode
```

**Use case**: Polypharmacology research, side effect prediction
**Data**: Drugs + protein networks + disease associations

## Full Pipeline - All Adapters

### Complete Biological Knowledge Graph
```bash
# All available adapters (default)
python run_pipeline.py --test-mode

# Explicit specification
python run_pipeline.py --adapters all --test-mode

# With real data (very large)
python run_pipeline.py
```

**Use case**: Comprehensive biological research, multi-omics integration
**Data**: Complete biological knowledge graph with all relationships

## Custom Combinations

### Research-Specific Examples

#### Cancer Research Focus
```bash
# Focus on cancer-relevant data
python run_pipeline.py --adapters uniprot opentargets disgenet --test-mode
```

#### Neuroscience Focus
```bash
# Brain-specific proteins and interactions
python run_pipeline.py --adapters uniprot string go --test-mode
```

#### Pharmacovigilance
```bash
# Drug safety and side effects
python run_pipeline.py --adapters chembl opentargets disgenet --test-mode
```

## Performance Considerations

### Test Mode vs Full Data
- **Test Mode** (`--test-mode`): ~100 records per adapter, completes in minutes
- **Full Data**: Millions of records, can take hours

### Data Size Estimates (Full Mode)
- **UniProt**: ~20K human proteins
- **ChEMBL**: ~2M compounds, ~500K drugs
- **STRING**: ~11M protein interactions
- **OpenTargets**: ~100K target-disease associations (real data)
- **All Combined**: 10-50GB knowledge graph

### Recommendations
1. **Start with test mode** to validate your setup
2. **Use specific combinations** for focused research
3. **Run full pipeline overnight** for complete data
4. **Use SSD storage** for better performance
5. **Ensure 16GB+ RAM** for full datasets