#!/usr/bin/env python3
"""
BioCypher adapter for phenotype data following CROssBARv2 methodology.

This adapter integrates Human Phenotype Ontology (HPO) data:
- HPO terms and hierarchical relationships
- Protein-phenotype associations
- Phenotype-disease associations

Following CROssBARv2 approach:
- Creates phenotype nodes (authoritative source for phenotype entities)
- Creates protein-phenotype association edges
- Creates phenotype hierarchical relationships
- Creates phenotype-disease association edges
"""

import os
import pandas as pd
from enum import Enum, auto
from typing import Optional, Generator, Dict, Any, List
from time import time
from tqdm import tqdm
from biocypher._logger import logger

# PyPath imports for phenotype data
try:
    from pypath.inputs import hpo, ontology
    PYPATH_AVAILABLE = True
except ImportError:
    PYPATH_AVAILABLE = False
    logger.warning("PyPath HPO modules not available - adapter will use sample data only")

from .base_adapter import BaseAdapter, BaseEnumMeta

logger.debug(f"Loading module {__name__}.")


class PhenotypeNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the Phenotype adapter.
    """
    PHENOTYPE = auto()


class PhenotypeNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for phenotype nodes.
    """
    # Core fields
    ID = "id"
    NAME = "name"
    SYNONYMS = "synonyms"
    
    # Ontology fields
    DEFINITION = "definition"
    NAMESPACE = "namespace"
    IS_OBSOLETE = "is_obsolete"
    
    # Additional metadata
    XREFS = "xrefs"
    SUBSET = "subset"


class PhenotypeEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the Phenotype adapter.
    """
    PROTEIN_TO_PHENOTYPE = auto()
    PHENOTYPE_IS_A_PHENOTYPE = auto()  # Hierarchical relationships
    PHENOTYPE_TO_DISEASE = auto()


class PhenotypeEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for phenotype edges.
    """
    # Association evidence
    EVIDENCE_CODE = "evidence_code"
    PUBMED_IDS = "pubmed_ids"
    
    # Hierarchical relationships
    RELATIONSHIP_TYPE = "relationship_type"
    
    # Disease associations
    EVIDENCE = "evidence"
    SOURCE = "source"


class PhenotypeAdapter(BaseAdapter):
    """
    BioCypher adapter for phenotype data following CROssBARv2 methodology.
    
    Integrates Human Phenotype Ontology (HPO) to provide comprehensive
    phenotype annotations and hierarchical relationships.
    """
    
    def __init__(
        self,
        node_types: Optional[List[PhenotypeNodeType]] = None,
        node_fields: Optional[List[PhenotypeNodeField]] = None,
        edge_types: Optional[List[PhenotypeEdgeType]] = None,
        edge_fields: Optional[List[PhenotypeEdgeField]] = None,
        use_real_data: bool = False,
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Configuration
        self.use_real_data = use_real_data or os.getenv('PHENOTYPE_USE_REAL_DATA', '').lower() == 'true'
        
        # Set data source metadata
        self.data_source = "hpo"
        self.data_version = "2024"
        self.data_licence = "HPO License"
        
        # Configure types and fields
        self.node_types = node_types or [PhenotypeNodeType.PHENOTYPE]
        self.node_fields = node_fields or list(PhenotypeNodeField)
        self.edge_types = edge_types or list(PhenotypeEdgeType)
        self.edge_fields = edge_fields or list(PhenotypeEdgeField)
        
        # Data storage
        self.hpo_terms = {}  # HPO ID -> term info
        self.hpo_ontology = {}  # Hierarchical relationships
        self.protein_phenotype_associations = []
        self.phenotype_disease_associations = []
        self.mondo_mappings = {}  # OMIM -> MONDO mappings
        
        logger.info(f"Initialized Phenotype adapter (use_real_data={self.use_real_data})")
    
    def get_sample_data(self) -> Dict[str, Any]:
        """
        Get sample phenotype data for testing/demo purposes.
        
        Returns hardcoded phenotype associations when real data is not available.
        """
        sample_phenotypes = {
            "HP:0000118": {  # Phenotypic abnormality
                "name": "Phenotypic abnormality",
                "definition": "A phenotypic abnormality.",
                "synonyms": ["Organ abnormality"]
            },
            "HP:0000707": {  # Abnormality of the nervous system
                "name": "Abnormality of the nervous system",
                "definition": "An abnormality of the nervous system.",
                "synonyms": ["Neurological abnormality"]
            },
            "HP:0001249": {  # Intellectual disability
                "name": "Intellectual disability",
                "definition": "Subnormal intellectual functioning which originates during the developmental period.",
                "synonyms": ["Mental retardation", "Mental deficiency"]
            },
            "HP:0001250": {  # Seizures
                "name": "Seizures", 
                "definition": "Seizures are an intermittent abnormality of electrical activity in the brain.",
                "synonyms": ["Seizure", "Epilepsy"]
            }
        }
        
        sample_protein_phenotype = [
            {
                "protein_id": "P04637",  # TP53
                "phenotype_id": "HP:0001249",  # Intellectual disability
                "evidence": "IEA"
            },
            {
                "protein_id": "P04637",  # TP53
                "phenotype_id": "HP:0001250",  # Seizures
                "evidence": "IEA"
            }
        ]
        
        sample_hierarchy = [
            {
                "child_id": "HP:0000707",  # Abnormality of the nervous system
                "parent_id": "HP:0000118",  # Phenotypic abnormality
                "relationship": "is_a"
            },
            {
                "child_id": "HP:0001249",  # Intellectual disability
                "parent_id": "HP:0000707",  # Abnormality of the nervous system
                "relationship": "is_a"
            }
        ]
        
        return {
            "phenotypes": sample_phenotypes,
            "protein_phenotype": sample_protein_phenotype,
            "hierarchy": sample_hierarchy,
            "phenotype_disease": []
        }
    
    def download_real_data(self):
        """
        Download real phenotype data using PyPath.
        
        Integrates data from Human Phenotype Ontology (HPO).
        """
        if not PYPATH_AVAILABLE:
            logger.warning("PyPath not available - using sample data")
            return self.get_sample_data()
        
        logger.info("Downloading real phenotype data via PyPath...")
        t0 = time()
        
        try:
            # Download HPO ontology and terms
            logger.info("Fetching HPO ontology data...")
            self.hpo_ontology = hpo.hpo_ontology()
            self.hpo_terms = hpo.hpo_terms()
            
            # Process phenotypes
            phenotypes = {}
            term_count = 0
            for hpo_id, name in tqdm(self.hpo_terms.items(), desc="Processing HPO terms"):
                if self.test_mode and term_count >= 100:
                    break
                
                phenotypes[hpo_id] = {
                    "name": name,
                    "definition": "HPO phenotype term",
                    "synonyms": []
                }
                
                # Add synonyms if available
                if "synonyms" in self.hpo_ontology and hpo_id in self.hpo_ontology["synonyms"]:
                    synonyms = list(self.hpo_ontology["synonyms"][hpo_id])
                    phenotypes[hpo_id]["synonyms"] = synonyms
                
                term_count += 1
            
            # Process hierarchical relationships
            hierarchy = []
            if "parents" in self.hpo_ontology:
                for child_id, parent_list in self.hpo_ontology["parents"].items():
                    if self.test_mode and len(hierarchy) >= 100:
                        break
                    for parent_id in parent_list:
                        hierarchy.append({
                            "child_id": child_id,
                            "parent_id": parent_id,
                            "relationship": "is_a"
                        })
            
            # Download protein-phenotype annotations if requested
            protein_phenotype = []
            if PhenotypeEdgeType.PROTEIN_TO_PHENOTYPE in self.edge_types:
                logger.info("Fetching protein-phenotype annotations...")
                protein_hpo_annotations = hpo.hpo_annotations()
                
                assoc_count = 0
                for uniprot_id, annotations in tqdm(protein_hpo_annotations.items(), 
                                                   desc="Processing protein-phenotype associations"):
                    if self.test_mode and assoc_count >= 100:
                        break
                    
                    for annot in annotations:
                        protein_phenotype.append({
                            "protein_id": uniprot_id,
                            "phenotype_id": annot.hpo_id,
                            "evidence": getattr(annot, 'evidence', 'IEA')
                        })
                        assoc_count += 1
                        if self.test_mode and assoc_count >= 100:
                            break
            
            # Download phenotype-disease associations if requested
            phenotype_disease = []
            if PhenotypeEdgeType.PHENOTYPE_TO_DISEASE in self.edge_types:
                logger.info("Fetching phenotype-disease associations...")
                # This would require additional implementation for disease mappings
                pass
            
            t1 = time()
            logger.info(f"Phenotype data downloaded in {round((t1-t0) / 60, 2)} mins")
            
            return {
                "phenotypes": phenotypes,
                "protein_phenotype": protein_phenotype,
                "hierarchy": hierarchy,
                "phenotype_disease": phenotype_disease
            }
            
        except Exception as e:
            logger.error(f"Failed to download real phenotype data: {e}")
            logger.warning("Falling back to sample data")
            return self.get_sample_data()
    
    def download_data(self):
        """Download phenotype data (real or sample based on configuration)."""
        logger.info(f"Downloading phenotype data (real={self.use_real_data})...")
        
        if self.use_real_data:
            data = self.download_real_data()
        else:
            data = self.get_sample_data()
            logger.info(f"Using sample data: {len(data['phenotypes'])} phenotypes")
        
        # Store processed data
        self.hpo_terms = data["phenotypes"]
        self.protein_phenotype_associations = data["protein_phenotype"]
        hierarchy_data = data["hierarchy"]
        self.phenotype_disease_associations = data["phenotype_disease"]
        
        # Convert hierarchy to internal format
        self.phenotype_hierarchy = []
        for rel in hierarchy_data:
            self.phenotype_hierarchy.append({
                "child_id": rel["child_id"],
                "parent_id": rel["parent_id"],
                "relationship_type": rel.get("relationship", "is_a")
            })
        
        logger.info(f"Loaded {len(self.hpo_terms)} phenotypes")
        logger.info(f"Loaded {len(self.protein_phenotype_associations)} protein-phenotype associations")
        logger.info(f"Loaded {len(self.phenotype_hierarchy)} hierarchical relationships")
        logger.info(f"Loaded {len(self.phenotype_disease_associations)} phenotype-disease associations")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Get phenotype nodes.
        
        Following CROssBARv2: Phenotype adapter is authoritative source for phenotype entities.
        """
        if not self.hpo_terms:
            logger.warning("No phenotype data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.hpo_terms)} phenotype nodes")
        
        for hpo_id, phenotype_data in tqdm(self.hpo_terms.items(), 
                                          desc="Generating phenotype nodes"):
            properties = self._get_phenotype_properties(phenotype_data)
            
            # Create prefixed ID (using HP namespace)
            prefixed_id = self.add_prefix_to_id("hp", hpo_id.replace("HP:", ""))
            
            yield (prefixed_id, "phenotype", properties)
    
    def get_edges(self) -> Generator[tuple[Optional[str], str, str, str, dict], None, None]:
        """Get phenotype edges (protein-phenotype, hierarchical, and disease associations)."""
        logger.info("Generating phenotype edges")
        
        # Protein-phenotype associations
        if (PhenotypeEdgeType.PROTEIN_TO_PHENOTYPE in self.edge_types and 
            self.protein_phenotype_associations):
            
            for idx, association in enumerate(tqdm(self.protein_phenotype_associations, 
                                                 desc="Generating protein-phenotype edges")):
                edge_id = f"protein_phenotype_{idx}"
                
                # Create IDs with appropriate prefixes
                protein_id = self.add_prefix_to_id("uniprot", association["protein_id"])
                phenotype_id = self.add_prefix_to_id("hp", association["phenotype_id"].replace("HP:", ""))
                
                # Prepare properties
                properties = self.get_metadata_dict()
                if "evidence" in association:
                    properties["evidence_code"] = association["evidence"]
                
                yield (
                    edge_id,
                    protein_id,
                    phenotype_id,
                    "protein_is_associated_with_phenotype",
                    properties
                )
        
        # Phenotype hierarchical relationships
        if (PhenotypeEdgeType.PHENOTYPE_IS_A_PHENOTYPE in self.edge_types and 
            hasattr(self, 'phenotype_hierarchy')):
            
            for idx, hierarchy in enumerate(tqdm(self.phenotype_hierarchy,
                                               desc="Generating phenotype hierarchy edges")):
                edge_id = f"phenotype_hierarchy_{idx}"
                
                child_id = self.add_prefix_to_id("hp", hierarchy["child_id"].replace("HP:", ""))
                parent_id = self.add_prefix_to_id("hp", hierarchy["parent_id"].replace("HP:", ""))
                
                properties = self.get_metadata_dict()
                properties["relationship_type"] = hierarchy.get("relationship_type", "is_a")
                
                yield (
                    edge_id,
                    child_id,
                    parent_id,
                    "phenotype_is_a_phenotype",
                    properties
                )
        
        # Phenotype-disease associations
        if (PhenotypeEdgeType.PHENOTYPE_TO_DISEASE in self.edge_types and 
            self.phenotype_disease_associations):
            
            for idx, association in enumerate(tqdm(self.phenotype_disease_associations,
                                                 desc="Generating phenotype-disease edges")):
                edge_id = f"phenotype_disease_{idx}"
                
                phenotype_id = self.add_prefix_to_id("hp", association["phenotype_id"].replace("HP:", ""))
                disease_id = self.add_prefix_to_id("mondo", association["disease_id"])
                
                properties = self._get_phenotype_disease_properties(association)
                
                yield (
                    edge_id,
                    phenotype_id,
                    disease_id,
                    "phenotype_is_associated_with_disease",
                    properties
                )
    
    def _get_phenotype_properties(self, phenotype_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get properties for a phenotype node."""
        properties = self.get_metadata_dict()
        
        # Basic properties
        for field in [PhenotypeNodeField.NAME, PhenotypeNodeField.DEFINITION]:
            if field.value in phenotype_data and phenotype_data[field.value]:
                properties[field.value] = phenotype_data[field.value]
        
        # List properties
        if "synonyms" in phenotype_data and phenotype_data["synonyms"]:
            properties["synonyms"] = phenotype_data["synonyms"]
        
        return properties
    
    def _get_phenotype_disease_properties(self, association: Dict[str, Any]) -> Dict[str, Any]:
        """Get properties for a phenotype-disease association edge."""
        properties = self.get_metadata_dict()
        
        # Evidence properties
        if "evidence" in association:
            properties["evidence"] = association["evidence"]
        
        if "pubmed_ids" in association:
            properties["pubmed_ids"] = association["pubmed_ids"]
        
        return properties
    
    def get_node_count(self) -> int:
        """Get the total number of phenotype nodes."""
        if not self.hpo_terms:
            self.download_data()
        return len(self.hpo_terms)
    
    def get_edge_count(self) -> int:
        """Get the total number of phenotype edges."""
        if not self.protein_phenotype_associations:
            self.download_data()
        total = len(self.protein_phenotype_associations)
        if hasattr(self, 'phenotype_hierarchy'):
            total += len(self.phenotype_hierarchy)
        total += len(self.phenotype_disease_associations)
        return total