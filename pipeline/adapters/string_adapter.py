from enum import Enum, auto
from typing import Optional, Generator, Union
from biocypher._logger import logger
import pandas as pd
import requests
import gzip
import io
from tqdm import tqdm
import os

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
    BASE_URL = "https://stringdb-downloads.org/download"
    VERSION = "v12.5"  # Update as needed
    FALLBACK_VERSIONS = ["v12.0", "v11.5", "v11.0"]  # Fallback versions to try
    
    def __init__(
        self,
        organism: str = "9606",  # Human by default
        node_types: Optional[list[StringNodeType]] = None,
        edge_types: Optional[list[StringEdgeType]] = None,
        edge_fields: Optional[list[StringEdgeField]] = None,
        score_threshold: float = 0.4,  # Default STRING confidence threshold
        physical_interaction_threshold: float = 0.7,  # Threshold for physical interactions
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
        self.physical_interaction_threshold = physical_interaction_threshold
        
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
        Download STRING data files.
        
        Args:
            force_download: Force re-download even if cached
        """
        with self.timer("Downloading STRING data"):
            # Download protein links (interactions)
            self._download_protein_links(force_download)
            
            # Download protein info (optional, for standalone use)
            if self.node_types:
                self._download_protein_info(force_download)
    
    def _download_protein_links(self, force_download: bool = False):
        """
        Download protein-protein interaction data from STRING.
        """
        logger.info("Downloading STRING protein links")
        
        # Try different versions to find working download
        versions_to_try = [self.VERSION] + self.FALLBACK_VERSIONS
        filepath = None
        
        for version in versions_to_try:
            try:
                # Construct URL for protein links file
                filename = f"{self.organism}.protein.links.full.{version.replace('.', '_')}.txt.gz"
                url = f"{self.BASE_URL}/protein.links.full/{version}/{filename}"
                
                # Download file
                local_filename = f"string_links_{self.organism}.txt.gz"
                logger.info(f"Trying STRING version {version}: {url}")
                filepath = self.download_file(url, local_filename, force_download)
                logger.info(f"Successfully downloaded STRING data from version {version}")
                break
                
            except Exception as e:
                logger.warning(f"Failed to download STRING version {version}: {str(e)}")
                if version == versions_to_try[-1]:  # Last version
                    logger.error("All STRING versions failed to download")
                    raise RuntimeError(f"Cannot download STRING data. All versions failed. Last error: {str(e)}")
                continue
        
        # Read the gzipped file
        logger.info("Reading STRING interactions file")
        
        # Define column names based on STRING format
        columns = [
            'protein1', 'protein2',
            'neighborhood', 'fusion', 'cooccurrence',
            'coexpression', 'experimental', 'database',
            'textmining', 'combined_score'
        ]
        
        # Read with appropriate settings
        if self.test_mode:
            # Read only first 10000 interactions in test mode
            self.interactions = pd.read_csv(
                filepath,
                compression='gzip',
                sep=' ',
                nrows=10000,
                names=columns,
                skiprows=1
            )
        else:
            # Read full file
            self.interactions = pd.read_csv(
                filepath,
                compression='gzip',
                sep=' ',
                names=columns,
                skiprows=1
            )
        
        # Add additional score columns if present in newer versions
        if 'physical' not in self.interactions.columns:
            # Calculate physical score from experimental and database evidence
            self.interactions['physical'] = (
                self.interactions['experimental'] + self.interactions['database']
            ) / 2
        
        if 'functional' not in self.interactions.columns:
            # Calculate functional score from other evidence channels
            self.interactions['functional'] = (
                self.interactions['neighborhood'] + 
                self.interactions['fusion'] +
                self.interactions['cooccurrence'] +
                self.interactions['coexpression'] +
                self.interactions['textmining']
            ) / 5
        
        # Filter by score threshold
        original_count = len(self.interactions)
        self.interactions = self.interactions[
            self.interactions['combined_score'] >= (self.score_threshold * 1000)
        ]
        
        logger.info(
            f"Loaded {len(self.interactions)} interactions "
            f"(filtered from {original_count} by score >= {self.score_threshold})"
        )
    
    def _download_protein_info(self, force_download: bool = False):
        """
        Download protein information from STRING (optional).
        """
        logger.info("Downloading STRING protein info")
        
        # Construct URL for protein info file
        filename = f"{self.organism}.protein.info.{self.VERSION.replace('.', '_')}.txt.gz"
        url = f"{self.BASE_URL}/protein.info/{self.VERSION}/{filename}"
        
        # Download file
        local_filename = f"string_info_{self.organism}.txt.gz"
        filepath = self.download_file(url, local_filename, force_download)
        
        # Read the file
        protein_info_df = pd.read_csv(filepath, compression='gzip', sep='\t')
        
        # Convert to dictionary for easier access
        self.protein_info = {}
        for _, row in protein_info_df.iterrows():
            protein_id = row['protein_external_id']
            self.protein_info[protein_id] = {
                'preferred_name': row.get('preferred_name', ''),
                'protein_size': row.get('protein_size', 0),
                'annotation': row.get('annotation', ''),
            }
        
        logger.info(f"Loaded info for {len(self.protein_info)} proteins")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield protein nodes (only if explicitly requested).
        
        Note: Usually proteins should come from UniProt adapter instead.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        if not self.node_types:
            logger.info("No node types requested for STRING adapter")
            return
        
        if not self.protein_info:
            logger.warning("No protein info loaded. Call download_data() first.")
            return
        
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
        Yield protein-protein interaction edges.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        if self.interactions.empty:
            logger.warning("No interaction data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.interactions)} interaction edges")
        
        # Process interactions
        for _, interaction in tqdm(self.interactions.iterrows(), 
                                   total=len(self.interactions),
                                   desc="Generating interaction edges"):
            
            # Extract protein IDs
            protein1_string = interaction['protein1']
            protein2_string = interaction['protein2']
            
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
            
            # Determine edge type
            edge_label = self._determine_edge_type(interaction)
            
            # Skip if edge type not requested
            if edge_label == "protein_physical_interaction" and \
               StringEdgeType.PHYSICAL_INTERACTION not in self.edge_types:
                continue
            elif edge_label == "protein_functional_association" and \
                 StringEdgeType.FUNCTIONAL_ASSOCIATION not in self.edge_types:
                continue
            elif edge_label == "protein_protein_interaction" and \
                 StringEdgeType.PROTEIN_PROTEIN_INTERACTION not in self.edge_types:
                continue
            
            # Build edge properties
            properties = self._get_edge_properties(interaction)
            
            yield (None, source_id, target_id, edge_label, properties)
    
    def _extract_uniprot_id(self, string_id: str) -> Optional[str]:
        """
        Extract UniProt ID from STRING protein ID.
        
        STRING uses Ensembl protein IDs prefixed with organism.
        This is a simplified extraction - in production, use proper ID mapping.
        """
        # Remove organism prefix (e.g., "9606.ENSP00000000233" -> "ENSP00000000233")
        if '.' in string_id:
            _, protein_part = string_id.split('.', 1)
            
            # For this example, we'll return the Ensembl ID
            # In production, you'd map this to UniProt using a mapping file
            return protein_part
        
        return None
    
    def _determine_edge_type(self, interaction: pd.Series) -> str:
        """
        Determine the type of interaction based on scores.
        """
        physical_score = interaction.get('physical', 0)
        
        # High physical score indicates physical interaction
        if physical_score >= (self.physical_interaction_threshold * 1000):
            return "protein_physical_interaction"
        
        # High combined score but low physical indicates functional association
        elif interaction['combined_score'] >= 700:  # 0.7 threshold
            return "protein_functional_association"
        
        # Default to generic interaction
        else:
            return "protein_protein_interaction"
    
    def _get_edge_properties(self, interaction: pd.Series) -> dict:
        """
        Extract edge properties from interaction data.
        """
        properties = self.get_metadata_dict()
        
        # Add score fields
        score_fields = [
            StringEdgeField.COMBINED_SCORE,
            StringEdgeField.PHYSICAL_SCORE,
            StringEdgeField.FUNCTIONAL_SCORE,
            StringEdgeField.NEIGHBORHOOD_SCORE,
            StringEdgeField.FUSION_SCORE,
            StringEdgeField.COOCCURRENCE_SCORE,
            StringEdgeField.COEXPRESSION_SCORE,
            StringEdgeField.EXPERIMENTAL_SCORE,
            StringEdgeField.DATABASE_SCORE,
            StringEdgeField.TEXTMINING_SCORE,
        ]
        
        for field in score_fields:
            if field in self.edge_fields:
                field_name = field.value
                if field_name in interaction:
                    # Normalize scores to 0-1 range
                    properties[field_name] = interaction[field_name] / 1000.0
        
        # Add interaction type
        properties['interaction_type'] = self._determine_edge_type(interaction)
        
        # Add evidence summary
        evidence_types = []
        if interaction.get('experimental', 0) > 0:
            evidence_types.append('experimental')
        if interaction.get('database', 0) > 0:
            evidence_types.append('database')
        if interaction.get('textmining', 0) > 0:
            evidence_types.append('textmining')
        if interaction.get('coexpression', 0) > 0:
            evidence_types.append('coexpression')
        
        properties['evidence_types'] = evidence_types
        
        return properties
    
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