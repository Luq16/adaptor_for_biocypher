# Troubleshooting Guide

## Common Issues and Solutions

### 1. ModuleNotFoundError: No module named 'template_package'

**Problem**: Python can't find the adapter modules.

**Solutions**:
```bash
# Option 1: Run from project root directory
cd /path/to/project-template
python examples/uniprot_example.py

# Option 2: Install in development mode
poetry install
poetry shell
python examples/uniprot_example.py

# Option 3: Set Python path
export PYTHONPATH=/path/to/project-template:$PYTHONPATH
python examples/uniprot_example.py
```

### 2. ModuleNotFoundError: No module named 'biocypher'

**Problem**: BioCypher is not installed.

**Solutions**:
```bash
# Install all dependencies
poetry install
poetry shell

# Or install BioCypher directly
pip install biocypher==0.10.1
```

### 3. Import errors for specific packages

**Problem**: Missing dependencies like pypath, chembl-webresource-client, etc.

**Solutions**:
```bash
# Install all project dependencies
poetry install

# Or install missing packages individually
pip install pypath-omnipath pandas numpy tqdm pydantic bioregistry requests chembl-webresource-client pronto
```

### 4. Permission errors or download failures

**Problem**: Cannot download data from external sources.

**Solutions**:
```bash
# Check internet connection
ping www.uniprot.org

# Try with cache disabled
export BIOCYPHER_CACHE=false
python examples/uniprot_example.py

# Use test mode for smaller datasets
export BIOCYPHER_TEST_MODE=true
python examples/uniprot_example.py
```

### 5. Memory issues with large datasets

**Problem**: Out of memory errors when processing full datasets.

**Solutions**:
```bash
# Always start with test mode
export BIOCYPHER_TEST_MODE=true
python create_biological_knowledge_graph.py

# Increase system memory or use streaming
# Reduce organism scope (focus on one organism)
# Process adapters individually
```

### 6. Neo4j import issues

**Problem**: Cannot import generated files into Neo4j.

**Solutions**:
```bash
# Check Neo4j is running
neo4j status

# Use Docker setup
docker-compose up -d

# Check file paths in import commands
# Ensure proper file permissions
```

### 7. Slow performance or timeouts

**Problem**: Data download or processing is very slow.

**Solutions**:
```bash
# Use test mode first
export BIOCYPHER_TEST_MODE=true

# Enable caching
export BIOCYPHER_CACHE=true

# Reduce organism scope
# Process one adapter at a time
```

## Quick Setup Verification

Run our setup verification script:

```bash
python setup.py
```

This will check:
- Python version compatibility
- Poetry installation
- Dependency installation
- Import functionality

## Getting Help

1. **Check logs**: Look in `biocypher-log/` directory for detailed error messages
2. **Enable debug mode**: Set `export BIOCYPHER_DEBUG=true`
3. **Run individual adapters**: Test each adapter separately
4. **Use test mode**: Always start with `export BIOCYPHER_TEST_MODE=true`

## Environment Variables

Useful environment variables for troubleshooting:

```bash
# Enable test mode (smaller datasets)
export BIOCYPHER_TEST_MODE=true

# Enable debug logging
export BIOCYPHER_DEBUG=true

# Disable caching
export BIOCYPHER_CACHE=false

# Set custom cache directory
export BIOCYPHER_CACHE_DIR=/path/to/cache

# Set Python path
export PYTHONPATH=/path/to/project-template:$PYTHONPATH
```

## System Requirements

**Minimum for test mode:**
- Python 3.10+
- 4GB RAM
- 1GB disk space
- Internet connection

**Recommended for full datasets:**
- Python 3.10+
- 16GB RAM
- 10GB disk space
- Stable internet connection
- SSD storage

## Example Success Output

When everything works correctly, you should see output like:

```
INFO -- This is BioCypher v0.10.1.
INFO -- Logging into `biocypher-log/biocypher-20250820-213705.log`.
Downloading UniProt data...
📥 Processing UniProt data...
🔍 Generated proteins:
  • uniprot:P04637 (protein): Tumor protein p53
  • uniprot:P53350 (protein): Serine/threonine-protein kinase PLK1
✅ UniProt adapter can provide 2 proteins
Done! Check the output directory for generated files.
```