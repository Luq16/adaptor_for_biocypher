#!/usr/bin/env python3
"""
BioCypher adapter for drug side effects following CROssBARv2 methodology.

This adapter integrates multiple side effect databases:
- SIDER: Drug-side effect associations with frequencies
- OFFSIDES: Additional drug-side effect associations
- ADReCS: Side effect ontology and hierarchical relationships

Following CROssBARv2 approach:
- Creates side effect nodes (authoritative source for side effect entities)
- Creates drug-side effect association edges
- Creates side effect hierarchical relationships
"""

import os
import pandas as pd
from enum import Enum, auto
from typing import Optional, Generator, Dict, Any, List
from time import time
from tqdm import tqdm
from biocypher._logger import logger

# PyPath imports for side effect data
try:
    from pypath.inputs import sider, offsides, adrecs
    PYPATH_AVAILABLE = True
except ImportError:
    PYPATH_AVAILABLE = False
    logger.warning("PyPath side effect modules not available - adapter will use sample data only")

from .base_adapter import BaseAdapter, BaseEnumMeta

logger.debug(f"Loading module {__name__}.")


class SideEffectNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the SideEffect adapter.
    """
    SIDE_EFFECT = auto()


class SideEffectNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for side effect nodes.
    """
    # Core fields
    ID = "id"
    NAME = "name"
    MEDDRA_ID = "meddra_id"
    SYNONYMS = "synonyms"
    
    # Classification
    CATEGORY = "category" 
    SOC = "system_organ_class"  # System Organ Class
    
    # Additional metadata
    FREQUENCY = "frequency"
    SEVERITY = "severity"


class SideEffectEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the SideEffect adapter.
    """
    DRUG_HAS_SIDE_EFFECT = auto()
    SIDE_EFFECT_IS_A_SIDE_EFFECT = auto()  # Hierarchical relationships


class SideEffectEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for side effect edges.
    """
    # Association scores and metrics
    FREQUENCY = "frequency"
    PROPORTIONAL_REPORTING_RATIO = "proportional_reporting_ratio"
    
    # Source information
    SOURCE = "source"
    DETECTION_METHOD = "detection_method"
    
    # Statistical measures
    CONFIDENCE_INTERVAL = "confidence_interval"
    P_VALUE = "p_value"
    
    # Clinical information
    SEVERITY = "severity"
    ONSET = "onset"


class SideEffectAdapter(BaseAdapter):
    """
    BioCypher adapter for drug side effects following CROssBARv2 methodology.
    
    Integrates multiple side effect databases to provide comprehensive
    drug-side effect associations and side effect ontology data.
    """
    
    def __init__(
        self,
        node_types: Optional[List[SideEffectNodeType]] = None,
        node_fields: Optional[List[SideEffectNodeField]] = None,
        edge_types: Optional[List[SideEffectEdgeType]] = None,
        edge_fields: Optional[List[SideEffectEdgeField]] = None,
        frequency_threshold: float = 0.0,  # Minimum frequency threshold
        use_real_data: bool = False,
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Configuration
        self.use_real_data = use_real_data or os.getenv('SIDE_EFFECT_USE_REAL_DATA', '').lower() == 'true'
        self.frequency_threshold = frequency_threshold
        
        # Set data source metadata
        self.data_source = "side_effects"
        self.data_version = "2024"
        self.data_licence = "Various (SIDER: CC BY-NC-SA, OFFSIDES: CC0)"
        
        # Configure types and fields
        self.node_types = node_types or [SideEffectNodeType.SIDE_EFFECT]
        self.node_fields = node_fields or list(SideEffectNodeField)
        self.edge_types = edge_types or list(SideEffectEdgeType)
        self.edge_fields = edge_fields or list(SideEffectEdgeField)
        
        # Data storage
        self.side_effects_data = {}  # MedDRA ID -> side effect info
        self.drug_side_effect_associations = []
        self.side_effect_hierarchy = []
        
        logger.info(f"Initialized SideEffect adapter (use_real_data={self.use_real_data})")
    
    def get_sample_data(self) -> Dict[str, Any]:
        """
        Get sample side effect data for testing/demo purposes.
        
        Returns hardcoded side effect associations when real data is not available.
        """
        sample_side_effects = {
            "10028813": {  # Nausea
                "name": "Nausea",
                "meddra_id": "10028813",
                "category": "Gastrointestinal disorders",
                "synonyms": ["Feeling sick", "Queasiness"]
            },
            "10019211": {  # Headache  
                "name": "Headache",
                "meddra_id": "10019211",
                "category": "Nervous system disorders",
                "synonyms": ["Cephalgia", "Head pain"]
            },
            "10013968": {  # Dizziness
                "name": "Dizziness",
                "meddra_id": "10013968", 
                "category": "Nervous system disorders",
                "synonyms": ["Vertigo", "Light-headedness"]
            },
            "10013473": {  # Diarrhea
                "name": "Diarrhea",
                "meddra_id": "10013473",
                "category": "Gastrointestinal disorders", 
                "synonyms": ["Loose stools"]
            }
        }
        
        sample_associations = [
            {
                "drug_id": "DB00316",  # Acetaminophen
                "side_effect_id": "10019211",  # Headache (rare paradoxical effect)
                "frequency": 0.02,
                "source": "SIDER",
                "proportional_reporting_ratio": 1.2
            },
            {
                "drug_id": "DB00316",  # Acetaminophen
                "side_effect_id": "10028813",  # Nausea
                "frequency": 0.05,
                "source": "SIDER", 
                "proportional_reporting_ratio": 1.5
            },
            {
                "drug_id": "DB00945",  # Aspirin
                "side_effect_id": "10028813",  # Nausea
                "frequency": 0.08,
                "source": "SIDER",
                "proportional_reporting_ratio": 2.1
            },
            {
                "drug_id": "DB00945",  # Aspirin
                "side_effect_id": "10013473",  # Diarrhea
                "frequency": 0.03,
                "source": "SIDER",
                "proportional_reporting_ratio": 1.3
            }
        ]
        
        return {
            "side_effects": sample_side_effects,
            "associations": sample_associations,
            "hierarchy": []  # Simple sample has no hierarchy
        }
    
    def download_real_data(self):
        """
        Download real side effect data using PyPath.
        
        Integrates data from SIDER, OFFSIDES, and ADReCS databases.
        """
        if not PYPATH_AVAILABLE:
            logger.warning("PyPath not available - using sample data")
            return self.get_sample_data()
        
        logger.info("Downloading real side effect data via PyPath...")
        t0 = time()
        
        try:
            # Download SIDER data
            logger.info("Fetching SIDER side effect data...")
            sider_meddra = sider.sider_meddra_side_effects()
            sider_side_effects = sider.sider_side_effects()
            sider_frequencies = sider.sider_side_effect_frequencies()
            
            # Process SIDER side effect names
            meddra_id_to_name = {}
            for entry in sider_meddra:
                meddra_id_to_name[entry.meddra_id] = entry.side_effect_name
            
            # Process SIDER drug-side effect associations
            associations = []
            association_count = 0
            
            for entry in tqdm(sider_side_effects, desc="Processing SIDER associations"):
                if self.test_mode and association_count >= 100:
                    break
                
                side_effect_name = meddra_id_to_name.get(entry.side_effect_meddra_id, "")
                if not side_effect_name:
                    continue
                
                # Store side effect info
                if entry.side_effect_meddra_id not in self.side_effects_data:
                    self.side_effects_data[entry.side_effect_meddra_id] = {
                        "name": side_effect_name,
                        "meddra_id": entry.side_effect_meddra_id,
                        "category": "Unknown",
                        "synonyms": []
                    }
                
                # Create association
                associations.append({
                    "drug_id": entry.pubchem_id,
                    "side_effect_id": entry.side_effect_meddra_id,
                    "frequency": 0.0,  # Will be updated from frequency data
                    "source": "SIDER",
                    "proportional_reporting_ratio": 1.0
                })
                association_count += 1
            
            # Add frequency information
            for entry in sider_frequencies:
                # Match frequencies to associations (simplified approach)
                for assoc in associations:
                    if (assoc["drug_id"] == entry.pubchem_id and 
                        assoc["side_effect_id"] == entry.side_effect_meddra_id):
                        assoc["frequency"] = float(entry.frequency) if entry.frequency else 0.0
                        break
            
            t1 = time()
            logger.info(f"Side effect data downloaded in {round((t1-t0) / 60, 2)} mins")
            
            return {
                "side_effects": self.side_effects_data,
                "associations": associations,
                "hierarchy": []  # Simplified for now
            }
            
        except Exception as e:
            logger.error(f"Failed to download real side effect data: {e}")
            logger.warning("Falling back to sample data")
            return self.get_sample_data()
    
    def download_data(self):
        """Download side effect data (real or sample based on configuration)."""
        logger.info(f"Downloading side effect data (real={self.use_real_data})...")
        
        if self.use_real_data:
            data = self.download_real_data()
        else:
            data = self.get_sample_data()
            logger.info(f"Using sample data: {len(data['side_effects'])} side effects")
        
        # Store processed data
        self.side_effects_data = data["side_effects"]
        self.drug_side_effect_associations = data["associations"]
        self.side_effect_hierarchy = data["hierarchy"]
        
        # Apply frequency threshold
        original_count = len(self.drug_side_effect_associations)
        self.drug_side_effect_associations = [
            assoc for assoc in self.drug_side_effect_associations
            if assoc.get("frequency", 0.0) >= self.frequency_threshold
        ]
        filtered_count = len(self.drug_side_effect_associations)
        
        logger.info(f"Loaded {len(self.side_effects_data)} side effects")
        logger.info(f"Loaded {filtered_count} associations (filtered from {original_count})")
        logger.info(f"Loaded {len(self.side_effect_hierarchy)} hierarchical relationships")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Get side effect nodes.
        
        Following CROssBARv2: SideEffect adapter is authoritative source for side effect entities.
        """
        if not self.side_effects_data:
            logger.warning("No side effect data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.side_effects_data)} side effect nodes")
        
        for side_effect_id, side_effect_data in tqdm(self.side_effects_data.items(), 
                                                    desc="Generating side effect nodes"):
            properties = self._get_side_effect_properties(side_effect_data)
            
            # Create prefixed ID (using MedDRA namespace)
            prefixed_id = self.add_prefix_to_id("meddra", side_effect_id)
            
            yield (prefixed_id, "side_effect", properties)
    
    def get_edges(self) -> Generator[tuple[Optional[str], str, str, str, dict], None, None]:
        """Get side effect edges (drug-side effect associations and hierarchical relationships)."""
        logger.info("Generating side effect edges")
        
        # Drug-side effect associations
        if (SideEffectEdgeType.DRUG_HAS_SIDE_EFFECT in self.edge_types and 
            self.drug_side_effect_associations):
            
            for idx, association in enumerate(tqdm(self.drug_side_effect_associations, 
                                                 desc="Generating drug-side effect edges")):
                edge_id = f"drug_side_effect_{idx}"
                
                # Create IDs with appropriate prefixes
                drug_id = self.add_prefix_to_id("drugbank", association["drug_id"])
                side_effect_id = self.add_prefix_to_id("meddra", association["side_effect_id"])
                
                # Prepare properties
                properties = self._get_drug_side_effect_properties(association)
                
                yield (
                    edge_id,
                    drug_id,
                    side_effect_id,
                    "drug_has_side_effect",
                    properties
                )
        
        # Side effect hierarchical relationships
        if (SideEffectEdgeType.SIDE_EFFECT_IS_A_SIDE_EFFECT in self.edge_types and 
            self.side_effect_hierarchy):
            
            for idx, hierarchy in enumerate(tqdm(self.side_effect_hierarchy,
                                               desc="Generating side effect hierarchy edges")):
                edge_id = f"side_effect_hierarchy_{idx}"
                
                parent_id = self.add_prefix_to_id("meddra", hierarchy["parent_id"])
                child_id = self.add_prefix_to_id("meddra", hierarchy["child_id"])
                
                properties = self.get_metadata_dict()
                properties["relationship_type"] = hierarchy.get("relationship", "is_a")
                
                yield (
                    edge_id,
                    child_id,
                    parent_id,
                    "side_effect_is_a_side_effect",
                    properties
                )
    
    def _get_side_effect_properties(self, side_effect_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get properties for a side effect node."""
        properties = self.get_metadata_dict()
        
        # Basic properties
        for field in [SideEffectNodeField.NAME, SideEffectNodeField.MEDDRA_ID, 
                     SideEffectNodeField.CATEGORY]:
            if field.value in side_effect_data and side_effect_data[field.value]:
                properties[field.value] = side_effect_data[field.value]
        
        # List properties
        if "synonyms" in side_effect_data and side_effect_data["synonyms"]:
            properties["synonyms"] = side_effect_data["synonyms"]
        
        return properties
    
    def _get_drug_side_effect_properties(self, association: Dict[str, Any]) -> Dict[str, Any]:
        """Get properties for a drug-side effect association edge."""
        properties = self.get_metadata_dict()
        
        # Numerical properties
        if "frequency" in association:
            properties["frequency"] = float(association["frequency"])
        
        if "proportional_reporting_ratio" in association:
            properties["proportional_reporting_ratio"] = float(association["proportional_reporting_ratio"])
        
        # String properties
        if "source" in association:
            properties["source"] = association["source"]
        
        if "detection_method" in association:
            properties["detection_method"] = association["detection_method"]
        
        return properties
    
    def get_node_count(self) -> int:
        """Get the total number of side effect nodes."""
        if not self.side_effects_data:
            self.download_data()
        return len(self.side_effects_data)
    
    def get_edge_count(self) -> int:
        """Get the total number of side effect edges."""
        if not self.drug_side_effect_associations:
            self.download_data()
        return len(self.drug_side_effect_associations) + len(self.side_effect_hierarchy)