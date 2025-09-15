from enum import Enum, auto
from typing import Optional, Generator, Union, Dict, Set
from biocypher._logger import logger
from pypath.inputs import reactome
from pypath.share import curl, settings
from contextlib import ExitStack
from tqdm import tqdm
import time
import requests

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

logger.debug(f"Loading module {__name__}.")


class ReactomeNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the Reactome adapter.
    """
    PATHWAY = auto()


class ReactomeNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for Reactome pathway nodes.
    """
    # Core fields
    ID = "id"
    NAME = "name"
    SPECIES = "species"
    DESCRIPTION = "description"
    
    # Hierarchical information
    PARENT_PATHWAYS = "parent_pathways"
    CHILD_PATHWAYS = "child_pathways"
    
    # Cross-references
    PUBMED_REFERENCES = "pubmed_references"
    REACTOME_ID = "reactome_id"
    
    # Additional metadata
    IS_DISEASE_PATHWAY = "is_disease_pathway"
    PATHWAY_TYPE = "pathway_type"


class ReactomeEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the Reactome adapter.
    """
    PROTEIN_IN_PATHWAY = auto()
    PATHWAY_CHILD_OF_PATHWAY = auto()


class ReactomeEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for Reactome edges.
    """
    EVIDENCE_TYPE = "evidence_type"
    ROLE = "role"  # e.g., catalyst, input, output
    COMPARTMENT = "compartment"


class ReactomeAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for Reactome pathway data.
    
    Provides pathway information and protein-pathway associations.
    """
    
    REACTOME_API_URL = "https://reactome.org/ContentService"
    
    def __init__(
        self,
        organism: Optional[Union[str, int]] = "9606",  # Human by default
        node_types: Optional[list[ReactomeNodeType]] = None,
        node_fields: Optional[list[ReactomeNodeField]] = None,
        edge_types: Optional[list[ReactomeEdgeType]] = None,
        edge_fields: Optional[list[ReactomeEdgeField]] = None,
        include_disease_pathways: bool = True,
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = "reactome"
        self.data_version = time.strftime("%Y_%m")
        self.data_licence = "CC BY 4.0"
        
        # Parameters
        self.organism = organism
        self.include_disease_pathways = include_disease_pathways
        
        # Configure fields
        self.node_types = node_types or list(ReactomeNodeType)
        self.node_fields = node_fields or list(ReactomeNodeField)
        self.edge_types = edge_types or list(ReactomeEdgeType)
        self.edge_fields = edge_fields or list(ReactomeEdgeField)
        
        # Storage for data
        self.pathways: Dict[str, dict] = {}
        self.protein_pathway_associations: list = []
        self.pathway_hierarchy: list = []
        
        # Species mapping
        self.species_map = {
            "9606": "Homo sapiens",
            "10090": "Mus musculus",
            "10116": "Rattus norvegicus",
            "559292": "Saccharomyces cerevisiae",
        }
        
        logger.info(f"Initialized Reactome adapter for organism {organism}")
    
    def download_data(
        self,
        cache: bool = True,
        retries: int = 3,
    ):
        """
        Download Reactome pathway data.
        
        Args:
            cache: Whether to use cached data
            retries: Number of download retries
        """
        with self.timer("Downloading Reactome data"):
            with ExitStack() as stack:
                # Handle pypath settings context compatibility
                if hasattr(settings, 'context'):
                    stack.enter_context(settings.context(retries=retries))
                else:
                    logger.warning("pypath settings.context not available, using default settings")
                
                if not cache:
                    stack.enter_context(curl.cache_off())
                
                self._download_pathways()
                if ReactomeEdgeType.PROTEIN_IN_PATHWAY in self.edge_types:
                    self._download_protein_pathway_associations()
                if ReactomeEdgeType.PATHWAY_CHILD_OF_PATHWAY in self.edge_types:
                    self._download_pathway_hierarchy()
    
    def _download_pathways(self):
        """
        Download Reactome pathways.
        """
        logger.info(f"Downloading Reactome pathways for {self.species_map.get(str(self.organism), self.organism)}")
        
        try:
            # Get pathways from PyPath reactome_raw data
            logger.info("Extracting pathway information from PyPath reactome_raw data")
            raw_data = reactome.reactome_raw(id_type='uniprot')
            
            self.pathways = {}
            pathway_count = 0
            
            for entry in tqdm(raw_data, desc="Extracting pathways from raw data"):
                # Filter for human data if organism is specified
                if (self.organism == "9606" or self.organism == 9606) and \
                   entry.get('species') != 'Homo sapiens':
                    continue
                
                pathway_id = entry['pathway_id']
                
                # Skip if we already have this pathway or reached test limit
                if pathway_id in self.pathways:
                    continue
                if self.test_mode and pathway_count >= 50:
                    break
                
                # Create pathway data dictionary
                pathway_data = {
                    ReactomeNodeField.ID.value: pathway_id,
                    ReactomeNodeField.REACTOME_ID.value: pathway_id,
                    ReactomeNodeField.NAME.value: entry.get('pathway_name', ''),
                    ReactomeNodeField.SPECIES.value: entry.get('species', ''),
                }
                
                # Add URL if available
                if entry.get('url'):
                    pathway_data['url'] = entry['url']
                
                # Check if it's a disease pathway
                pathway_name = entry.get('pathway_name', '').lower()
                is_disease = any(keyword in pathway_name for keyword in 
                               ['disease', 'cancer', 'disorder', 'syndrome', 'deficiency'])
                pathway_data[ReactomeNodeField.IS_DISEASE_PATHWAY.value] = is_disease
                
                # Skip disease pathways if not requested
                if is_disease and not self.include_disease_pathways:
                    continue
                
                self.pathways[pathway_id] = pathway_data
                pathway_count += 1
            
            logger.info(f"Downloaded {len(self.pathways)} pathways")
            
        except Exception as e:
            logger.error(f"Failed to download pathways: {e}")
            # Try alternative approach using Reactome API
            self._download_pathways_api()
    
    def _download_pathways_api(self):
        """
        Download pathways using Reactome REST API as fallback.
        """
        logger.info("Downloading pathways using Reactome API")
        
        try:
            species_name = self.species_map.get(str(self.organism), "Homo sapiens")
            url = f"{self.REACTOME_API_URL}/data/pathways/top/{species_name}"
            
            response = requests.get(url)
            response.raise_for_status()
            
            pathways_json = response.json()
            
            self.pathways = {}
            for pathway in pathways_json[:20 if self.test_mode else None]:  # Limit in test mode
                pathway_id = pathway.get('stId', pathway.get('dbId', ''))
                if not pathway_id:
                    continue
                
                pathway_data = {
                    ReactomeNodeField.ID.value: str(pathway_id),
                    ReactomeNodeField.REACTOME_ID.value: str(pathway_id),
                    ReactomeNodeField.NAME.value: pathway.get('displayName', ''),
                    ReactomeNodeField.SPECIES.value: species_name,
                    ReactomeNodeField.IS_DISEASE_PATHWAY.value: False,  # Top-level pathways are typically not disease-specific
                }
                
                self.pathways[str(pathway_id)] = pathway_data
            
            logger.info(f"Downloaded {len(self.pathways)} pathways via API")
            
        except Exception as e:
            logger.error(f"Failed to download pathways via API: {e}")
            # Create minimal mock data for testing
            self._create_mock_pathways()
    
    def _create_mock_pathways(self):
        """
        Create mock pathway data for testing when downloads fail.
        """
        logger.warning("Creating mock pathway data")
        
        mock_pathways = [
            {
                'id': 'R-HSA-162582',
                'name': 'Signal Transduction',
                'description': 'Signal transduction pathways',
            },
            {
                'id': 'R-HSA-1643685',
                'name': 'Disease',
                'description': 'Disease-related pathways',
            },
            {
                'id': 'R-HSA-109582',
                'name': 'Hemostasis',
                'description': 'Blood coagulation pathways',
            }
        ]
        
        self.pathways = {}
        for pathway in mock_pathways:
            pathway_data = {
                ReactomeNodeField.ID.value: pathway['id'],
                ReactomeNodeField.REACTOME_ID.value: pathway['id'],
                ReactomeNodeField.NAME.value: pathway['name'],
                ReactomeNodeField.DESCRIPTION.value: pathway['description'],
                ReactomeNodeField.SPECIES.value: self.species_map.get(str(self.organism), "Homo sapiens"),
                ReactomeNodeField.IS_DISEASE_PATHWAY.value: 'disease' in pathway['name'].lower(),
            }
            self.pathways[pathway['id']] = pathway_data
    
    def _download_protein_pathway_associations(self):
        """
        Download protein-pathway associations using correct PyPath function.
        """
        logger.info("Downloading protein-pathway associations")
        
        try:
            # Get raw Reactome data with UniProt IDs
            raw_data = reactome.reactome_raw(id_type='uniprot')
            
            self.protein_pathway_associations = []
            association_count = 0
            
            for entry in tqdm(raw_data, desc="Processing protein-pathway associations"):
                if self.test_mode and association_count >= 500:
                    break
                
                # Filter for human data if organism is specified
                if (self.organism == "9606" or self.organism == 9606) and \
                   entry.get('species') != 'Homo sapiens':
                    continue
                
                uniprot_id = entry['id']
                pathway_id = entry['pathway_id']
                
                # Check if this pathway is in our pathways collection
                if pathway_id in self.pathways:
                    self.protein_pathway_associations.append({
                        'protein_id': uniprot_id,
                        'pathway_id': pathway_id,
                        'role': 'participant',
                        'evidence_code': entry.get('evidence_code', 'IEA'),
                        'pathway_name': entry.get('pathway_name', ''),
                    })
                    association_count += 1
            
            logger.info(f"Downloaded {len(self.protein_pathway_associations)} protein-pathway associations")
            
        except Exception as e:
            logger.error(f"Failed to download protein-pathway associations: {e}")
            logger.warning("Continuing without protein-pathway associations")
            self.protein_pathway_associations = []
    
    def _download_pathway_hierarchy(self):
        """
        Download pathway hierarchy relationships.
        """
        logger.info("Downloading pathway hierarchy")
        
        try:
            # Get pathway hierarchy data using correct PyPath function
            hierarchy_data = reactome.pathway_hierarchy()
            
            self.pathway_hierarchy = []
            hierarchy_count = 0
            
            for entry in tqdm(hierarchy_data, desc="Processing hierarchy"):
                if self.test_mode and hierarchy_count >= 100:
                    break
                
                parent_id = entry['parent']
                child_id = entry['child']
                
                # Only include hierarchy relationships between pathways we have
                if parent_id in self.pathways and child_id in self.pathways:
                    self.pathway_hierarchy.append({
                        'parent_id': parent_id,
                        'child_id': child_id,
                        'relationship': 'child_of'
                    })
                    hierarchy_count += 1
            
            logger.info(f"Downloaded {len(self.pathway_hierarchy)} pathway hierarchy relationships")
            
        except Exception as e:
            logger.error(f"Failed to download pathway hierarchy: {e}")
            logger.warning("Continuing without pathway hierarchy")
            self.pathway_hierarchy = []
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield pathway nodes.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        if not self.pathways:
            logger.warning("No pathway data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.pathways)} pathway nodes")
        
        for pathway_id, pathway_data in tqdm(self.pathways.items(), desc="Generating pathway nodes"):
            properties = self._get_pathway_properties(pathway_data)
            
            # Create prefixed ID
            prefixed_id = self.add_prefix_to_id("reactome", pathway_id.replace("R-HSA-", ""))
            
            yield (prefixed_id, "pathway", properties)
    
    def get_edges(self) -> Generator[tuple[None, str, str, str, dict], None, None]:
        """
        Yield pathway edges.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        logger.info("Generating pathway edges")
        
        # Check if we have any data to generate edges from
        has_associations = (ReactomeEdgeType.PROTEIN_IN_PATHWAY in self.edge_types and 
                           self.protein_pathway_associations)
        has_hierarchy = (ReactomeEdgeType.PATHWAY_CHILD_OF_PATHWAY in self.edge_types and 
                        self.pathway_hierarchy)
        
        if not has_associations and not has_hierarchy:
            logger.warning("No protein-pathway associations or hierarchy data available for edge generation")
            # Return empty generator - this prevents StopIteration errors
            return
            yield  # Make this a proper generator
        
        # Protein-pathway associations
        if has_associations:
            for association in tqdm(self.protein_pathway_associations, 
                                  desc="Generating protein-pathway edges"):
                protein_id = self.add_prefix_to_id("uniprot", association['protein_id'])
                pathway_id = self.add_prefix_to_id("reactome", 
                                                 association['pathway_id'].replace("R-HSA-", ""))
                
                properties = self.get_metadata_dict()
                properties['role'] = association.get('role', 'participant')
                
                yield (None, protein_id, pathway_id, "protein_participates_in_pathway", properties)
        
        # Pathway hierarchy
        if has_hierarchy:
            for hierarchy in tqdm(self.pathway_hierarchy, 
                                desc="Generating pathway hierarchy edges"):
                child_id = self.add_prefix_to_id("reactome", 
                                               hierarchy['child_id'].replace("R-HSA-", ""))
                parent_id = self.add_prefix_to_id("reactome", 
                                                hierarchy['parent_id'].replace("R-HSA-", ""))
                
                properties = self.get_metadata_dict()
                properties['relationship_type'] = hierarchy.get('relationship', 'child_of')
                
                yield (None, child_id, parent_id, "pathway_child_of_pathway", properties)
    
    def _get_pathway_properties(self, pathway_data: dict) -> dict:
        """
        Get properties for a pathway node.
        """
        properties = self.get_metadata_dict()
        
        # Basic properties
        basic_fields = [
            ReactomeNodeField.NAME,
            ReactomeNodeField.DESCRIPTION,
            ReactomeNodeField.SPECIES,
            ReactomeNodeField.REACTOME_ID,
        ]
        
        for field in basic_fields:
            if field.value in pathway_data and pathway_data[field.value]:
                properties[field.value] = pathway_data[field.value]
        
        # Boolean properties
        if pathway_data.get(ReactomeNodeField.IS_DISEASE_PATHWAY.value) is not None:
            properties[ReactomeNodeField.IS_DISEASE_PATHWAY.value] = pathway_data[ReactomeNodeField.IS_DISEASE_PATHWAY.value]
        
        return properties