# BioCypher Real Data Adapters

This project provides BioCypher adapters for extracting real biological data from public databases and creating comprehensive knowledge graphs.

## Available Adapters

### 1. UniProt Adapter
Extracts protein, gene, and organism data from UniProt/SwissProt.

**Data provided:**
- Protein nodes with properties (sequence, function, mass, length, etc.)
- Gene nodes with identifiers (Entrez, Ensembl)
- Organism nodes
- Gene-to-protein relationships
- Protein-to-organism relationships

**Usage:**
```python
from template_package.adapters import UniprotAdapter

adapter = UniprotAdapter(
    organism="9606",  # Human
    reviewed=True,    # SwissProt only
    test_mode=True    # Limit data for testing
)
adapter.download_data()
```

### 2. ChEMBL Adapter
Extracts drug, compound, and target data from ChEMBL database.

**Data provided:**
- Drug nodes (approved medications)
- Compound nodes (bioactive molecules)
- Target nodes (proteins targeted by drugs/compounds)
- Compound-targets-protein relationships with bioactivity data

**Usage:**
```python
from template_package.adapters import ChemblAdapter

adapter = ChemblAdapter(
    max_phase=4,      # Only approved drugs
    organism="Homo sapiens",
    test_mode=True
)
adapter.download_data(limit=100)
```

### 3. Disease Ontology Adapter
Extracts disease classifications from Disease Ontology (DO) or MONDO.

**Data provided:**
- Disease nodes with definitions, synonyms, and cross-references
- Disease hierarchy (is-a relationships)
- Disease-to-disease relationships

**Usage:**
```python
from template_package.adapters import DiseaseOntologyAdapter

adapter = DiseaseOntologyAdapter(
    ontology="DO",    # or "MONDO"
    include_obsolete=False,
    test_mode=True
)
adapter.download_data()
```

### 4. STRING Adapter
Extracts protein-protein interaction data from the STRING database.

**Data provided:**
- Protein-protein interaction edges with confidence scores
- Physical interaction edges (high-confidence physical binding)
- Functional association edges (functional relationships)
- Evidence channels (experimental, database, text mining, etc.)

**Usage:**
```python
from template_package.adapters import StringAdapter

adapter = StringAdapter(
    organism="9606",  # Human
    score_threshold=0.4,    # Medium confidence
    test_mode=True
)
adapter.download_data()
```

### 5. Gene Ontology (GO) Adapter
Extracts functional annotations and GO term hierarchies from the Gene Ontology.

**Data provided:**
- GO term nodes (biological process, molecular function, cellular component)
- GO term hierarchical relationships (is-a, part-of, regulates)
- Protein-GO term annotations with evidence codes

**Usage:**
```python
from template_package.adapters import GOAdapter

adapter = GOAdapter(
    organism="9606",  # Human
    go_aspects=['P', 'F', 'C'],  # All aspects
    test_mode=True
)
adapter.download_data()
```

### 6. Reactome Pathway Adapter
Extracts biological pathway data from the Reactome database.

**Data provided:**
- Pathway nodes with names and descriptions
- Protein-pathway participation relationships
- Pathway hierarchy relationships

**Usage:**
```python
from template_package.adapters import ReactomeAdapter

adapter = ReactomeAdapter(
    organism="9606",  # Human
    include_disease_pathways=True,
    test_mode=True
)
adapter.download_data()
```

### 7. DisGeNET Gene-Disease Adapter
Extracts gene-disease associations from the DisGeNET database.

**Data provided:**
- Gene-disease association edges with confidence scores
- Evidence information and source tracking
- Clinical relevance indicators

**Usage:**
```python
from template_package.adapters import DisGeNETAdapter

adapter = DisGeNETAdapter(
    score_threshold=0.1,  # Minimum confidence
    evidence_level="all",  # Curated and literature
    test_mode=True
)
adapter.download_data()
```

## Quick Start

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Run individual adapter examples:**
   ```bash
   python examples/uniprot_example.py
   python examples/chembl_example.py
   python examples/string_example.py
   ```

3. **Create complete knowledge graph:**
   ```bash
   python create_biological_knowledge_graph.py
   ```

4. **Test mode for development:**
   ```bash
   export BIOCYPHER_TEST_MODE=true
   python create_biological_knowledge_graph.py
   ```

5. **Run tests:**
   ```bash
   python run_tests.py
   # Or run specific tests
   python run_tests.py test_adapters.TestUniprotAdapter
   ```

## Configuration

### Schema Configuration
The `config/schema_config.yaml` file defines how data is mapped to the knowledge graph schema. Key mappings include:

- `protein`: UniProt proteins
- `gene`: Genes from various databases
- `drug`: Approved medications from ChEMBL
- `compound`: Bioactive compounds from ChEMBL
- `disease`: Disease entities from DO/MONDO
- Various relationship types between these entities

### BioCypher Configuration
The `config/biocypher_config.yaml` file controls BioCypher behavior:
- Output format (Neo4j, CSV, etc.)
- Database connection settings
- Import configuration

## Data Sources

| Adapter | Source Database | License | Update Frequency |
|---------|----------------|---------|------------------|
| UniProt | UniProt/SwissProt | CC BY 4.0 | Monthly |
| ChEMBL | ChEMBL Database | CC BY-SA 3.0 | Quarterly |
| Disease Ontology | DO/MONDO | CC0 1.0 | Monthly |
| STRING | STRING Database | CC BY 4.0 | Annually |
| Gene Ontology | GO Consortium | CC BY 4.0 | Monthly |
| Reactome | Reactome Database | CC BY 4.0 | Quarterly |
| DisGeNET | DisGeNET Database | CC BY-NC-SA 4.0 | Annually |

## Output

The adapters generate files compatible with Neo4j import:
- Node CSV files for each entity type
- Edge CSV files for relationships
- Import commands for Neo4j

## Extending the Adapters

To add a new data source:

1. Create a new adapter class inheriting from `BaseAdapter`
2. Define node types, fields, and edge types as Enums
3. Implement `download_data()`, `get_nodes()`, and `get_edges()` methods
4. Update `schema_config.yaml` with new entity types
5. Add the adapter to the orchestration script

Example structure:
```python
class MyAdapter(BaseAdapter):
    def download_data(self):
        # Fetch data from source
        pass
    
    def get_nodes(self):
        # Yield (id, label, properties) tuples
        pass
    
    def get_edges(self):
        # Yield (edge_id, source, target, label, properties) tuples
        pass
```

## Common Issues

1. **Memory issues with large datasets:**
   - Use `test_mode=True` for development
   - Implement streaming/pagination in adapters
   - Process data in batches

2. **Download failures:**
   - Check internet connection
   - Verify API endpoints are accessible
   - Use cached data when available

3. **Import errors:**
   - Ensure Neo4j is running
   - Check file paths in import statements
   - Verify CSV formatting

## Testing

The project includes comprehensive tests for all adapters:

### Running Tests
```bash
# Run all tests
python run_tests.py

# Run specific adapter tests
python run_tests.py test_adapters.TestUniprotAdapter
python run_tests.py test_adapters.TestChemblAdapter

# Run integration tests
python run_tests.py test_integration.TestPipelineIntegration
```

### Test Coverage
- Unit tests for each adapter
- Integration tests for the complete pipeline
- Data validation tests
- Schema configuration validation
- Mock tests for external API dependencies

## Future Enhancements

- Reactome/KEGG adapters for pathway data
- Gene Ontology adapter for functional annotations
- DisGeNET adapter for gene-disease associations
- DrugBank adapter for additional drug information
- Enhanced ID mapping between databases

## Contributing

When contributing new adapters:
1. Follow the existing adapter patterns
2. Include comprehensive docstrings
3. Add appropriate test cases
4. Update schema configuration
5. Document data sources and licenses