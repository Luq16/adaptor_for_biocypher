"""
BioCypher adapters for biological data sources.
"""

# Base imports that should always work
from .example_adapter import (
    ExampleAdapter,
    ExampleAdapterNodeType,
    ExampleAdapterEdgeType,
    ExampleAdapterProteinField,
    ExampleAdapterDiseaseField,
)

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

# Optional imports with graceful fallback
_adapters_available = {}

# Try to import each adapter individually
try:
    from .uniprot_adapter import (
        UniprotAdapter,
        UniprotNodeType,
        UniprotNodeField,
        UniprotEdgeType,
    )
    _adapters_available['uniprot'] = True
except ImportError as e:
    print(f"Warning: UniProt adapter not available: {e}")
    _adapters_available['uniprot'] = False

try:
    from .chembl_adapter import (
        ChemblAdapter,
        ChemblNodeType,
        ChemblNodeField,
        ChemblEdgeType,
    )
    _adapters_available['chembl'] = True
except ImportError as e:
    print(f"Warning: ChEMBL adapter not available: {e}")
    _adapters_available['chembl'] = False

try:
    from .disease_adapter import (
        DiseaseOntologyAdapter,
        DiseaseNodeType,
        DiseaseNodeField,
        DiseaseEdgeType,
    )
    _adapters_available['disease'] = True
except ImportError as e:
    print(f"Warning: Disease Ontology adapter not available: {e}")
    _adapters_available['disease'] = False

try:
    from .string_adapter import (
        StringAdapter,
        StringNodeType,
        StringEdgeType,
        StringEdgeField,
    )
    _adapters_available['string'] = True
except ImportError as e:
    print(f"Warning: STRING adapter not available: {e}")
    _adapters_available['string'] = False

try:
    from .go_adapter import (
        GOAdapter,
        GONodeType,
        GONodeField,
        GOEdgeType,
        GOEdgeField,
    )
    _adapters_available['go'] = True
except ImportError as e:
    print(f"Warning: Gene Ontology adapter not available: {e}")
    _adapters_available['go'] = False

try:
    from .reactome_adapter import (
        ReactomeAdapter,
        ReactomeNodeType,
        ReactomeNodeField,
        ReactomeEdgeType,
        ReactomeEdgeField,
    )
    _adapters_available['reactome'] = True
except ImportError as e:
    print(f"Warning: Reactome adapter not available: {e}")
    _adapters_available['reactome'] = False

try:
    from .disgenet_adapter import (
        DisGeNETAdapter,
        DisGeNETNodeType,
        DisGeNETEdgeType,
        DisGeNETEdgeField,
    )
    _adapters_available['disgenet'] = True
except ImportError as e:
    print(f"Warning: DisGeNET adapter not available: {e}")
    _adapters_available['disgenet'] = False

try:
    from .opentargets_adapter import (
        OpenTargetsAdapter,
        OpenTargetsNodeType,
        OpenTargetsEdgeType,
        OpenTargetsEdgeField,
    )
    _adapters_available['opentargets'] = True
except ImportError as e:
    print(f"Warning: OpenTargets adapter not available: {e}")
    _adapters_available['opentargets'] = False

try:
    from .side_effect_adapter import (
        SideEffectAdapter,
        SideEffectNodeType,
        SideEffectNodeField,
        SideEffectEdgeType,
        SideEffectEdgeField,
    )
    _adapters_available['side_effect'] = True
except ImportError as e:
    print(f"Warning: SideEffect adapter not available: {e}")
    _adapters_available['side_effect'] = False

try:
    from .phenotype_adapter import (
        PhenotypeAdapter,
        PhenotypeNodeType,
        PhenotypeNodeField,
        PhenotypeEdgeType,
        PhenotypeEdgeField,
    )
    _adapters_available['phenotype'] = True
except ImportError as e:
    print(f"Warning: Phenotype adapter not available: {e}")
    _adapters_available['phenotype'] = False

try:
    from .orthology_adapter import (
        OrthologyAdapter,
        OrthologyNodeType,
        OrthologyNodeField,
        OrthologyEdgeType,
        OrthologyEdgeField,
    )
    _adapters_available['orthology'] = True
except ImportError as e:
    print(f"Warning: Orthology adapter not available: {e}")
    _adapters_available['orthology'] = False

try:
    from .ppi_adapter import (
        PPIAdapter,
        PPINodeType,
        PPINodeField,
        PPIEdgeType,
        PPIEdgeField,
    )
    _adapters_available['ppi'] = True
except ImportError as e:
    print(f"Warning: PPI adapter not available: {e}")
    _adapters_available['ppi'] = False

# Build __all__ list dynamically based on available adapters
__all__ = [
    # Always available
    "ExampleAdapter",
    "ExampleAdapterNodeType", 
    "ExampleAdapterEdgeType",
    "ExampleAdapterProteinField",
    "ExampleAdapterDiseaseField",
    "BaseAdapter",
    "BaseEnumMeta",
    "DataDownloadMixin",
    "_adapters_available",
]

# Add available adapters to __all__
if _adapters_available.get('uniprot', False):
    __all__.extend([
        "UniprotAdapter", "UniprotNodeType", "UniprotNodeField", "UniprotEdgeType"
    ])

if _adapters_available.get('chembl', False):
    __all__.extend([
        "ChemblAdapter", "ChemblNodeType", "ChemblNodeField", "ChemblEdgeType"
    ])

if _adapters_available.get('disease', False):
    __all__.extend([
        "DiseaseOntologyAdapter", "DiseaseNodeType", "DiseaseNodeField", "DiseaseEdgeType"
    ])

if _adapters_available.get('string', False):
    __all__.extend([
        "StringAdapter", "StringNodeType", "StringEdgeType", "StringEdgeField"
    ])

if _adapters_available.get('go', False):
    __all__.extend([
        "GOAdapter", "GONodeType", "GONodeField", "GOEdgeType", "GOEdgeField"
    ])

if _adapters_available.get('reactome', False):
    __all__.extend([
        "ReactomeAdapter", "ReactomeNodeType", "ReactomeNodeField", "ReactomeEdgeType", "ReactomeEdgeField"
    ])

if _adapters_available.get('disgenet', False):
    __all__.extend([
        "DisGeNETAdapter", "DisGeNETNodeType", "DisGeNETEdgeType", "DisGeNETEdgeField"
    ])

if _adapters_available.get('opentargets', False):
    __all__.extend([
        "OpenTargetsAdapter", "OpenTargetsNodeType", "OpenTargetsEdgeType", "OpenTargetsEdgeField"
    ])

if _adapters_available.get('side_effect', False):
    __all__.extend([
        "SideEffectAdapter", "SideEffectNodeType", "SideEffectNodeField", "SideEffectEdgeType", "SideEffectEdgeField"
    ])

if _adapters_available.get('phenotype', False):
    __all__.extend([
        "PhenotypeAdapter", "PhenotypeNodeType", "PhenotypeNodeField", "PhenotypeEdgeType", "PhenotypeEdgeField"
    ])

if _adapters_available.get('orthology', False):
    __all__.extend([
        "OrthologyAdapter", "OrthologyNodeType", "OrthologyNodeField", "OrthologyEdgeType", "OrthologyEdgeField"
    ])

if _adapters_available.get('ppi', False):
    __all__.extend([
        "PPIAdapter", "PPINodeType", "PPINodeField", "PPIEdgeType", "PPIEdgeField"
    ])

def get_available_adapters():
    """Return a dictionary of available adapters."""
    return _adapters_available.copy()

def list_available_adapters():
    """Print available adapters."""
    print("Available adapters:")
    for adapter, available in _adapters_available.items():
        status = "✅" if available else "❌"
        print(f"  {status} {adapter}")

__all__.extend(["get_available_adapters", "list_available_adapters"])