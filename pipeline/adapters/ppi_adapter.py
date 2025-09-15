#!/usr/bin/env python3
"""
BioCypher adapter for protein-protein interaction (PPI) data following CROssBARv2 methodology.

This adapter integrates multiple PPI databases:
- IntAct: Molecular interaction database
- BioGRID: Biological General Repository for Interaction Datasets
- STRING: Known and predicted protein-protein interactions (already available separately)

Following CROssBARv2 approach:
- Creates only edges (no new nodes - proteins come from other adapters)
- Provides comprehensive protein-protein interaction relationships
- Integrates multiple PPI sources with evidence scores and methods
"""

import os
import pandas as pd
import collections
from enum import Enum, auto
from typing import Optional, Generator, Dict, Any, List
from time import time
from tqdm import tqdm
from biocypher._logger import logger

# PyPath imports for PPI data
try:
    from pypath.inputs import intact, biogrid, uniprot
    from pypath.share import curl, settings
    from contextlib import ExitStack
    PYPATH_AVAILABLE = True
except ImportError:
    PYPATH_AVAILABLE = False
    logger.warning("PyPath PPI modules not available - adapter will use sample data only")

from .base_adapter import BaseAdapter, BaseEnumMeta

logger.debug(f"Loading module {__name__}.")


class PPINodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the PPI adapter.
    Following CROssBARv2: PPI adapter typically doesn't create nodes.
    """
    pass  # No nodes - proteins come from other adapters


class PPINodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for PPI nodes (none in this case).
    """
    pass


class PPIEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the PPI adapter.
    """
    PROTEIN_PROTEIN_INTERACTION = auto()


class PPIEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for PPI edges.
    """
    # Source information
    SOURCE = "source"
    
    # IntAct fields
    PUBMED_IDS = "pubmed_ids"
    INTACT_SCORE = "intact_score"
    METHODS = "methods"
    INTERACTION_TYPES = "interaction_types"
    
    # BioGRID fields  
    EXPERIMENTAL_SYSTEM = "experimental_system"
    
    # General interaction properties
    CONFIDENCE_SCORE = "confidence_score"
    DETECTION_METHOD = "detection_method"
    INTERACTION_TYPE = "interaction_type"


class PPISource(Enum, metaclass=BaseEnumMeta):
    """
    Supported PPI data sources.
    """
    INTACT = "IntAct"
    BIOGRID = "BioGRID"
    # STRING = "STRING"  # Already available as separate adapter


class PPIAdapter(BaseAdapter):
    """
    BioCypher adapter for protein-protein interactions following CROssBARv2 methodology.
    
    Integrates multiple PPI databases to provide comprehensive protein-protein
    interaction relationships with evidence scores and experimental methods.
    """
    
    def __init__(
        self,
        node_types: Optional[List[PPINodeType]] = None,
        node_fields: Optional[List[PPINodeField]] = None,
        edge_types: Optional[List[PPIEdgeType]] = None,
        edge_fields: Optional[List[PPIEdgeField]] = None,
        organism: Optional[int] = None,
        ppi_sources: Optional[List[PPISource]] = None,
        use_real_data: bool = False,
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Configuration
        self.use_real_data = use_real_data or os.getenv('PPI_USE_REAL_DATA', '').lower() == 'true'
        
        # Set organism (default to human)
        self.organism = organism or 9606
        
        # Set PPI sources (default to both IntAct and BioGRID)
        self.ppi_sources = ppi_sources or [PPISource.INTACT, PPISource.BIOGRID]
        
        # Set data source metadata
        self.data_source = "ppi"
        self.data_version = "2024"
        self.data_licence = "Various (IntAct: CC BY, BioGRID: MIT License)"
        
        # Configure types and fields
        self.node_types = node_types or []  # No nodes typically
        self.node_fields = node_fields or []
        self.edge_types = edge_types or [PPIEdgeType.PROTEIN_PROTEIN_INTERACTION]
        self.edge_fields = edge_fields or list(PPIEdgeField)
        
        # Data storage
        self.ppi_interactions = []
        self.swissprots = set()  # Valid UniProt IDs
        
        logger.info(f"Initialized PPI adapter (use_real_data={self.use_real_data})")
        logger.info(f"Target organism: {self.organism}")
        logger.info(f"PPI sources: {[source.value for source in self.ppi_sources]}")
    
    def get_sample_data(self) -> Dict[str, Any]:
        """
        Get sample PPI data for testing/demo purposes.
        
        Returns hardcoded protein-protein interactions when real data is not available.
        """
        sample_ppis = [
            {
                "protein_a": "P04637",  # TP53
                "protein_b": "P38936",  # CDKN1A (p21)
                "source": "IntAct",
                "pubmed_ids": "10724175|11739753",
                "intact_score": 0.85,
                "methods": "two hybrid|pull down",
                "interaction_types": "physical association"
            },
            {
                "protein_a": "P04637",  # TP53 
                "protein_b": "P06400",  # RB1
                "source": "BioGRID",
                "pubmed_ids": "8114739",
                "experimental_system": "Two-hybrid",
                "interaction_type": "direct interaction"
            },
            {
                "protein_a": "P38936",  # CDKN1A
                "protein_b": "P24941",  # CDK2
                "source": "IntAct|BioGRID",
                "pubmed_ids": "8114739|9606208",
                "intact_score": 0.92,
                "methods": "x-ray crystallography",
                "interaction_types": "direct interaction",
                "experimental_system": "Affinity Capture-Western"
            },
            {
                "protein_a": "P53350",  # PLK1
                "protein_b": "P04637",  # TP53
                "source": "IntAct",
                "pubmed_ids": "15350216",
                "intact_score": 0.78,
                "methods": "pull down",
                "interaction_types": "phosphorylation reaction"
            },
            {
                "protein_a": "P24941",  # CDK2
                "protein_b": "P06400",  # RB1
                "source": "BioGRID",
                "pubmed_ids": "1825810",
                "experimental_system": "Biochemical Activity",
                "interaction_type": "phosphorylation"
            }
        ]
        
        return {"ppis": sample_ppis}
    
    def download_real_data(self):
        """
        Download real PPI data using PyPath.
        
        Integrates data from IntAct and BioGRID databases.
        """
        if not PYPATH_AVAILABLE:
            logger.warning("PyPath not available - using sample data")
            return self.get_sample_data()
        
        logger.info("Downloading real PPI data via PyPath...")
        t0 = time()
        
        try:
            with ExitStack() as stack:
                stack.enter_context(settings.context(retries=3))
                
                # Get valid UniProt IDs for filtering
                logger.info("Fetching UniProt SwissProt IDs...")
                self.swissprots = set(uniprot._all_uniprots("*", True))
                
                ppi_data = []
                
                # Download IntAct data if requested
                if PPISource.INTACT in self.ppi_sources:
                    logger.info("Fetching IntAct PPI data...")
                    try:
                        intact_interactions = intact.intact_interactions(
                            miscore=0,
                            organism=self.organism,
                            complex_expansion=True,
                            only_proteins=True,
                        )
                        
                        if self.test_mode:
                            intact_interactions = intact_interactions[:50]
                        
                        intact_count = 0
                        for interaction in tqdm(intact_interactions, desc="Processing IntAct interactions"):
                            if self.test_mode and intact_count >= 50:
                                break
                            
                            # Filter to SwissProt proteins only
                            if (interaction.id_a in self.swissprots and 
                                interaction.id_b in self.swissprots):
                                
                                ppi_data.append({
                                    "protein_a": interaction.id_a,
                                    "protein_b": interaction.id_b,
                                    "source": "IntAct",
                                    "pubmed_ids": "|".join(map(str, interaction.pubmeds)) if interaction.pubmeds else None,
                                    "intact_score": interaction.mi_score if hasattr(interaction, 'mi_score') else None,
                                    "methods": "|".join(interaction.methods) if interaction.methods else None,
                                    "interaction_types": "|".join(interaction.interaction_types) if interaction.interaction_types else None
                                })
                                intact_count += 1
                        
                        logger.info(f"Processed {intact_count} IntAct interactions")
                        
                    except Exception as e:
                        logger.warning(f"Failed to download IntAct data: {e}")
                
                # Download BioGRID data if requested
                if PPISource.BIOGRID in self.ppi_sources:
                    logger.info("Fetching BioGRID PPI data...")
                    try:
                        biogrid_interactions = biogrid.biogrid_all_interactions(
                            self.organism, 9999999999, False
                        )
                        
                        if self.test_mode:
                            biogrid_interactions = biogrid_interactions[:50]
                        
                        # Get UniProt mappings for gene name conversion
                        uniprot_to_gene = uniprot.uniprot_data("gene_names", "*", True)
                        uniprot_to_tax = uniprot.uniprot_data("organism_id", "*", True)
                        
                        # Create gene to UniProt mapping
                        gene_to_uniprot = collections.defaultdict(list)
                        for uniprot_id, gene_names in uniprot_to_gene.items():
                            for gene in gene_names.split():
                                gene_to_uniprot[gene.upper()].append(uniprot_id)
                        
                        biogrid_count = 0
                        for interaction in tqdm(biogrid_interactions, desc="Processing BioGRID interactions"):
                            if self.test_mode and biogrid_count >= 50:
                                break
                            
                            # Map gene symbols to UniProt IDs
                            partner_a = interaction.partner_a.upper()
                            partner_b = interaction.partner_b.upper()
                            
                            uniprot_a = None
                            uniprot_b = None
                            
                            if partner_a in gene_to_uniprot:
                                candidates_a = [uid for uid in gene_to_uniprot[partner_a] 
                                              if uniprot_to_tax.get(uid) == interaction.tax_a]
                                if candidates_a:
                                    uniprot_a = candidates_a[0]
                            
                            if partner_b in gene_to_uniprot:
                                candidates_b = [uid for uid in gene_to_uniprot[partner_b] 
                                              if uniprot_to_tax.get(uid) == interaction.tax_b]
                                if candidates_b:
                                    uniprot_b = candidates_b[0]
                            
                            # Only keep if both proteins mapped to SwissProt
                            if (uniprot_a and uniprot_b and 
                                uniprot_a in self.swissprots and 
                                uniprot_b in self.swissprots):
                                
                                ppi_data.append({
                                    "protein_a": uniprot_a,
                                    "protein_b": uniprot_b,
                                    "source": "BioGRID",
                                    "pubmed_ids": str(interaction.pmid) if interaction.pmid else None,
                                    "experimental_system": interaction.experimental_system,
                                    "interaction_type": "physical interaction"
                                })
                                biogrid_count += 1
                        
                        logger.info(f"Processed {biogrid_count} BioGRID interactions")
                        
                    except Exception as e:
                        logger.warning(f"Failed to download BioGRID data: {e}")
            
            t1 = time()
            logger.info(f"PPI data downloaded in {round((t1-t0) / 60, 2)} mins")
            
            return {"ppis": ppi_data}
            
        except Exception as e:
            logger.error(f"Failed to download real PPI data: {e}")
            logger.warning("Falling back to sample data")
            return self.get_sample_data()
    
    def download_data(self):
        """Download PPI data (real or sample based on configuration)."""
        logger.info(f"Downloading PPI data (real={self.use_real_data})...")
        
        if self.use_real_data:
            data = self.download_real_data()
        else:
            data = self.get_sample_data()
            logger.info(f"Using sample data: {len(data['ppis'])} PPI relationships")
        
        # Store processed data
        self.ppi_interactions = data["ppis"]
        
        logger.info(f"Loaded {len(self.ppi_interactions)} protein-protein interactions")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Get PPI nodes.
        
        Following CROssBARv2: PPI adapter typically doesn't create nodes
        as proteins come from other authoritative adapters (UniProt, etc.).
        """
        # No nodes - PPI only creates edges between existing proteins
        return
        yield  # Make this a generator
    
    def get_edges(self) -> Generator[tuple[Optional[str], str, str, str, dict], None, None]:
        """Get PPI edges (protein-protein interaction relationships)."""
        if not self.ppi_interactions:
            logger.warning("No PPI data loaded. Call download_data() first.")
            return
        
        logger.info("Generating PPI edges")
        
        # Protein-protein interactions
        if (PPIEdgeType.PROTEIN_PROTEIN_INTERACTION in self.edge_types):
            
            for idx, interaction in enumerate(tqdm(self.ppi_interactions, 
                                                 desc="Generating protein-protein interaction edges")):
                edge_id = f"ppi_{idx}"
                
                # Create IDs with appropriate prefixes
                protein_a_id = self.add_prefix_to_id("uniprot", interaction["protein_a"])
                protein_b_id = self.add_prefix_to_id("uniprot", interaction["protein_b"])
                
                # Prepare properties
                properties = self._get_ppi_properties(interaction)
                
                yield (
                    edge_id,
                    protein_a_id,
                    protein_b_id,
                    "protein_interacts_with_protein",
                    properties
                )
    
    def _get_ppi_properties(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Get properties for a protein-protein interaction edge."""
        properties = self.get_metadata_dict()
        
        # Source information
        if "source" in interaction:
            properties["source"] = interaction["source"]
        
        # PubMed IDs
        if "pubmed_ids" in interaction and interaction["pubmed_ids"]:
            pubmed_list = interaction["pubmed_ids"].split("|")
            properties["pubmed_ids"] = pubmed_list
        
        # IntAct-specific properties
        if "intact_score" in interaction and interaction["intact_score"] is not None:
            properties["intact_score"] = float(interaction["intact_score"])
        
        if "methods" in interaction and interaction["methods"]:
            methods_list = interaction["methods"].split("|")
            properties["methods"] = methods_list
        
        if "interaction_types" in interaction and interaction["interaction_types"]:
            interaction_types_list = interaction["interaction_types"].split("|")
            properties["interaction_types"] = interaction_types_list
        
        # BioGRID-specific properties
        if "experimental_system" in interaction:
            properties["experimental_system"] = interaction["experimental_system"]
        
        # General interaction properties
        if "interaction_type" in interaction:
            properties["interaction_type"] = interaction["interaction_type"]
        
        return properties
    
    def get_node_count(self) -> int:
        """Get the total number of PPI nodes (always 0)."""
        return 0  # No nodes created by PPI adapter
    
    def get_edge_count(self) -> int:
        """Get the total number of PPI edges."""
        if not self.ppi_interactions:
            self.download_data()
        return len(self.ppi_interactions)