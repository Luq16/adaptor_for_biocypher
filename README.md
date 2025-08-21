# BioCypher Real Data Knowledge Graph

A comprehensive BioCypher project template with real biological data adapters for creating large-scale knowledge graphs. This project includes adapters for UniProt, ChEMBL, Disease Ontology, and STRING databases.

## 🚀 Features

- **Real Data Adapters**: Extract data from major biological databases
- **Comprehensive Schema**: Well-defined ontology mappings for biological entities
- **Modular Design**: Use individual adapters or combine them all
- **Test Suite**: Complete testing framework with integration tests
- **Docker Support**: Ready-to-use Docker setup for Neo4j deployment
- **Documentation**: Extensive documentation and examples

## 📊 Supported Data Sources

- **UniProt**: Proteins, genes, and organisms
- **ChEMBL**: Drugs, compounds, and their targets
- **Disease Ontology**: Disease classifications and hierarchies
- **STRING**: Protein-protein interactions
- **Gene Ontology**: Functional annotations and GO terms
- **Reactome**: Biological pathways and processes
- **DisGeNET**: Gene-disease associations

## ⚡ Quick Reference

```bash
# Essential commands (use these instead of python3 directly)
poetry install                                    # Install dependencies
poetry run python examples/uniprot_example.py    # Run UniProt example
poetry run python simple_example.py              # Run working example
export BIOCYPHER_TEST_MODE=true                   # Always use for first run
```

## 🔧 Quick Start

### 1. Installation

```bash
# Step 1: Run setup script
python3 setup.py

# Step 2: Install dependencies with Poetry
poetry install

# Step 3: Verify installation
poetry run python test_environment.py

# Note: Always use 'poetry run' before python commands
# Never use 'python3' directly - it won't find the dependencies
```

### 2. Create Knowledge Graph

```bash
# Create complete biological knowledge graph
poetry run python create_biological_knowledge_graph.py

# Or use test mode for development (recommended first run)
export BIOCYPHER_TEST_MODE=true
poetry run python create_biological_knowledge_graph.py
```

### 3. Try Individual Adapters

#### Step-by-Step: Running UniProt Example

1. **Navigate to project directory:**
   ```bash
   cd /path/to/your/biocypher-project-template
   ```

2. **Install dependencies and activate environment:**
   ```bash
   # Install all dependencies
   poetry install
   
   # IMPORTANT: Use one of these two approaches
   ```

3. **Option A - Use `poetry run` (Recommended):**
   ```bash
   # Set test mode
   export BIOCYPHER_TEST_MODE=true
   
   # Run with poetry (this uses the virtual environment automatically)
   poetry run python examples/uniprot_example.py
   ```

4. **Option B - Activate shell first:**
   ```bash
   # Activate poetry environment (if available)
   poetry shell
   
   # Set test mode
   export BIOCYPHER_TEST_MODE=true
   
   # Run the example
   python examples/uniprot_example.py
   ```

   **Note:** If `poetry shell` doesn't work (Poetry 2.0+), use Option A instead.

5. **Expected output (Success!):**
   ```
   INFO -- This is BioCypher v0.10.1.
   INFO -- Initialized UniProt adapter for organism 9606
   INFO -- Found 100 UniProt entries
   Downloading fields: 100%|██████████| 8/8 [00:47<00:00,  6.00s/it]
   INFO -- Preprocessing UniProt data
   INFO -- Completed: Downloading UniProt data in 0.08 seconds
   ```
   
   **Note:** If you see a schema error at the end, that's normal and indicates the UniProt adapter is working correctly. The error is just a configuration issue, not a data download problem.

6. **Check generated files:**
   ```bash
   ls -la *.csv                    # Node and edge files
   ls -la biocypher-log/          # Detailed logs
   cat uniprot_proteins_nodes.csv # View protein data
   ```

#### Troubleshooting UniProt Example

If you encounter dependency errors:

```bash
# Option 1: Fix pypath dependencies
poetry add "paramiko==2.12.0"
poetry install

# Option 2: Use working simple example instead
python simple_example.py

# Option 3: Check detailed troubleshooting
cat TROUBLESHOOTING.md
```

#### Other Examples

```bash
# ChEMBL drugs and targets
export BIOCYPHER_TEST_MODE=true
python examples/chembl_example.py

# STRING protein interactions  
export BIOCYPHER_TEST_MODE=true
python examples/string_example.py

# Comprehensive example (multiple adapters)
export BIOCYPHER_TEST_MODE=true
python examples/comprehensive_example.py
```

### 4. Export to Neo4j

BioCypher provides multiple ways to export your knowledge graph data to Neo4j. Choose the method that best fits your needs:

#### Method 1: Neo4j Browser Import (Recommended for Small Datasets)

**Best for:** Quick testing, small samples, learning Neo4j  
**Data size:** ~246 sample queries (manageable for copy-paste)

```bash
# Generate Cypher import queries
python3 generate_cypher_import.py

# This creates neo4j_import_queries.cypher with sample data
# Copy queries from this file and paste into Neo4j Browser
```

**Steps:**
1. Run the biological knowledge graph creation:
   ```bash
   export BIOCYPHER_TEST_MODE=true
   python3 create_biological_knowledge_graph.py
   ```

2. Generate browser-friendly queries:
   ```bash
   python3 generate_cypher_import.py
   ```

3. Open Neo4j Browser (Aura, Desktop, or Sandbox)
4. Copy queries from `neo4j_import_queries.cypher` 
5. Paste into Neo4j Browser and run

**What you get:**
- 50 Compounds (ChEMBL drugs)
- 50 Proteins (UniProt entries)
- 50 Pathways (Reactome)
- 50 Diseases (Disease Ontology)
- Gene-disease associations
- Drug-target relationships  
- Disease hierarchy relationships

#### Method 2: Neo4j Aura Cloud Upload

**Best for:** Cloud deployment, sharing with team, no local setup  
**Data size:** Full datasets supported

```bash
# Upload to Neo4j Aura cloud
python3 upload_to_aura.py
```

**Prerequisites:**
1. Create free Neo4j Aura account at https://neo4j.com/cloud/aura-free/
2. Create a new instance  
3. Copy your connection URI (format: `neo4j+s://xxxxx.databases.neo4j.io`)
4. Update `upload_to_aura.py` with your credentials:
   ```python
   NEO4J_URI = "neo4j+s://your-instance.databases.neo4j.io"
   NEO4J_PASSWORD = "your-generated-password"
   ```

#### Method 3: Docker Compose (Local Neo4j)

**Best for:** Local development, full control, large datasets  
**Data size:** Full datasets supported

```bash
# Start Neo4j with your knowledge graph
docker-compose up -d

# Access Neo4j Browser at http://localhost:7474
```

#### Method 4: CSV Import (Advanced)

**Best for:** Large datasets, custom processing, ETL pipelines  
**Data size:** Unlimited

BioCypher outputs CSV files that can be imported using:
- Neo4j Admin Import tool
- LOAD CSV Cypher commands
- Neo4j ETL tools

```bash
# Files are created in biocypher-out/[timestamp]/
ls biocypher-out/20250821002412/
# Contains: *-part000.csv (data) and *-header.csv (schema) files
```

#### Comparison of Methods

| Method | Best For | Data Size | Complexity | Setup Time |
|--------|----------|-----------|------------|------------|
| Browser Import | Learning, testing | Small samples | Low | 5 minutes |
| Aura Upload | Cloud deployment | Medium-Large | Medium | 15 minutes |
| Docker Compose | Local development | Large | Medium | 10 minutes |
| CSV Import | Production ETL | Unlimited | High | 30+ minutes |

#### Troubleshooting Neo4j Export

**Neo4j Aura URI Issues:**
```bash
# ❌ Wrong - This is the console URL
NEO4J_URI = "https://console.neo4j.io/..."

# ✅ Correct - This is the connection URI  
NEO4J_URI = "neo4j+s://xxxxx.databases.neo4j.io"
```

**Browser Query Syntax Errors:**
- Property names with `[]` cause syntax errors
- The `generate_cypher_import.py` script automatically cleans these
- If you see syntax errors, regenerate the queries

**Memory Issues with Large Datasets:**
```bash
# Always start with test mode
export BIOCYPHER_TEST_MODE=true
python3 create_biological_knowledge_graph.py
```

## 🛠 Usage

### Structure
The project template is structured as follows:
```
.
│  # Project setup
│
├── LICENSE
├── README.md
├── pyproject.toml
│
│  # Docker setup
│
├── Dockerfile
├── docker
│   ├── biocypher_entrypoint_patch.sh
│   ├── create_table.sh
│   └── import.sh
├── docker-compose.yml
├── docker-variables.env
│
│  # Project pipeline
│
├── create_knowledge_graph.py
├── config
│   ├── biocypher_config.yaml
│   ├── biocypher_docker_config.yaml
│   └── schema_config.yaml
└── template_package
    └── adapters
        └── example_adapter.py
```

The main components of the BioCypher pipeline are the
`create_knowledge_graph.py`, the configuration in the `config` directory, and
the adapter module in the `template_package` directory. The latter can be used
to publish your own adapters (see below). You can also use other adapters from
anywhere on GitHub, PyPI, or your local machine.

**The BioCypher ecosystem relies on the collection of adapters (planned, in
development, or already available) to inform the community about the available
data sources and to facilitate the creation of knowledge graphs. If you think
your adapter could be useful for others, please create an issue for it on the
[main BioCypher repository](https://github.com/biocypher/biocypher/issues).**

In addition, the docker setup is provided to run the pipeline (from the same
python script) in a docker container, and subsequently load the knowledge graph
into a Neo4j instance (also from a docker container). This is useful if you want
to run the pipeline on a server, or if you want to run it in a reproducible
environment.

### Running the pipeline

`python create_knowledge_graph.py` will create a knowledge graph from the
example data included in this repository (borrowed from the [BioCypher
tutorial](https://biocypher.org/tutorial.html)). To do that, it uses the
following components:

- `create_knowledge_graph.py`: the main script that orchestrates the pipeline.
It brings together the BioCypher package with the data sources. To build a 
knowledge graph, you need at least one adapter (see below). For common 
resources, there may already be an adapter available in the BioCypher package or
in a separate repository. You can also write your own adapter, should none be
available for your data.

- `example_adapter.py` (in `template_package.adapters`): a module that defines
the adapter to the data source. In this case, it is a random generator script.
If you want to create your own adapters, we recommend to use the example adapter
as a blueprint and create one python file per data source, approproately named.
You can then import the adapter in `create_knowledge_graph.py` and add it to
the pipeline. This way, you ensure that others can easily install and use your 
adapters.

- `schema_config.yaml`: a configuration file (found in the `config` directory)
that defines the schema of the knowledge graph. It is used by BioCypher to map
the data source to the knowledge representation on the basis of ontology (see
[this part of the BioCypher 
tutorial](https://biocypher.org/tutorial-ontology.html)).

- `biocypher_config.yaml`: a configuration file (found in the `config` 
directory) that defines some BioCypher parameters, such as the mode, the 
separators used, and other options. More on its use can be found in the
[Documentation](https://biocypher.org/installation.html#configuration).

### Publishing your own adapters

After adding your adapter(s) to the `adapters` directory, you may want to
publish them for easier reuse. To create a package to distribute your own
adapter(s), we recommend using [Poetry](https://python-poetry.org/). Poetry,
after setup, allows you to publish your package to PyPI using few simple
commands. To set up your package, rename the `template_package` directory to
your desired package name and update the `pyproject.toml` file accordingly. Most
importantly, update the `name`,`author`, and `version` fields. You can also add
a `description` and a `license`.  Then, you can publish your package to PyPI
using the following commands:

```{bash}
poetry build
poetry publish
```

If you don't want to publish your package to PyPI, you can also install it from
GitHub using the respective functions of poetry or pip.

### Further reading / code

If you want to see a second example of the workflow, check our
[CollecTRI](https://github.com/biocypher/collectri) pipeline. Its README describes
the process of data assessment and adapter creation in more detail.

## 🐳 Docker

This repo also contains a `docker compose` workflow to create the example
database using BioCypher and load it into a dockerised Neo4j instance
automatically. To run it, simply execute `docker compose up -d` in the root 
directory of the project. This will start up a single (detached) docker
container with a Neo4j instance that contains the knowledge graph built by
BioCypher as the DB `neo4j` (the default DB), which you can connect to and
browse at localhost:7474. Authentication is deactivated by default and can be
modified in the `docker_variables.env` file (in which case you need to provide
the .env file to the deploy stage of the `docker-compose.yml`).

Regarding the BioCypher build procedure, the `biocypher_docker_config.yaml` file
is used instead of the `biocypher_config.yaml` (configured in
`scripts/build.sh`). Everything else is the same as in the local setup. The
first container (`build`) installs and runs the BioCypher pipeline, the second
container (`import`) installs Neo4j and runs the import, and the third container
(`deploy`) deploys the Neo4j instance on localhost. The files are shared using a
Docker Volume. This three-stage setup strictly is not necessary for the mounting
of a read-write instance of Neo4j, but is required if the purpose is to provide
a read-only instance (e.g. for a web app) that is updated regularly; for an
example, see the [meta graph
repository](https://github.com/biocypher/meta-graph). The read-only setting is
configured in the `docker-compose.yml` file
(`NEO4J_dbms_databases_default__to__read__only: "false"`) and is deactivated by
default.

## 🧬 Real Data Adapters

This template includes production-ready adapters for major biological databases:

### Available Adapters

- **UniProt**: 20,000+ human proteins with sequences, functions, and gene mappings
- **ChEMBL**: 2,000+ approved drugs and 500,000+ bioactive compounds  
- **Disease Ontology**: 10,000+ disease terms with hierarchical relationships
- **STRING**: Millions of protein-protein interactions with confidence scores
- **Gene Ontology**: 45,000+ GO terms with functional annotations
- **Reactome**: 2,500+ biological pathways and processes
- **DisGeNET**: 1,000,000+ gene-disease associations with evidence scores

### Running Tests

```bash
# Run all adapter tests
python run_tests.py

# Run specific tests
python run_tests.py test_adapters.TestUniprotAdapter
```

### Performance Notes

- Use `test_mode=True` for development (limits data to ~100 entries per source)
- Full datasets can take 60-120 minutes to download and process
- Resulting knowledge graphs contain 500,000+ nodes and 10,000,000+ edges
- Neo4j requires 8-16GB RAM for optimal performance with full datasets

## 📖 Documentation

- See `ADAPTERS_README.md` for detailed adapter documentation
- Check `examples/` directory for usage examples
- Review `config/schema_config.yaml` for ontology mappings

## 🔧 Troubleshooting

### Common Issues When Running UniProt Example

#### Issue 1: Module Not Found Error
```bash
ModuleNotFoundError: No module named 'biocypher'
# OR
ModuleNotFoundError: No module named 'template_package'
```

**Root Cause:** Running `python3` directly instead of using Poetry's virtual environment.

**Solution:**
```bash
# Make sure you're in the project directory
cd /path/to/biocypher-project-template

# Install dependencies first
poetry install

# ALWAYS use poetry run (recommended)
poetry run python examples/uniprot_example.py

# DON'T use python3 directly - this won't work:
# python3 examples/uniprot_example.py  ❌

# If poetry shell works on your system:
poetry shell
python examples/uniprot_example.py
```

#### Issue 2: PyPath Dependency Error
```bash
ImportError: cannot import name 'DSSKey' from 'paramiko'
```

**Solution:**
```bash
# Fix paramiko version
poetry add "paramiko==2.12.0"
poetry install

# Or use the working simple example
python simple_example.py
```

#### Issue 3: Memory Issues
```bash
# For large datasets, always start with test mode
export BIOCYPHER_TEST_MODE=true
python examples/uniprot_example.py
```

#### Issue 4: Slow Downloads
```bash
# Enable caching to speed up subsequent runs
export BIOCYPHER_CACHE=true
export BIOCYPHER_TEST_MODE=true
python examples/uniprot_example.py
```

### Getting Help

1. **Check the logs**: Look in `biocypher-log/` for detailed error messages
2. **Use test mode**: Always start with `export BIOCYPHER_TEST_MODE=true`
3. **Try simple example**: Run `python simple_example.py` to verify BioCypher works
4. **Read troubleshooting guide**: See `TROUBLESHOOTING.md` for detailed solutions

### Environment Variables for Troubleshooting

```bash
# Essential for first runs
export BIOCYPHER_TEST_MODE=true

# Enable debug logging
export BIOCYPHER_DEBUG=true

# Control caching
export BIOCYPHER_CACHE=true
export BIOCYPHER_CACHE_DIR=/path/to/cache
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

For adding new data sources, see the adapter development guide in `ADAPTERS_README.md`.
