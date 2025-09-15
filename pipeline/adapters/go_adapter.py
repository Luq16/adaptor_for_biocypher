from enum import Enum, auto
from typing import Optional, Generator, Union, Dict, Set
from biocypher._logger import logger
from pypath.inputs import go as go_input
from pypath.utils import go as go_util
from pypath.share import curl, settings
from contextlib import ExitStack
from tqdm import tqdm
import time
import os

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

logger.debug(f"Loading module {__name__}.")


class GONodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the Gene Ontology adapter.
    """
    GO_TERM = auto()


class GONodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for GO term nodes.
    """
    # Core fields
    ID = "id"
    NAME = "name"
    NAMESPACE = "namespace"
    DEFINITION = "definition"
    SYNONYMS = "synonyms"
    
    # Relationships
    IS_A = "is_a"
    PART_OF = "part_of"
    REGULATES = "regulates"
    POSITIVELY_REGULATES = "positively_regulates"
    NEGATIVELY_REGULATES = "negatively_regulates"
    
    # Additional properties
    IS_OBSOLETE = "is_obsolete"
    REPLACED_BY = "replaced_by"
    CONSIDER = "consider"
    SUBSET = "subset"
    
    # Cross-references
    XREFS = "xrefs"


class GOEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the Gene Ontology adapter.
    """
    PROTEIN_TO_GO_TERM = auto()
    GO_TERM_IS_A_GO_TERM = auto()
    GO_TERM_PART_OF_GO_TERM = auto()
    GO_TERM_REGULATES_GO_TERM = auto()


class GOEdgeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for GO edges.
    """
    EVIDENCE_CODE = "evidence_code"
    REFERENCE = "reference"
    QUALIFIER = "qualifier"
    ASPECT = "aspect"
    WITH_OR_FROM = "with_or_from"
    ASSIGNED_BY = "assigned_by"


class GOAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for Gene Ontology data.
    
    Provides GO terms, their hierarchical relationships, and protein annotations.
    """
    
    def __init__(
        self,
        organism: Optional[Union[str, int]] = "9606",  # Human by default
        node_types: Optional[list[GONodeType]] = None,
        node_fields: Optional[list[GONodeField]] = None,
        edge_types: Optional[list[GOEdgeType]] = None,
        edge_fields: Optional[list[GOEdgeField]] = None,
        go_aspects: Optional[list[str]] = None,  # ['P', 'F', 'C'] for all aspects
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = "gene_ontology"
        self.data_version = time.strftime("%Y_%m")
        self.data_licence = "CC BY 4.0"
        
        # Parameters
        self.organism = organism
        self.go_aspects = go_aspects or ['P', 'F', 'C']  # Process, Function, Component
        
        # Configure fields
        self.node_types = node_types or list(GONodeType)
        self.node_fields = node_fields or list(GONodeField)
        self.edge_types = edge_types or list(GOEdgeType)
        self.edge_fields = edge_fields or list(GOEdgeField)
        
        # Storage for data
        self.go_terms: Dict[str, dict] = {}
        self.go_annotations: Dict[str, list] = {}  # protein_id -> list of GO annotations
        self.go_relationships: list = []
        
        logger.info(f"Initialized GO adapter for organism {organism}")
    
    def download_data(
        self,
        cache: bool = True,
        retries: int = 3,
    ):
        """
        Download Gene Ontology data.
        
        Args:
            cache: Whether to use cached data
            retries: Number of download retries
        """
        with self.timer("Downloading Gene Ontology data"):
            with ExitStack() as stack:
                # Handle pypath settings context compatibility
                if hasattr(settings, 'context'):
                    stack.enter_context(settings.context(retries=retries))
                else:
                    logger.warning("pypath settings.context not available, using default settings")
                
                if not cache:
                    stack.enter_context(curl.cache_off())
                
                self._download_go_ontology()
                if GOEdgeType.PROTEIN_TO_GO_TERM in self.edge_types:
                    self._download_go_annotations()
    
    def _download_go_ontology(self):
        """
        Download GO ontology structure.
        """
        logger.info("Downloading GO ontology structure")
        
        # Get GO ontology using reliable function
        try:
            # Download GO annotations using pypath get_go_quick
            logger.info("Fetching GO annotations from pypath")
            # Convert organism to integer if it's a string
            organism_id = int(self.organism) if isinstance(self.organism, str) else self.organism
            go_data = go_input.get_go_quick(organism=organism_id)
            
            # Convert to expected format for processing
            self._process_go_data_from_pypath(go_data)
            
        except Exception as e:
            logger.error(f"Failed to download GO ontology: {e}")
            raise
    
    def _download_go_annotations(self):
        """
        Download GO annotations for proteins.
        """
        logger.info(f"Downloading GO annotations for organism {self.organism}")
        
        try:
            # Get GO annotations for the specified organism
            annotations = go_input.go_annotations_uniprot(organism=self.organism)
            
            # Process annotations
            self._process_go_annotations(annotations)
            
        except Exception as e:
            logger.error(f"Failed to download GO annotations: {e}")
            # Continue without annotations if they fail
            logger.warning("Continuing without GO annotations")
    
    def _process_go_data_from_pypath(self, go_data):
        """
        Process GO data from pypath get_go_quick format.
        """
        logger.info("Processing GO data from pypath")
        
        self.go_terms = {}
        self.go_annotations = {}
        
        # Extract GO names dictionary
        go_names = go_data.get('names', {})
        
        # Extract GO terms and annotations for each aspect
        terms_data = go_data.get('terms', {})
        
        # Collect all unique GO terms
        all_go_terms = set()
        for aspect in ['C', 'F', 'P']:  # Cellular Component, Function, Process
            aspect_terms = terms_data.get(aspect, {})
            for protein_id, go_term_set in aspect_terms.items():
                all_go_terms.update(go_term_set)
                
                # Store annotations
                if protein_id not in self.go_annotations:
                    self.go_annotations[protein_id] = []
                
                for go_term in go_term_set:
                    self.go_annotations[protein_id].append({
                        'go_term': go_term,
                        'aspect': aspect,
                        'evidence_code': 'IEA',  # Default from get_go_quick
                    })
        
        # Create GO term entries
        term_count = 0
        aspect_map = {
            'C': 'cellular_component',
            'F': 'molecular_function', 
            'P': 'biological_process'
        }
        
        for go_id in tqdm(all_go_terms, desc="Processing GO terms"):
            if self.test_mode and term_count >= 100:
                break
            
            # Determine aspect from GO ID or use default
            aspect = 'P'  # Default to biological process
            
            self.go_terms[go_id] = {
                GONodeField.ID.value: go_id,
                GONodeField.NAME.value: go_names.get(go_id, ''),
                GONodeField.NAMESPACE.value: aspect_map.get(aspect, 'biological_process'),
                GONodeField.DEFINITION.value: '',  # Not available in get_go_quick
                GONodeField.IS_OBSOLETE.value: False,
                GONodeField.SYNONYMS.value: [],
            }
            
            term_count += 1
        
        logger.info(f"Processed {len(self.go_terms)} GO terms")
        logger.info(f"Processed GO annotations for {len(self.go_annotations)} proteins")
    
    def _process_go_terms_from_pypath(self, go_terms_data):
        """
        Process GO terms from pypath format.
        """
        logger.info("Processing GO terms from pypath")
        
        self.go_terms = {}
        
        # Process terms from pypath data
        processed_count = 0
        for term_data in tqdm(go_terms_data, desc="Processing GO terms"):
            try:
                # Extract basic term information
                term_id = term_data.get('go_id', '')
                if not term_id:
                    continue
                
                # Filter by aspect if specified
                aspect = term_data.get('aspect', '').upper()
                if aspect and aspect not in self.go_aspects:
                    continue
                
                # Skip obsolete terms unless specifically requested
                if term_data.get('is_obsolete', False):
                    continue
                
                # Create term dictionary
                term_dict = {
                    GONodeField.ID.value: term_id,
                    GONodeField.NAME.value: term_data.get('name', ''),
                    GONodeField.NAMESPACE.value: term_data.get('namespace', ''),
                    GONodeField.DEFINITION.value: term_data.get('definition', ''),
                    GONodeField.IS_OBSOLETE.value: term_data.get('is_obsolete', False),
                }
                
                # Add synonyms if available
                if 'synonyms' in term_data and term_data['synonyms']:
                    term_dict[GONodeField.SYNONYMS.value] = term_data['synonyms']
                
                self.go_terms[term_id] = term_dict
                processed_count += 1
                
                # Stop if in test mode and we have enough terms
                if self.test_mode and processed_count >= 100:
                    break
                    
            except Exception as e:
                logger.debug(f"Skipping GO term due to error: {e}")
                continue
        
        logger.info(f"Processed {len(self.go_terms)} GO terms")
    
    def _process_go_terms(self, go_ontology):
        """
        Process GO terms from ontology.
        """
        logger.info("Processing GO terms")
        
        self.go_terms = {}
        
        # Extract terms from ontology
        for term_id, term_data in tqdm(go_ontology.items(), desc="Processing GO terms"):
            # Filter by aspect if specified
            aspect = getattr(term_data, 'namespace', '').upper()
            if aspect and aspect[0] not in self.go_aspects:
                continue
            
            # Skip obsolete terms unless specifically requested
            if getattr(term_data, 'is_obsolete', False):
                continue
            
            # Create term data
            term_dict = {
                GONodeField.ID.value: term_id,
                GONodeField.NAME.value: getattr(term_data, 'name', ''),
                GONodeField.NAMESPACE.value: getattr(term_data, 'namespace', ''),
                GONodeField.DEFINITION.value: getattr(term_data, 'definition', ''),
                GONodeField.IS_OBSOLETE.value: getattr(term_data, 'is_obsolete', False),
            }
            
            # Add synonyms if available
            if hasattr(term_data, 'synonyms') and term_data.synonyms:
                term_dict[GONodeField.SYNONYMS.value] = list(term_data.synonyms)
            
            # Add subsets if available
            if hasattr(term_data, 'subsets') and term_data.subsets:
                term_dict[GONodeField.SUBSET.value] = list(term_data.subsets)
            
            # Add cross-references if available
            if hasattr(term_data, 'xrefs') and term_data.xrefs:
                term_dict[GONodeField.XREFS.value] = list(term_data.xrefs)
            
            self.go_terms[term_id] = term_dict
            
            # Stop if in test mode and we have enough terms
            if self.test_mode and len(self.go_terms) >= 100:
                break
        
        logger.info(f"Processed {len(self.go_terms)} GO terms")
    
    def _process_go_relationships(self, go_ontology):
        """
        Process relationships between GO terms.
        """
        logger.info("Processing GO relationships")
        
        self.go_relationships = []
        
        for term_id, term_data in tqdm(go_ontology.items(), desc="Processing relationships"):
            if term_id not in self.go_terms:
                continue
            
            # Process is_a relationships
            if hasattr(term_data, 'is_a') and term_data.is_a:
                for parent_id in term_data.is_a:
                    if parent_id in self.go_terms:
                        self.go_relationships.append({
                            'source': term_id,
                            'target': parent_id,
                            'type': 'is_a',
                            'edge_type': GOEdgeType.GO_TERM_IS_A_GO_TERM,
                        })
            
            # Process part_of relationships
            if hasattr(term_data, 'relationships') and term_data.relationships:
                for rel_type, targets in term_data.relationships.items():
                    if rel_type == 'part_of':
                        for target_id in targets:
                            if target_id in self.go_terms:
                                self.go_relationships.append({
                                    'source': term_id,
                                    'target': target_id,
                                    'type': 'part_of',
                                    'edge_type': GOEdgeType.GO_TERM_PART_OF_GO_TERM,
                                })
                    elif rel_type in ['regulates', 'positively_regulates', 'negatively_regulates']:
                        for target_id in targets:
                            if target_id in self.go_terms:
                                self.go_relationships.append({
                                    'source': term_id,
                                    'target': target_id,
                                    'type': rel_type,
                                    'edge_type': GOEdgeType.GO_TERM_REGULATES_GO_TERM,
                                })
        
        logger.info(f"Processed {len(self.go_relationships)} GO relationships")
    
    def _process_go_annotations(self, annotations):
        """
        Process GO annotations for proteins.
        """
        logger.info("Processing GO annotations")
        
        self.go_annotations = {}
        annotation_count = 0
        
        for protein_id, protein_annotations in tqdm(annotations.items(), desc="Processing annotations"):
            if self.test_mode and annotation_count >= 1000:
                break
            
            processed_annotations = []
            
            for annotation in protein_annotations:
                # Extract annotation data
                go_id = annotation.get('go_id')
                evidence_code = annotation.get('evidence_code', '')
                reference = annotation.get('reference', '')
                qualifier = annotation.get('qualifier', '')
                aspect = annotation.get('aspect', '')
                
                # Only include annotations for GO terms we have
                if go_id and go_id in self.go_terms:
                    processed_annotations.append({
                        'go_id': go_id,
                        'evidence_code': evidence_code,
                        'reference': reference,
                        'qualifier': qualifier,
                        'aspect': aspect,
                    })
                    annotation_count += 1
            
            if processed_annotations:
                self.go_annotations[protein_id] = processed_annotations
        
        logger.info(f"Processed {annotation_count} GO annotations for {len(self.go_annotations)} proteins")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield GO term nodes.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        if not self.go_terms:
            logger.warning("No GO data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.go_terms)} GO term nodes")
        
        for go_id, term_data in tqdm(self.go_terms.items(), desc="Generating GO nodes"):
            properties = self._get_go_term_properties(term_data)
            
            # Create prefixed ID
            prefixed_id = self.add_prefix_to_id("go", go_id.replace("GO:", ""))
            
            yield (prefixed_id, "go_term", properties)
    
    def get_edges(self) -> Generator[tuple[None, str, str, str, dict], None, None]:
        """
        Yield GO edges.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        logger.info("Generating GO edges")
        
        # GO term relationships
        if self.go_relationships:
            for rel in tqdm(self.go_relationships, desc="Generating GO relationships"):
                source_id = self.add_prefix_to_id("go", rel['source'].replace("GO:", ""))
                target_id = self.add_prefix_to_id("go", rel['target'].replace("GO:", ""))
                
                properties = self.get_metadata_dict()
                properties['relationship_type'] = rel['type']
                
                # Determine edge label
                if rel['type'] == 'is_a':
                    edge_label = "go_term_is_a_go_term"
                elif rel['type'] == 'part_of':
                    edge_label = "go_term_part_of_go_term"
                else:
                    edge_label = f"go_term_{rel['type']}_go_term"
                
                yield (None, source_id, target_id, edge_label, properties)
        
        # Protein-GO term annotations
        if (GOEdgeType.PROTEIN_TO_GO_TERM in self.edge_types and 
            self.go_annotations):
            
            for protein_id, annotations in tqdm(
                self.go_annotations.items(), 
                desc="Generating protein-GO annotations"
            ):
                protein_node_id = self.add_prefix_to_id("uniprot", protein_id)
                
                for annotation in annotations:
                    go_id = annotation.get('go_term') or annotation.get('go_id')
                    go_node_id = self.add_prefix_to_id("go", go_id.replace("GO:", ""))
                    
                    properties = self.get_metadata_dict()
                    
                    # Add annotation properties
                    if annotation.get('evidence_code'):
                        properties['evidence_code'] = annotation['evidence_code']
                    if annotation.get('reference'):
                        properties['reference'] = annotation['reference']
                    if annotation.get('qualifier'):
                        properties['qualifier'] = annotation['qualifier']
                    if annotation.get('aspect'):
                        properties['aspect'] = annotation['aspect']
                    
                    yield (None, protein_node_id, go_node_id, "protein_annotated_with_go_term", properties)
    
    def _get_go_term_properties(self, term_data: dict) -> dict:
        """
        Get properties for a GO term node.
        """
        properties = self.get_metadata_dict()
        
        # Basic properties
        for field in [GONodeField.NAME, GONodeField.NAMESPACE, GONodeField.DEFINITION]:
            if field.value in term_data and term_data[field.value]:
                properties[field.value] = term_data[field.value]
        
        # Boolean properties
        if term_data.get(GONodeField.IS_OBSOLETE.value):
            properties[GONodeField.IS_OBSOLETE.value] = term_data[GONodeField.IS_OBSOLETE.value]
        
        # List properties
        for field in [GONodeField.SYNONYMS, GONodeField.SUBSET, GONodeField.XREFS]:
            if field.value in term_data and term_data[field.value]:
                properties[field.value] = term_data[field.value]
        
        return properties