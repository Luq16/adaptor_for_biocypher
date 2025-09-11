from enum import Enum, auto
from typing import Optional, Generator, Union
from biocypher._logger import logger
import pronto
from tqdm import tqdm
import requests
import os

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

logger.debug(f"Loading module {__name__}.")


class DiseaseNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the Disease Ontology adapter.
    """
    DISEASE = auto()


class DiseaseNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for disease nodes.
    """
    # Core fields
    ID = "id"
    NAME = "name"
    DEFINITION = "definition"
    SYNONYMS = "synonyms"
    NAMESPACE = "namespace"
    
    # Cross-references
    XREFS = "xrefs"
    UMLS_CUI = "umls_cui"
    MESH_ID = "mesh_id"
    ICD10_CODE = "icd10_code"
    ICD9_CODE = "icd9_code"
    OMIM_ID = "omim_id"
    
    # Ontology structure
    IS_OBSOLETE = "is_obsolete"
    REPLACED_BY = "replaced_by"
    PARENTS = "parents"
    CHILDREN = "children"
    
    # Additional metadata
    SUBSET = "subset"
    CREATED_BY = "created_by"
    CREATION_DATE = "creation_date"


class DiseaseEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the Disease Ontology adapter.
    """
    DISEASE_IS_A_DISEASE = auto()  # Parent-child relationships
    DISEASE_RELATED_TO_DISEASE = auto()  # Other relationships


class DiseaseOntologyAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for Disease Ontology (DO) data.
    
    Fetches disease classifications and relationships from the Disease Ontology.
    """
    
    DO_URL = "https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/doid.obo"
    MONDO_URL = "http://purl.obolibrary.org/obo/mondo.obo"
    
    def __init__(
        self,
        ontology: str = "DO",  # "DO" for Disease Ontology or "MONDO" for Mondo Disease Ontology
        node_types: Optional[list[DiseaseNodeType]] = None,
        node_fields: Optional[list[DiseaseNodeField]] = None,
        edge_types: Optional[list[DiseaseEdgeType]] = None,
        include_obsolete: bool = False,
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = ontology.lower()
        self.data_version = "2024-01"  # Update as needed
        self.data_licence = "CC0 1.0"
        
        # Parameters
        self.ontology_type = ontology.upper()
        self.include_obsolete = include_obsolete
        
        # Configure fields
        self.node_types = node_types or list(DiseaseNodeType)
        self.node_fields = node_fields or list(DiseaseNodeField)
        self.edge_types = edge_types or list(DiseaseEdgeType)
        
        # Storage for ontology
        self.ontology = None
        self.diseases = []
        self.relationships = []
        
        # Set URL based on ontology type
        self.ontology_url = self.MONDO_URL if ontology.upper() == "MONDO" else self.DO_URL
        
        logger.info(f"Initialized Disease Ontology adapter for {self.ontology_type}")
    
    def download_data(self, force_download: bool = False):
        """
        Download and parse disease ontology data.
        
        Args:
            force_download: Force re-download even if cached
        """
        with self.timer(f"Downloading {self.ontology_type} ontology"):
            # Download OBO file
            filename = f"{self.ontology_type.lower()}.obo"
            obo_path = self.download_file(self.ontology_url, filename, force_download)
            
            # Parse ontology
            logger.info(f"Parsing {self.ontology_type} ontology from {obo_path}")
            self.ontology = pronto.Ontology(obo_path)
            
            # Process diseases
            self._process_diseases()
            self._process_relationships()
    
    def _process_diseases(self):
        """
        Process disease terms from the ontology.
        """
        logger.info("Processing disease terms")
        
        self.diseases = []
        
        # Get all terms
        terms = list(self.ontology.terms())
        if self.test_mode:
            terms = terms[:100]
        
        for term in tqdm(terms, desc="Processing diseases"):
            # Skip obsolete terms if not requested
            if term.obsolete and not self.include_obsolete:
                continue
            
            # Extract disease data
            disease_data = {
                DiseaseNodeField.ID.value: term.id,
                DiseaseNodeField.NAME.value: term.name,
                DiseaseNodeField.NAMESPACE.value: term.namespace,
                DiseaseNodeField.IS_OBSOLETE.value: term.obsolete,
            }
            
            # Add definition if available
            if term.definition:
                disease_data[DiseaseNodeField.DEFINITION.value] = term.definition
            
            # Add synonyms
            if term.synonyms:
                disease_data[DiseaseNodeField.SYNONYMS.value] = [
                    syn.description for syn in term.synonyms
                ]
            
            # Process cross-references
            if term.xrefs:
                xrefs = {}
                for xref in term.xrefs:
                    xref_id = str(xref.id)
                    # Parse specific database cross-references
                    if xref_id.startswith("UMLS:"):
                        disease_data[DiseaseNodeField.UMLS_CUI.value] = xref_id.replace("UMLS:", "")
                    elif xref_id.startswith("MESH:"):
                        disease_data[DiseaseNodeField.MESH_ID.value] = xref_id.replace("MESH:", "")
                    elif xref_id.startswith("ICD10CM:"):
                        disease_data[DiseaseNodeField.ICD10_CODE.value] = xref_id.replace("ICD10CM:", "")
                    elif xref_id.startswith("ICD9CM:"):
                        disease_data[DiseaseNodeField.ICD9_CODE.value] = xref_id.replace("ICD9CM:", "")
                    elif xref_id.startswith("OMIM:"):
                        disease_data[DiseaseNodeField.OMIM_ID.value] = xref_id.replace("OMIM:", "")
                    
                    xrefs[xref.id] = str(xref)
                
                disease_data[DiseaseNodeField.XREFS.value] = list(xrefs.keys())
            
            # Add subsets
            if term.subsets:
                # Handle both string and object subsets
                subsets = []
                for s in term.subsets:
                    if hasattr(s, 'name'):
                        subsets.append(s.name)
                    else:
                        subsets.append(str(s))
                disease_data[DiseaseNodeField.SUBSET.value] = subsets
            
            # Add replaced_by if obsolete
            if term.obsolete and hasattr(term, 'replaced_by') and term.replaced_by:
                # Handle both string and object replaced_by
                replaced_by = []
                for t in term.replaced_by:
                    if hasattr(t, 'id'):
                        replaced_by.append(t.id)
                    else:
                        replaced_by.append(str(t))
                disease_data[DiseaseNodeField.REPLACED_BY.value] = replaced_by
            
            self.diseases.append(disease_data)
        
        logger.info(f"Processed {len(self.diseases)} disease terms")
    
    def _process_relationships(self):
        """
        Process relationships between diseases.
        """
        logger.info("Processing disease relationships")
        
        self.relationships = []
        
        terms = list(self.ontology.terms())
        if self.test_mode:
            terms = terms[:100]
        
        for term in tqdm(terms, desc="Processing relationships"):
            if term.obsolete and not self.include_obsolete:
                continue
            
            # Parent-child relationships (is_a)
            for parent in term.superclasses(distance=1, with_self=False):
                if parent.id != term.id:  # Avoid self-loops
                    self.relationships.append({
                        'source': term.id,
                        'target': parent.id,
                        'type': 'is_a',
                        'relationship': DiseaseEdgeType.DISEASE_IS_A_DISEASE
                    })
            
            # Other relationships from term relationships
            if hasattr(term, 'relationships'):
                for rel_type, targets in term.relationships.items():
                    for target in targets:
                        if hasattr(target, 'id'):
                            self.relationships.append({
                                'source': term.id,
                                'target': target.id,
                                'type': rel_type.name,
                                'relationship': DiseaseEdgeType.DISEASE_RELATED_TO_DISEASE
                            })
        
        logger.info(f"Processed {len(self.relationships)} relationships")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield disease nodes.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        if not self.diseases:
            logger.warning("No disease data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.diseases)} disease nodes")
        
        for disease in tqdm(self.diseases, desc="Generating disease nodes"):
            properties = self._get_disease_properties(disease)
            
            # Use appropriate prefix based on ontology
            if self.ontology_type == "MONDO":
                prefix = "mondo"
            else:
                prefix = "doid"
            
            disease_id = disease[DiseaseNodeField.ID.value]
            # Remove prefix from ID if it's already there
            if ":" in disease_id:
                disease_id = disease_id.split(":", 1)[1]
            
            prefixed_id = self.add_prefix_to_id(prefix, disease_id)
            
            yield (prefixed_id, "disease", properties)
    
    def get_edges(self) -> Generator[tuple[None, str, str, str, dict], None, None]:
        """
        Yield disease relationship edges.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        if not self.relationships:
            logger.warning("No relationship data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating {len(self.relationships)} relationship edges")
        
        # Use appropriate prefix based on ontology
        if self.ontology_type == "MONDO":
            prefix = "mondo"
        else:
            prefix = "doid"
        
        for rel in tqdm(self.relationships, desc="Generating relationship edges"):
            # Process IDs
            source_id = rel['source']
            target_id = rel['target']
            
            # Remove prefix if already present
            if ":" in source_id:
                source_id = source_id.split(":", 1)[1]
            if ":" in target_id:
                target_id = target_id.split(":", 1)[1]
            
            source_node_id = self.add_prefix_to_id(prefix, source_id)
            target_node_id = self.add_prefix_to_id(prefix, target_id)
            
            # Determine edge label
            if rel['relationship'] == DiseaseEdgeType.DISEASE_IS_A_DISEASE:
                edge_label = "disease_is_subtype_of_disease"
            else:
                edge_label = f"disease_{rel['type']}_disease"
            
            # Edge properties
            properties = self.get_metadata_dict()
            properties['relationship_type'] = rel['type']
            
            yield (None, source_node_id, target_node_id, edge_label, properties)
    
    def _get_disease_properties(self, disease: dict) -> dict:
        """
        Get properties for a disease node.
        """
        properties = self.get_metadata_dict()
        
        # Basic properties
        basic_fields = [
            DiseaseNodeField.NAME,
            DiseaseNodeField.DEFINITION,
            DiseaseNodeField.NAMESPACE,
            DiseaseNodeField.IS_OBSOLETE,
        ]
        
        for field in basic_fields:
            if field.value in disease and disease[field.value] is not None:
                properties[field.value] = disease[field.value]
        
        # List properties
        list_fields = [
            DiseaseNodeField.SYNONYMS,
            DiseaseNodeField.SUBSET,
            DiseaseNodeField.XREFS,
            DiseaseNodeField.REPLACED_BY,
        ]
        
        for field in list_fields:
            if field.value in disease and disease[field.value]:
                properties[field.value] = disease[field.value]
        
        # Cross-reference IDs
        xref_fields = [
            DiseaseNodeField.UMLS_CUI,
            DiseaseNodeField.MESH_ID,
            DiseaseNodeField.ICD10_CODE,
            DiseaseNodeField.ICD9_CODE,
            DiseaseNodeField.OMIM_ID,
        ]
        
        for field in xref_fields:
            if field.value in disease and disease[field.value]:
                properties[field.value] = disease[field.value]
        
        return properties