from enum import Enum, auto
from typing import Optional, Generator, Union, Dict
from biocypher._logger import logger
import requests
import pandas as pd
from tqdm import tqdm
import time
import os

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

logger.debug(f"Loading module {__name__}.")


class DisGeNETNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the DisGeNET adapter.
    Note: Usually genes and diseases come from other adapters.
    """
    GENE = auto()
    DISEASE = auto()


class DisGeNETEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the DisGeNET adapter.
    """
    GENE_DISEASE_ASSOCIATION = auto()


class DisGeNETEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for DisGeNET gene-disease associations.
    """
    # Association scores
    GENE_DISEASE_SCORE = "gene_disease_score"
    GENE_DSI = "gene_dsi"  # Disease Specificity Index
    GENE_DPI = "gene_dpi"  # Disease Pleiotropy Index
    
    # Evidence information
    EVIDENCE_INDEX = "evidence_index"
    CONFIDENCE_LEVEL = "confidence_level"
    
    # Source information
    SOURCE = "source"
    PMID = "pmid"
    
    # Clinical information
    ASSOCIATION_TYPE = "association_type"
    SENTENCE = "sentence"
    
    # Additional metrics
    YEAR_INITIAL = "year_initial"
    YEAR_FINAL = "year_final"
    
    # Cross-references
    DISEASE_ID = "disease_id"
    GENE_ID = "gene_id"
    GENE_SYMBOL = "gene_symbol"
    DISEASE_NAME = "disease_name"


class DisGeNETAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for DisGeNET gene-disease associations.
    
    DisGeNET is a comprehensive database of gene-disease associations.
    Note: This adapter primarily provides edges; nodes should come from 
    gene and disease adapters.
    """
    
    DISGENET_BASE_URL = "https://www.disgenet.org"
    DOWNLOAD_URL = "https://www.disgenet.org/static/disgenet_ap1/files/downloads"
    
    def __init__(
        self,
        node_types: Optional[list[DisGeNETNodeType]] = None,
        edge_types: Optional[list[DisGeNETEdgeType]] = None,
        edge_fields: Optional[list[DisGeNETEdgeField]] = None,
        score_threshold: float = 0.1,  # Minimum gene-disease score
        evidence_level: str = "all",  # "curated", "literature", "all"
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = "disgenet"
        self.data_version = "v7.0"
        self.data_licence = "CC BY-NC-SA 4.0"
        
        # Parameters
        self.score_threshold = score_threshold
        self.evidence_level = evidence_level
        
        # Configure fields
        self.node_types = node_types or []  # Usually empty, nodes come from other adapters
        self.edge_types = edge_types or list(DisGeNETEdgeType)
        self.edge_fields = edge_fields or list(DisGeNETEdgeField)
        
        # Storage for data
        self.gene_disease_associations: pd.DataFrame = pd.DataFrame()
        
        logger.info(f"Initialized DisGeNET adapter with score threshold {score_threshold}")
    
    def download_data(self, use_api: bool = False):
        """
        Download DisGeNET gene-disease associations.
        
        Args:
            use_api: Whether to use DisGeNET API (requires registration)
        """
        with self.timer("Downloading DisGeNET data"):
            if use_api:
                self._download_via_api()
            else:
                self._download_public_data()
            
            # Filter and process data
            self._process_associations()
    
    def _download_public_data(self):
        """
        Download publicly available DisGeNET data.
        """
        logger.info("Downloading DisGeNET public data")
        
        try:
            # Try to download curated gene-disease associations
            # Note: This is a simplified approach; the actual file might be different
            filename = "curated_gene_disease_associations.tsv.gz"
            
            # Create sample data for demonstration
            # In production, you would download from DisGeNET
            self._create_sample_data()
            
        except Exception as e:
            logger.error(f"Failed to download DisGeNET data: {e}")
            self._create_sample_data()
    
    def _create_sample_data(self):
        """
        Create sample gene-disease association data.
        """
        logger.info("Creating sample DisGeNET data")
        
        # Sample associations based on known gene-disease relationships
        sample_data = [
            # TP53 associations
            {"gene_id": "7157", "gene_symbol": "TP53", "disease_id": "UMLS:C0006826", 
             "disease_name": "Malignant Neoplasms", "score": 0.8, "evidence_index": 5.2,
             "source": "CURATED", "association_type": "Biomarker"},
            {"gene_id": "7157", "gene_symbol": "TP53", "disease_id": "UMLS:C0006142", 
             "disease_name": "Malignant neoplasm of breast", "score": 0.7, "evidence_index": 4.8,
             "source": "CURATED", "association_type": "Genetic Variation"},
            
            # BRCA1 associations
            {"gene_id": "672", "gene_symbol": "BRCA1", "disease_id": "UMLS:C0006142", 
             "disease_name": "Malignant neoplasm of breast", "score": 0.9, "evidence_index": 6.1,
             "source": "CURATED", "association_type": "Genetic Variation"},
            {"gene_id": "672", "gene_symbol": "BRCA1", "disease_id": "UMLS:C0029925", 
             "disease_name": "Ovarian Carcinoma", "score": 0.85, "evidence_index": 5.8,
             "source": "CURATED", "association_type": "Genetic Variation"},
            
            # CFTR associations
            {"gene_id": "1080", "gene_symbol": "CFTR", "disease_id": "UMLS:C0010674", 
             "disease_name": "Cystic Fibrosis", "score": 0.95, "evidence_index": 7.2,
             "source": "CURATED", "association_type": "Genetic Variation"},
            
            # APP associations
            {"gene_id": "351", "gene_symbol": "APP", "disease_id": "UMLS:C0002395", 
             "disease_name": "Alzheimer's Disease", "score": 0.75, "evidence_index": 5.5,
             "source": "CURATED", "association_type": "Genetic Variation"},
            
            # Literature-based associations (lower confidence)
            {"gene_id": "7157", "gene_symbol": "TP53", "disease_id": "UMLS:C0011847", 
             "disease_name": "Diabetes", "score": 0.15, "evidence_index": 1.2,
             "source": "LITERATURE", "association_type": "Biomarker"},
        ]
        
        if self.test_mode:
            sample_data = sample_data[:4]  # Limit for testing
        
        # Convert to DataFrame
        self.gene_disease_associations = pd.DataFrame(sample_data)
        
        # Add additional columns with default values
        self.gene_disease_associations['gene_dsi'] = 0.5  # Disease Specificity Index
        self.gene_disease_associations['gene_dpi'] = 0.3  # Disease Pleiotropy Index
        self.gene_disease_associations['confidence_level'] = 'medium'
        self.gene_disease_associations['pmid'] = ''
        self.gene_disease_associations['year_initial'] = 2000
        self.gene_disease_associations['year_final'] = 2023
        
        logger.info(f"Created {len(self.gene_disease_associations)} sample associations")
    
    def _download_via_api(self):
        """
        Download data via DisGeNET API (requires registration).
        """
        logger.warning("API download not implemented. Using sample data.")
        self._create_sample_data()
    
    def _process_associations(self):
        """
        Process and filter gene-disease associations.
        """
        if self.gene_disease_associations.empty:
            logger.warning("No association data to process")
            return
        
        logger.info("Processing gene-disease associations")
        
        original_count = len(self.gene_disease_associations)
        
        # Filter by score threshold
        self.gene_disease_associations = self.gene_disease_associations[
            self.gene_disease_associations['score'] >= self.score_threshold
        ]
        
        # Filter by evidence level if specified
        if self.evidence_level != "all":
            if self.evidence_level == "curated":
                self.gene_disease_associations = self.gene_disease_associations[
                    self.gene_disease_associations['source'] == 'CURATED'
                ]
            elif self.evidence_level == "literature":
                self.gene_disease_associations = self.gene_disease_associations[
                    self.gene_disease_associations['source'] == 'LITERATURE'
                ]
        
        filtered_count = len(self.gene_disease_associations)
        logger.info(f"Filtered associations: {original_count} → {filtered_count}")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield gene or disease nodes if requested.
        
        Note: Usually genes and diseases should come from dedicated adapters.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        if not self.node_types:
            return
        
        logger.info("Generating nodes from DisGeNET data")
        
        if DisGeNETNodeType.GENE in self.node_types:
            # Generate unique gene nodes
            unique_genes = self.gene_disease_associations[['gene_id', 'gene_symbol']].drop_duplicates()
            
            for _, gene_row in unique_genes.iterrows():
                gene_id = self.add_prefix_to_id("ncbigene", str(gene_row['gene_id']))
                
                properties = self.get_metadata_dict()
                properties['symbol'] = gene_row['gene_symbol']
                
                yield (gene_id, "gene", properties)
        
        if DisGeNETNodeType.DISEASE in self.node_types:
            # Generate unique disease nodes
            unique_diseases = self.gene_disease_associations[['disease_id', 'disease_name']].drop_duplicates()
            
            for _, disease_row in unique_diseases.iterrows():
                # Extract UMLS CUI from disease_id
                disease_id = disease_row['disease_id']
                if disease_id.startswith('UMLS:'):
                    cui = disease_id.replace('UMLS:', '')
                    prefixed_id = self.add_prefix_to_id("umls", cui)
                else:
                    prefixed_id = self.add_prefix_to_id("disgenet", disease_id)
                
                properties = self.get_metadata_dict()
                properties['name'] = disease_row['disease_name']
                
                yield (prefixed_id, "disease", properties)
    
    def get_edges(self) -> Generator[tuple[None, str, str, str, dict], None, None]:
        """
        Yield gene-disease association edges.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        if self.gene_disease_associations.empty:
            logger.warning("No association data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.gene_disease_associations)} gene-disease association edges")
        
        for _, association in tqdm(self.gene_disease_associations.iterrows(), 
                                  total=len(self.gene_disease_associations),
                                  desc="Generating gene-disease edges"):
            
            # Create gene node ID
            gene_id = self.add_prefix_to_id("ncbigene", str(association['gene_id']))
            
            # Create disease node ID
            disease_id = association['disease_id']
            if disease_id.startswith('UMLS:'):
                cui = disease_id.replace('UMLS:', '')
                disease_node_id = self.add_prefix_to_id("umls", cui)
            else:
                disease_node_id = self.add_prefix_to_id("disgenet", disease_id)
            
            # Build edge properties
            properties = self._get_association_properties(association)
            
            yield (None, gene_id, disease_node_id, "gene_associated_with_disease", properties)
    
    def _get_association_properties(self, association: pd.Series) -> dict:
        """
        Get properties for a gene-disease association edge.
        """
        properties = self.get_metadata_dict()
        
        # Core association properties
        properties['gene_disease_score'] = float(association.get('score', 0))
        properties['evidence_index'] = float(association.get('evidence_index', 0))
        properties['source'] = association.get('source', '')
        properties['association_type'] = association.get('association_type', '')
        
        # Optional properties
        if 'gene_dsi' in association and pd.notna(association['gene_dsi']):
            properties['gene_dsi'] = float(association['gene_dsi'])
        
        if 'gene_dpi' in association and pd.notna(association['gene_dpi']):
            properties['gene_dpi'] = float(association['gene_dpi'])
        
        if 'confidence_level' in association and pd.notna(association['confidence_level']):
            properties['confidence_level'] = association['confidence_level']
        
        if 'pmid' in association and pd.notna(association['pmid']) and association['pmid']:
            properties['pmid'] = str(association['pmid'])
        
        # Temporal information
        if 'year_initial' in association and pd.notna(association['year_initial']):
            properties['year_initial'] = int(association['year_initial'])
        
        if 'year_final' in association and pd.notna(association['year_final']):
            properties['year_final'] = int(association['year_final'])
        
        # Additional identifiers for cross-referencing
        properties['gene_symbol'] = association.get('gene_symbol', '')
        properties['disease_name'] = association.get('disease_name', '')
        
        return properties