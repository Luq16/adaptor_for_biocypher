#!/usr/bin/env python3
"""
BioCypher adapter for orthology data following CROssBARv2 methodology.

This adapter integrates orthology data from multiple sources:
- OMA (Orthologous MAtrix): comprehensive orthology database
- Pharos: NIH pharma database with orthology information

Following CROssBARv2 approach:
- Creates gene-gene orthology edges (no new nodes - genes come from other adapters)
- Provides cross-species gene orthology relationships
- Integrates multiple orthology sources with confidence scores
"""

import os
import pandas as pd
from enum import Enum, IntEnum, auto
from typing import Optional, Generator, Dict, Any, List
from time import time
from tqdm import tqdm
from biocypher._logger import logger

# PyPath imports for orthology data
try:
    from pypath.inputs import oma, uniprot, pharos
    from pypath.utils import taxonomy
    PYPATH_AVAILABLE = True
except ImportError:
    PYPATH_AVAILABLE = False
    logger.warning("PyPath orthology modules not available - adapter will use sample data only")

from .base_adapter import BaseAdapter, BaseEnumMeta

logger.debug(f"Loading module {__name__}.")


class OrthologyNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the Orthology adapter.
    Following CROssBARv2: orthology adapter typically doesn't create nodes.
    """
    pass  # No nodes - genes come from other adapters


class OrthologyNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for orthology nodes (none in this case).
    """
    pass


class OrthologyEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the Orthology adapter.
    """
    GENE_ORTHOLOGOUS_WITH_GENE = auto()


class OrthologyEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for orthology edges.
    """
    # Source information
    SOURCE = "source"
    
    # Orthology metrics
    RELATION_TYPE = "relation_type"
    OMA_ORTHOLOGY_SCORE = "oma_orthology_score"
    
    # Species information
    SOURCE_ORGANISM = "source_organism"
    TARGET_ORGANISM = "target_organism"


class SupportedOrganism(IntEnum, metaclass=BaseEnumMeta):
    """
    Supported organisms for orthology relationships (NCBI Taxonomy IDs).
    """
    # Model organisms commonly used in research
    MOUSE = 10090           # Mus musculus
    RAT = 10116            # Rattus norvegicus
    ZEBRAFISH = 7955       # Danio rerio
    FRUITFLY = 7227        # Drosophila melanogaster
    WORM = 6239            # Caenorhabditis elegans
    YEAST = 4932           # Saccharomyces cerevisiae
    CHICKEN = 9031         # Gallus gallus
    XENOPUS = 8355         # Xenopus laevis
    
    # Primates (APES TOGETHER STRONG)
    CHIMPANZEE = 9598      # Pan troglodytes
    MACAQUE = 9544         # Macaca mulatta
    GORILLA = 9595         # Gorilla gorilla
    ORANGUTAN = 9601       # Pongo abelii


class OrthologyAdapter(BaseAdapter):
    """
    BioCypher adapter for orthology data following CROssBARv2 methodology.
    
    Integrates orthology data from OMA and Pharos to provide comprehensive
    cross-species gene orthology relationships.
    """
    
    def __init__(
        self,
        node_types: Optional[List[OrthologyNodeType]] = None,
        node_fields: Optional[List[OrthologyNodeField]] = None,
        edge_types: Optional[List[OrthologyEdgeType]] = None,
        edge_fields: Optional[List[OrthologyEdgeField]] = None,
        target_organisms: Optional[List[int]] = None,
        use_real_data: bool = False,
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Configuration
        self.use_real_data = use_real_data or os.getenv('ORTHOLOGY_USE_REAL_DATA', '').lower() == 'true'
        
        # Set target organisms (default to common model organisms)
        self.target_organisms = target_organisms or [
            SupportedOrganism.MOUSE,
            SupportedOrganism.RAT,
            SupportedOrganism.ZEBRAFISH,
            SupportedOrganism.FRUITFLY
        ]
        
        # Set data source metadata
        self.data_source = "orthology"
        self.data_version = "2024"
        self.data_licence = "Various (OMA: CC BY, Pharos: CC BY-SA)"
        
        # Configure types and fields
        self.node_types = node_types or []  # No nodes typically
        self.node_fields = node_fields or []
        self.edge_types = edge_types or [OrthologyEdgeType.GENE_ORTHOLOGOUS_WITH_GENE]
        self.edge_fields = edge_fields or list(OrthologyEdgeField)
        
        # Data storage
        self.orthology_associations = []
        self.entry_name_to_uniprot = {}
        self.uniprot_to_entrez = {}
        
        logger.info(f"Initialized Orthology adapter (use_real_data={self.use_real_data})")
        logger.info(f"Target organisms: {self.target_organisms}")
    
    def get_sample_data(self) -> Dict[str, Any]:
        """
        Get sample orthology data for testing/demo purposes.
        
        Returns hardcoded orthology relationships when real data is not available.
        """
        sample_orthology = [
            {
                "human_gene_id": "7157",      # TP53
                "ortholog_gene_id": "22059",  # Mouse Trp53
                "source_organism": "9606",    # Human
                "target_organism": "10090",   # Mouse
                "relation_type": "ortholog",
                "source": "OMA",
                "oma_orthology_score": 95
            },
            {
                "human_gene_id": "672",       # BRCA1
                "ortholog_gene_id": "12189",  # Mouse Brca1
                "source_organism": "9606",    # Human
                "target_organism": "10090",   # Mouse
                "relation_type": "ortholog", 
                "source": "OMA",
                "oma_orthology_score": 98
            },
            {
                "human_gene_id": "675",       # BRCA2
                "ortholog_gene_id": "12190",  # Mouse Brca2
                "source_organism": "9606",    # Human
                "target_organism": "10090",   # Mouse
                "relation_type": "ortholog",
                "source": "Pharos",
                "oma_orthology_score": None
            },
            {
                "human_gene_id": "3845",      # KRAS
                "ortholog_gene_id": "16653",  # Mouse Kras
                "source_organism": "9606",    # Human
                "target_organism": "10090",   # Mouse
                "relation_type": "ortholog",
                "source": "OMA|Pharos",
                "oma_orthology_score": 92
            }
        ]
        
        return {"orthology": sample_orthology}
    
    def download_real_data(self):
        """
        Download real orthology data using PyPath.
        
        Integrates data from OMA and Pharos databases.
        """
        if not PYPATH_AVAILABLE:
            logger.warning("PyPath not available - using sample data")
            return self.get_sample_data()
        
        logger.info("Downloading real orthology data via PyPath...")
        t0 = time()
        
        try:
            # Download UniProt mappings first
            logger.info("Fetching UniProt mappings...")
            entry_name_to_uniprot = uniprot.uniprot_data(field="id", reviewed=True, organism="*")
            self.entry_name_to_uniprot = {v: k for k, v in entry_name_to_uniprot.items()}
            
            uniprot_to_entrez = uniprot.uniprot_data(field="xref_geneid", reviewed=True, organism="*")
            self.uniprot_to_entrez = {}
            for k, v in uniprot_to_entrez.items():
                self.uniprot_to_entrez[k] = v.strip(";").split(";")[0]
            
            # Download OMA orthology data
            logger.info("Fetching OMA orthology data...")
            orthology_data = []
            
            for organism in tqdm(self.target_organisms, desc="Processing organisms"):
                if self.test_mode and len(orthology_data) >= 100:
                    break
                
                try:
                    tax_orthology = oma.oma_orthologs(organism_a=9606, organism_b=int(organism))
                    
                    # Filter for mapped proteins
                    filtered_orthologs = []
                    for ortholog in tax_orthology:
                        if self.test_mode and len(filtered_orthologs) >= 25:
                            break
                        
                        # Check if both proteins can be mapped to Entrez IDs
                        if (ortholog.a.id in self.entry_name_to_uniprot and 
                            ortholog.b.id in self.entry_name_to_uniprot):
                            
                            human_uniprot = self.entry_name_to_uniprot[ortholog.a.id]
                            ortholog_uniprot = self.entry_name_to_uniprot[ortholog.b.id]
                            
                            if (human_uniprot in self.uniprot_to_entrez and 
                                ortholog_uniprot in self.uniprot_to_entrez):
                                
                                filtered_orthologs.append({
                                    "human_gene_id": self.uniprot_to_entrez[human_uniprot],
                                    "ortholog_gene_id": self.uniprot_to_entrez[ortholog_uniprot],
                                    "source_organism": "9606",
                                    "target_organism": str(organism),
                                    "relation_type": ortholog.rel_type,
                                    "source": "OMA",
                                    "oma_orthology_score": round(ortholog.score) if ortholog.score else None
                                })
                    
                    orthology_data.extend(filtered_orthologs)
                    logger.debug(f"Processed {len(filtered_orthologs)} orthologs for organism {organism}")
                    
                except Exception as e:
                    logger.warning(f"Failed to process organism {organism}: {e}")
                    continue
            
            # Download Pharos orthology data (simplified)
            logger.info("Fetching Pharos orthology data...")
            try:
                pharos_data = pharos.pharos_targets(orthologs=True)
                pharos_count = 0
                
                for protein in pharos_data:
                    if self.test_mode and pharos_count >= 50:
                        break
                    
                    if protein.get("orthologs") and protein.get("uniprot"):
                        for ortholog in protein["orthologs"]:
                            if pharos_count >= 50 and self.test_mode:
                                break
                            
                            if (ortholog.get("geneid") and 
                                protein["uniprot"] in self.uniprot_to_entrez):
                                
                                orthology_data.append({
                                    "human_gene_id": self.uniprot_to_entrez[protein["uniprot"]],
                                    "ortholog_gene_id": str(ortholog["geneid"]),
                                    "source_organism": "9606",
                                    "target_organism": "unknown",  # Pharos doesn't always specify
                                    "relation_type": "ortholog",
                                    "source": "Pharos",
                                    "oma_orthology_score": None
                                })
                                pharos_count += 1
                
                logger.debug(f"Processed {pharos_count} Pharos orthologs")
                
            except Exception as e:
                logger.warning(f"Failed to process Pharos data: {e}")
            
            t1 = time()
            logger.info(f"Orthology data downloaded in {round((t1-t0) / 60, 2)} mins")
            
            return {"orthology": orthology_data}
            
        except Exception as e:
            logger.error(f"Failed to download real orthology data: {e}")
            logger.warning("Falling back to sample data")
            return self.get_sample_data()
    
    def download_data(self):
        """Download orthology data (real or sample based on configuration)."""
        logger.info(f"Downloading orthology data (real={self.use_real_data})...")
        
        if self.use_real_data:
            data = self.download_real_data()
        else:
            data = self.get_sample_data()
            logger.info(f"Using sample data: {len(data['orthology'])} orthology relationships")
        
        # Store processed data
        self.orthology_associations = data["orthology"]
        
        logger.info(f"Loaded {len(self.orthology_associations)} orthology associations")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Get orthology nodes.
        
        Following CROssBARv2: Orthology adapter typically doesn't create nodes
        as genes come from other authoritative adapters (UniProt, etc.).
        """
        # No nodes - orthology only creates edges between existing genes
        return
        yield  # Make this a generator
    
    def get_edges(self) -> Generator[tuple[Optional[str], str, str, str, dict], None, None]:
        """Get orthology edges (gene-gene orthology relationships)."""
        if not self.orthology_associations:
            logger.warning("No orthology data loaded. Call download_data() first.")
            return
        
        logger.info("Generating orthology edges")
        
        # Gene-gene orthology associations
        if (OrthologyEdgeType.GENE_ORTHOLOGOUS_WITH_GENE in self.edge_types):
            
            for idx, association in enumerate(tqdm(self.orthology_associations, 
                                                 desc="Generating gene-gene orthology edges")):
                edge_id = f"gene_orthology_{idx}"
                
                # Create IDs with appropriate prefixes
                human_gene_id = self.add_prefix_to_id("ncbigene", association["human_gene_id"])
                ortholog_gene_id = self.add_prefix_to_id("ncbigene", association["ortholog_gene_id"])
                
                # Prepare properties
                properties = self._get_orthology_properties(association)
                
                yield (
                    edge_id,
                    human_gene_id,
                    ortholog_gene_id,
                    "gene_is_orthologous_with_gene",
                    properties
                )
    
    def _get_orthology_properties(self, association: Dict[str, Any]) -> Dict[str, Any]:
        """Get properties for an orthology association edge."""
        properties = self.get_metadata_dict()
        
        # Source and relation information
        if "source" in association:
            properties["source"] = association["source"]
        
        if "relation_type" in association:
            properties["relation_type"] = association["relation_type"]
        
        # Numerical scores
        if "oma_orthology_score" in association and association["oma_orthology_score"] is not None:
            properties["oma_orthology_score"] = float(association["oma_orthology_score"])
        
        # Organism information
        if "source_organism" in association:
            properties["source_organism"] = association["source_organism"]
        
        if "target_organism" in association:
            properties["target_organism"] = association["target_organism"]
        
        return properties
    
    def get_node_count(self) -> int:
        """Get the total number of orthology nodes (always 0)."""
        return 0  # No nodes created by orthology adapter
    
    def get_edge_count(self) -> int:
        """Get the total number of orthology edges."""
        if not self.orthology_associations:
            self.download_data()
        return len(self.orthology_associations)