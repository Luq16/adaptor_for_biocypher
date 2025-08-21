# Quick Start Guide

## ✅ What's Working Right Now

Your BioCypher project is **successfully set up** and working! Here's how to get started:

### 1. Test Basic Functionality (Working Now)

```bash
# Navigate to your project
cd /Users/luqmanawoniyi_1/Documents/biocypher/project-template

# Run the working example
poetry run python simple_example.py
```

**Expected Output:**
```
🧬 Simple BioCypher Example
========================================
✅ BioCypher initialized successfully
✅ Example adapter created successfully
✅ Generated 200 nodes and 27 edges
✅ Data written to BioCypher
🎉 Success! BioCypher is working correctly.
```

### 2. Explore Generated Files

After running the example, check these files:
```bash
ls -la *.csv                    # Node and edge CSV files
ls -la biocypher-log/          # Detailed logs
cat biocypher_import_call.sh   # Neo4j import script
```

### 3. Understanding the Project Structure

```
project-template/
├── simple_example.py              # ✅ Working example
├── template_package/adapters/     # All adapter implementations  
│   ├── example_adapter.py         # ✅ Working synthetic data
│   ├── uniprot_adapter.py         # ⚠️ Real data (dependency issue)
│   ├── chembl_adapter.py          # ⚠️ Real data (dependency issue)
│   └── ...                        # More real data adapters
├── config/                        # BioCypher configuration
├── examples/                      # Usage examples
└── STATUS_REPORT.md               # Detailed status
```

## 🔧 Fix Real Data Adapters (Optional)

The real data adapters are implemented but have a dependency issue. To fix:

### Option 1: Quick Fix (Recommended)
```bash
# Try downgrading paramiko
poetry add "paramiko==2.12.0"
poetry run python examples/uniprot_example.py
```

### Option 2: Alternative Approach
Create adapters that don't use pypath:
```python
# Use direct API calls instead of pypath
import requests
import pandas as pd
```

## 🚀 Next Steps

### For Immediate Use
1. **Use the working example** to understand BioCypher patterns
2. **Develop custom adapters** using the base classes
3. **Import generated data** into Neo4j using the provided scripts

### For Production Use
1. **Fix dependency issues** (see options above)
2. **Test real data adapters** with small datasets first
3. **Configure schemas** for your specific use case

## 📖 Learning Resources

### Key Files to Study
- `simple_example.py` - Working BioCypher integration
- `template_package/adapters/base_adapter.py` - Adapter pattern
- `template_package/adapters/example_adapter.py` - Synthetic data generation
- `config/schema_config.yaml` - Knowledge graph schema

### Available Adapters (Once Dependencies Fixed)
- **UniProt**: Proteins, genes, organisms (20K+ proteins)
- **ChEMBL**: Drugs, compounds, targets (2K+ drugs)  
- **Disease Ontology**: Disease classifications (10K+ diseases)
- **STRING**: Protein interactions (millions of interactions)
- **Gene Ontology**: Functional annotations (45K+ terms)
- **Reactome**: Biological pathways (2.5K+ pathways)
- **DisGeNET**: Gene-disease associations (1M+ associations)

## 🎯 Success Confirmation

Run this to confirm everything is working:

```bash
poetry run python simple_example.py
```

If you see "🎉 Success! BioCypher is working correctly", you're ready to:
- ✅ Build knowledge graphs with BioCypher
- ✅ Develop custom data adapters  
- ✅ Process biological data at scale
- ✅ Generate Neo4j-compatible datasets

The foundation is solid - you now have a working BioCypher template with comprehensive adapter infrastructure!