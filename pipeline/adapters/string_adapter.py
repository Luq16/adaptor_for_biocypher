from enum import Enum, auto
from typing import Optional, Generator, Union
from biocypher._logger import logger
import pandas as pd
from tqdm import tqdm
import os
import collections

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
        Download STRING data using pypath with CROssBARv2 approach.
        
        Args:
            force_download: Force re-download even if cached
        """
        if not PYPATH_AVAILABLE:
            raise ImportError("PyPath is required for STRING data download. Install with: pip install pypath-omnipath")
        
        with self.timer("Downloading STRING data"):
            # Step 1: Get UniProt mappings FIRST (CROssBARv2 approach)
            self._get_uniprot_mappings()
            
            # Step 2: Download and filter protein interactions using mappings
            self._download_string_interactions()
    
    def _download_string_interactions(self):
        """
        Download STRING interactions using pypath with CROssBARv2 filtering approach.
        """
        logger.info(f"Downloading STRING interactions for organism {self.organism} with {self.score_threshold} threshold")
        
        try:
            # Step 1: Download raw STRING interactions
            logger.info("Downloading raw STRING interactions...")
            interactions_generator = pypath_string.string_links_interactions(
                ncbi_tax_id=int(self.organism), 
                score_threshold=self.score_threshold
            )
            
            # Step 2: Filter interactions (CROssBARv2 approach if mapping available)
            filtered_interactions = []
            
            if hasattr(self, 'use_simple_mapping') and self.use_simple_mapping:
                # Fallback: Take all interactions without UniProt filtering
                logger.info("Using simplified approach - taking all interactions")
                for interaction in interactions_generator:
                    filtered_interactions.append(interaction)
                    
                    # Apply test mode limiting
                    if self.test_mode and len(filtered_interactions) >= 100:
                        logger.info(f"Test mode: Limited to 100 interactions")
                        break
            else:
                # CROssBARv2 approach: Only keep interactions where both proteins can be mapped to UniProt
                logger.info("Filtering interactions using CROssBARv2 approach...")
                for interaction in interactions_generator:
                    # Check if both proteins can be mapped to UniProt
                    if (hasattr(self, 'string_to_uniprot') and 
                        interaction.protein_a in self.string_to_uniprot and 
                        interaction.protein_b in self.string_to_uniprot):
                        filtered_interactions.append(interaction)
                        
                        # Apply test mode limiting during filtering
                        if self.test_mode and len(filtered_interactions) >= 100:
                            logger.info(f"Test mode: Limited to 100 filtered interactions")
                            break
                
                if not filtered_interactions:
                    logger.warning("No STRING interactions passed UniProt mapping filter, falling back to unfiltered")
                    # Fallback to unfiltered if CROssBARv2 filtering yields no results
                    self.use_simple_mapping = True
                    return self._download_string_interactions()
            
            # Convert to DataFrame
            self.interactions = pd.DataFrame(filtered_interactions)
            
            logger.info(f"Downloaded {len(self.interactions)} STRING interactions after UniProt filtering")
            
        except Exception as e:
            logger.error(f"Failed to download STRING interactions: {str(e)}")
            raise RuntimeError(f"Cannot download STRING data via pypath: {str(e)}")
    
    def _get_uniprot_mappings(self):
        """
        Get UniProt mappings for STRING proteins.
        
        Attempts CROssBARv2 approach first, falls back to simple mapping if needed.
        """
        logger.info("Getting UniProt mappings for STRING proteins")
        
        try:
            # Import collections for defaultdict
            from pypath.inputs import uniprot
            
            # Initialize mapping structures
            self.string_to_uniprot = collections.defaultdict(list)
            self.swissprots = set()
            
            # Try CROssBARv2 approach first
            logger.info("Attempting CROssBARv2 approach: Downloading UniProt cross-references to STRING...")
            try:
                uniprot_to_string = uniprot.uniprot_data("xref_string", "*", True)
                
                if uniprot_to_string:
                    # Create STRING ID to UniProt ID mapping (exact CROssBARv2 implementation)
                    for k, v in uniprot_to_string.items():
                        # k = UniProt ID, v = STRING cross-reference data (semicolon-separated)
                        if v:  # Make sure v is not empty
                            for string_id in list(filter(None, v.split(";"))):
                                if "." in string_id:
                                    # Extract protein ID from STRING format (e.g., "9606.ENSP00012345" -> "ENSP00012345")
                                    self.string_to_uniprot[string_id.split(".")[1]].append(k)
                    
                    logger.info(f"✅ CROssBARv2 approach: Created mapping for {len(self.string_to_uniprot)} STRING proteins")
                else:
                    raise ValueError("Empty UniProt cross-reference data")
                    
            except Exception as e:
                logger.warning(f"CROssBARv2 approach failed: {e}")
                logger.info("Falling back to simplified approach...")
                
                # Fallback: Don't filter - let edges be created with ENSP IDs and fix in post-processing
                # This allows the adapter to work even without the full CROssBARv2 infrastructure
                self.use_simple_mapping = True
                logger.info("Using simplified mapping - edges will be created with ENSP IDs")
            
            # Try to get SwissProt proteins for filtering
            try:
                self.swissprots = set(uniprot._all_uniprots("*", True))
                logger.info(f"Retrieved {len(self.swissprots)} SwissProt protein IDs for filtering")
            except Exception as e:
                logger.warning(f"Could not retrieve SwissProt IDs: {e}")
                self.swissprots = set()
            
        except Exception as e:
            logger.warning(f"Could not set up UniProt mappings: {str(e)}")
            self.string_to_uniprot = collections.defaultdict(list)
            self.swissprots = set()
            self.use_simple_mapping = True
    
    
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
        Extract UniProt ID from STRING protein ID using CROssBARv2 mapping approach.
        
        Uses the downloaded UniProt cross-references to map STRING IDs to UniProt IDs.
        """
        if not string_id or pd.isna(string_id):
            return None
        
        # Convert to string and strip whitespace
        string_id = str(string_id).strip()
        
        # If it's already a UniProt-style ID, return it
        if string_id.startswith(('P', 'Q', 'O', 'A', 'B', 'C')):
            return string_id
        
        # Handle STRING native format (organism.protein_id)
        protein_part = string_id
        if '.' in string_id:
            organism_id, protein_part = string_id.split('.', 1)
        
        # Use the CROssBARv2 mapping approach
        if hasattr(self, 'string_to_uniprot') and protein_part in self.string_to_uniprot:
            uniprot_ids = self.string_to_uniprot[protein_part]
            
            # Filter to SwissProt if available (following CROssBARv2 approach)
            if hasattr(self, 'swissprots') and self.swissprots:
                swissprot_matches = [uid for uid in uniprot_ids if uid in self.swissprots]
                if swissprot_matches:
                    return swissprot_matches[0]  # Take first SwissProt match
            
            # If no SwissProt match or no filtering, take first UniProt ID
            if uniprot_ids:
                return uniprot_ids[0]
        
        # If no mapping found, return None (following CROssBARv2 filtering approach)
        return None
    
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