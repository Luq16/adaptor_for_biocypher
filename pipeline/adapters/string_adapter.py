from enum import Enum, auto
from typing import Optional, Generator, Union
from biocypher._logger import logger
import pandas as pd
from tqdm import tqdm
import os

# Use pypath for STRING data download (like CROssBARv2 implementation)
try:
    from pypath.inputs import string as pypath_string
    from pypath import omnipath
    PYPATH_AVAILABLE = True
    logger.info("PyPath available for STRING data download")
except ImportError:
    PYPATH_AVAILABLE = False
    logger.warning("PyPath not available, falling back to manual downloads")
    import requests
    import gzip
    import io

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

logger.debug(f"Loading module {__name__}.")


class StringNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the STRING adapter.
    Note: STRING primarily provides edges, nodes should come from UniProt adapter.
    """
    PROTEIN = auto()  # Only if creating standalone protein nodes


class StringEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the STRING adapter.
    """
    PROTEIN_PROTEIN_INTERACTION = auto()
    PHYSICAL_INTERACTION = auto()
    FUNCTIONAL_ASSOCIATION = auto()


class StringEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for STRING edges.
    """
    # Score fields
    COMBINED_SCORE = "combined_score"
    PHYSICAL_SCORE = "physical"
    FUNCTIONAL_SCORE = "functional"
    
    # Evidence channel scores
    NEIGHBORHOOD_SCORE = "neighborhood"
    FUSION_SCORE = "fusion"
    COOCCURRENCE_SCORE = "cooccurrence"
    COEXPRESSION_SCORE = "coexpression"
    EXPERIMENTAL_SCORE = "experimental"
    DATABASE_SCORE = "database"
    TEXTMINING_SCORE = "textmining"
    
    # Additional fields
    HOMOLOGY_SCORE = "homology"


class StringAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for STRING protein-protein interaction data.
    
    STRING database provides known and predicted protein-protein interactions.
    """
    
    # STRING download URLs
    BASE_URL = "https://stringdb-static.org/download"
    VERSION = "v11.5"  # Latest stable version
    FALLBACK_VERSIONS = ["v11.0", "v10.5"]  # Fallback versions to try
    
    def __init__(
        self,
        organism: str = "9606",  # Human by default
        node_types: Optional[list[StringNodeType]] = None,
        edge_types: Optional[list[StringEdgeType]] = None,
        edge_fields: Optional[list[StringEdgeField]] = None,
        score_threshold: str = "high_confidence",  # Use STRING's predefined thresholds
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = "string"
        self.data_version = self.VERSION
        self.data_licence = "CC BY 4.0"
        
        # Parameters
        self.organism = organism
        self.score_threshold = score_threshold
        
        # Configure fields
        self.node_types = node_types or []  # Usually empty, as proteins come from UniProt
        self.edge_types = edge_types or list(StringEdgeType)
        self.edge_fields = edge_fields or list(StringEdgeField)
        
        # Storage for data
        self.protein_info = {}
        self.interactions = pd.DataFrame()
        
        logger.info(f"Initialized STRING adapter for organism {organism}")
    
    def download_data(self, force_download: bool = False):
        """
        Download STRING data using pypath.
        
        Args:
            force_download: Force re-download even if cached
        """
        if not PYPATH_AVAILABLE:
            raise ImportError("PyPath is required for STRING data download. Install with: pip install pypath-omnipath")
        
        with self.timer("Downloading STRING data"):
            # Download protein interactions using pypath
            self._download_string_interactions()
            
            # Get UniProt mappings
            self._get_uniprot_mappings()
    
    def _download_string_interactions(self):
        """
        Download STRING interactions using pypath (like CROssBARv2).
        """
        logger.info(f"Downloading STRING interactions for organism {self.organism} with {self.score_threshold} threshold")
        
        try:
            # Use pypath to download STRING data with predefined threshold
            # This follows the CROssBARv2 approach exactly
            interactions_generator = pypath_string.string_links_interactions(
                ncbi_tax_id=int(self.organism), 
                score_threshold=self.score_threshold
            )
            
            # Convert generator to list and then to DataFrame
            interactions_list = list(interactions_generator)
            
            if not interactions_list:
                raise ValueError("No STRING interactions downloaded")
            
            # Convert to DataFrame
            # PyPath returns named tuples or similar objects
            self.interactions = pd.DataFrame(interactions_list)
            
            # Apply test mode limiting if needed
            if self.test_mode and len(self.interactions) > 100:
                self.interactions = self.interactions.head(100)
                logger.info(f"Test mode: Limited to 100 interactions")
            
            logger.info(f"Downloaded {len(self.interactions)} STRING interactions with {self.score_threshold} confidence")
            
        except Exception as e:
            logger.error(f"Failed to download STRING interactions: {str(e)}")
            raise RuntimeError(f"Cannot download STRING data via pypath: {str(e)}")
    
    def _get_uniprot_mappings(self):
        """
        Get UniProt mappings for STRING proteins.
        """
        logger.info("Getting UniProt mappings for STRING proteins")
        
        try:
            # Get unique protein IDs from interactions
            protein_ids = set()
            if not self.interactions.empty:
                # Get all protein IDs from both columns
                for col in ['protein_a', 'protein_b', 'source', 'target']:  # Handle different possible column names
                    if col in self.interactions.columns:
                        protein_ids.update(self.interactions[col].unique())
            
            logger.info(f"Found {len(protein_ids)} unique STRING protein IDs")
            
            # Store for later use in ID conversion
            self.string_protein_ids = protein_ids
            
        except Exception as e:
            logger.warning(f"Could not get UniProt mappings: {str(e)}")
            self.string_protein_ids = set()
    
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield protein nodes (only if explicitly requested).
        
        Note: Usually proteins should come from UniProt adapter instead.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        if not self.node_types:
            logger.info("No node types requested for STRING adapter")
            # Return empty generator that doesn't cause StopIteration
            return
            yield  # Unreachable but makes this a generator
        
        if not self.protein_info:
            logger.warning("No protein info loaded. Call download_data() first.")
            return
            yield  # Unreachable but makes this a generator
        
        logger.info(f"Generating {len(self.protein_info)} protein nodes from STRING")
        
        for protein_string_id, info in tqdm(self.protein_info.items(), desc="Generating protein nodes"):
            # Extract UniProt ID from STRING ID (format: 9606.ENSP00000000233)
            uniprot_id = self._extract_uniprot_id(protein_string_id)
            
            if uniprot_id:
                properties = self.get_metadata_dict()
                properties.update({
                    'string_id': protein_string_id,
                    'preferred_name': info['preferred_name'],
                    'protein_size': info['protein_size'],
                    'annotation': info['annotation'],
                })
                
                prefixed_id = self.add_prefix_to_id("uniprot", uniprot_id)
                yield (prefixed_id, "protein", properties)
    
    def get_edges(self) -> Generator[tuple[None, str, str, str, dict], None, None]:
        """
        Yield protein-protein interaction edges from pypath STRING data.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        if self.interactions.empty:
            logger.warning("No interaction data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.interactions)} interaction edges")
        logger.info(f"Available columns: {list(self.interactions.columns)}")
        
        # Determine column names from pypath output
        # Common pypath column names for STRING data
        source_col = None
        target_col = None
        score_col = None
        
        for col in self.interactions.columns:
            if col.lower() in ['source', 'protein_a', 'protein1']:
                source_col = col
            elif col.lower() in ['target', 'protein_b', 'protein2']:
                target_col = col
            elif col.lower() in ['combined_score', 'score']:
                score_col = col
        
        if not source_col or not target_col:
            logger.error(f"Could not find source/target columns in: {list(self.interactions.columns)}")
            return
        
        # Process interactions
        for _, interaction in tqdm(self.interactions.iterrows(), 
                                   total=len(self.interactions),
                                   desc="Generating interaction edges"):
            
            # Extract protein IDs
            protein1_string = interaction[source_col]
            protein2_string = interaction[target_col]
            
            # Convert STRING IDs to UniProt IDs  
            protein1_id = self._extract_uniprot_id(protein1_string)
            protein2_id = self._extract_uniprot_id(protein2_string)
            
            if not protein1_id or not protein2_id:
                continue
            
            # Skip self-interactions
            if protein1_id == protein2_id:
                continue
            
            # Create node IDs
            source_id = self.add_prefix_to_id("uniprot", protein1_id)
            target_id = self.add_prefix_to_id("uniprot", protein2_id)
            
            # Use generic protein interaction edge type
            edge_label = "protein_protein_interaction"
            
            # Skip if edge type not requested
            if StringEdgeType.PROTEIN_PROTEIN_INTERACTION not in self.edge_types:
                continue
            
            # Build edge properties
            properties = self._get_edge_properties(interaction, score_col)
            
            yield (None, source_id, target_id, edge_label, properties)
    
    def _extract_uniprot_id(self, string_id: str) -> Optional[str]:
        """
        Extract UniProt ID from STRING protein ID using pypath approach.
        
        PyPath STRING data may already include proper UniProt mappings,
        or we need to handle STRING native identifiers appropriately.
        """
        if not string_id or pd.isna(string_id):
            return None
        
        # Convert to string and strip whitespace
        string_id = str(string_id).strip()
        
        # If it's already a UniProt-style ID, return it
        if string_id.startswith(('P', 'Q', 'O', 'A', 'B', 'C')):
            return string_id
        
        # Handle STRING native format (organism.protein_id)
        if '.' in string_id:
            organism_id, protein_id = string_id.split('.', 1)
            # For human (9606), return the protein part directly
            # PyPath may handle the mapping internally
            return protein_id
        
        # Return as-is for other formats
        return string_id
    
    def _get_edge_properties(self, interaction: pd.Series, score_col: Optional[str] = None) -> dict:
        """
        Extract edge properties from pypath interaction data.
        """
        properties = self.get_metadata_dict()
        
        # Add score information
        if score_col and score_col in interaction:
            # PyPath already applies the threshold, so scores should be high confidence
            properties['string_combined_score'] = float(interaction[score_col]) 
            properties['confidence'] = self.score_threshold
        
        # Add all available fields from the interaction
        for col, value in interaction.items():
            if col not in [self._get_source_col(), self._get_target_col()] and pd.notna(value):
                # Clean column name for property
                clean_col = col.lower().replace(' ', '_')
                properties[f'string_{clean_col}'] = value
        
        return properties
    
    def _get_source_col(self) -> Optional[str]:
        """Get the source column name from interactions dataframe."""
        for col in self.interactions.columns:
            if col.lower() in ['source', 'protein_a', 'protein1']:
                return col
        return None
    
    def _get_target_col(self) -> Optional[str]:
        """Get the target column name from interactions dataframe."""
        for col in self.interactions.columns:
            if col.lower() in ['target', 'protein_b', 'protein2']:
                return col
        return None
    
    def get_id_mapping(self, mapping_file: Optional[str] = None) -> dict:
        """
        Get STRING to UniProt ID mapping.
        
        In production, this would download and parse the STRING aliases file
        to properly map STRING IDs to UniProt accessions.
        """
        if mapping_file:
            # Read mapping file if provided
            mapping_df = pd.read_csv(mapping_file, sep='\t')
            # Process mapping...
            pass
        
        # For now, return empty mapping
        # In production, download from STRING aliases file
        return {}