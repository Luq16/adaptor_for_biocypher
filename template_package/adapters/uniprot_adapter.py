from enum import Enum, auto
from typing import Optional, Generator, Union
from biocypher._logger import logger
from pypath.share import curl, settings
from pypath.inputs import uniprot
from pypath.utils import mapping
from contextlib import ExitStack
from tqdm import tqdm
import time
import os

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

logger.debug(f"Loading module {__name__}.")


class UniprotNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the UniProt adapter.
    """
    PROTEIN = auto()
    GENE = auto()
    ORGANISM = auto()


class UniprotNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for UniProt nodes.
    """
    # Protein fields
    LENGTH = "length"
    MASS = "mass"
    ORGANISM_ID = "organism_id"
    ORGANISM_NAME = "organism_name"
    PROTEIN_NAME = "protein_name"
    EC = "ec"
    SEQUENCE = "sequence"
    FUNCTION = "function"
    SUBCELLULAR_LOCATION = "subcellular_location"
    
    # Gene fields
    GENE_NAMES = "gene_names"
    PRIMARY_GENE_NAME = "gene_primary"
    
    # Cross-references
    ENSEMBL_TRANSCRIPT = "xref_ensembl"
    ENTREZ_GENE_ID = "xref_geneid"
    KEGG_ID = "xref_kegg"
    PDB_ID = "xref_pdb"
    
    # Derived fields
    ENSEMBL_GENE_ID = "ensembl_gene_id"


class UniprotEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the UniProt adapter.
    """
    GENE_TO_PROTEIN = auto()
    PROTEIN_TO_ORGANISM = auto()


class UniprotAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for UniProt data.
    
    Fetches protein, gene, and organism data from UniProt using pypath.
    """
    
    def __init__(
        self,
        organism: Optional[Union[str, int]] = "9606",  # Human by default
        reviewed: bool = True,  # SwissProt only by default
        node_types: Optional[list[UniprotNodeType]] = None,
        node_fields: Optional[list[UniprotNodeField]] = None,
        edge_types: Optional[list[UniprotEdgeType]] = None,
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = "uniprot"
        self.data_version = time.strftime("%Y_%m")
        self.data_licence = "CC BY 4.0"
        
        # Parameters
        self.organism = organism
        self.reviewed = reviewed
        
        # Configure fields
        self.node_types = node_types or list(UniprotNodeType)
        self.node_fields = [f.value for f in (node_fields or list(UniprotNodeField))]
        self.edge_types = edge_types or list(UniprotEdgeType)
        
        # Storage for downloaded data
        self.uniprot_ids = set()
        self.data = {}
        
        logger.info(f"Initialized UniProt adapter for organism {organism}")
    
    def download_data(
        self,
        cache: bool = True,
        retries: int = 3,
    ):
        """
        Download UniProt data using pypath.
        
        Args:
            cache: Whether to use cached data
            retries: Number of download retries
        """
        with self.timer("Downloading UniProt data"):
            with ExitStack() as stack:
                # Handle pypath settings context method
                try:
                    if hasattr(settings, 'context'):
                        stack.enter_context(settings.context(retries=retries))
                    else:
                        # Fallback for older pypath versions
                        logger.warning("pypath settings.context not available, using default settings")
                except Exception as e:
                    logger.warning(f"Could not set pypath context: {e}")
                
                # Handle cache settings
                try:
                    if not cache and hasattr(curl, 'cache_off'):
                        stack.enter_context(curl.cache_off())
                except Exception as e:
                    logger.warning(f"Could not disable cache: {e}")
                
                self._download_uniprot_data()
                self._preprocess_data()
    
    def _download_uniprot_data(self):
        """
        Internal method to download UniProt data.
        """
        logger.info(f"Downloading UniProt IDs for organism {self.organism}")
        
        # Get UniProt IDs
        self.uniprot_ids = set(uniprot._all_uniprots(self.organism, self.reviewed))
        
        if self.test_mode:
            test_limit = int(os.environ.get('BIOCYPHER_TEST_LIMIT', 100))
            self.uniprot_ids = set(list(self.uniprot_ids)[:test_limit])
            logger.info(f"Test mode: limiting to {test_limit} proteins")
        
        logger.info(f"Found {len(self.uniprot_ids)} UniProt entries")
        
        # Download data for each field
        for field in tqdm(self.node_fields, desc="Downloading fields"):
            if field in [UniprotNodeField.ENSEMBL_GENE_ID.value]:
                # Skip derived fields
                continue
            
            try:
                if field == UniprotNodeField.SUBCELLULAR_LOCATION.value:
                    result = uniprot.uniprot_locations(self.organism, self.reviewed)
                else:
                    # Use a more specific query with UniProt IDs
                    result = uniprot.uniprot_data(
                        field, 
                        organism=self.organism, 
                        reviewed=self.reviewed
                    )
                
                # Handle empty results
                if result is None or (hasattr(result, '__len__') and len(result) == 0):
                    logger.warning(f"No data retrieved for field {field}")
                    self.data[field] = {}
                else:
                    self.data[field] = result
                    
                logger.debug(f"Downloaded {field} field")
                
            except Exception as e:
                logger.warning(f"Failed to download field {field}: {e}")
                self.data[field] = {}
        
        # Initialize derived fields
        if UniprotNodeField.ENSEMBL_GENE_ID.value in self.node_fields:
            self.data[UniprotNodeField.ENSEMBL_GENE_ID.value] = {}
    
    def _preprocess_data(self):
        """
        Preprocess downloaded data.
        """
        logger.info("Preprocessing UniProt data")
        
        for field in tqdm(self.node_fields, desc="Preprocessing fields"):
            if field == UniprotNodeField.ENSEMBL_GENE_ID.value:
                # Skip - will be derived from transcripts
                continue
            
            # Ensure data is in dictionary format
            field_data = self.data.get(field, {})
            if not isinstance(field_data, dict):
                logger.warning(f"Field {field} data is not in expected dictionary format, skipping preprocessing")
                continue
            
            if field in [
                UniprotNodeField.LENGTH.value,
                UniprotNodeField.MASS.value,
                UniprotNodeField.ORGANISM_ID.value,
            ]:
                # Convert to integers
                for protein, value in field_data.items():
                    if value:
                        try:
                            self.data[field][protein] = int(str(value).replace(",", ""))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Could not convert {field} value for {protein}: {e}")
                            self.data[field][protein] = None
            
            elif field == UniprotNodeField.SUBCELLULAR_LOCATION.value:
                # Process subcellular locations
                for protein, locations in field_data.items():
                    if locations:
                        processed_locs = []
                        for loc in locations:
                            loc_str = str(loc.location).strip("[]'")
                            processed_locs.append(loc_str)
                        self.data[field][protein] = processed_locs
            
            elif field == UniprotNodeField.ENSEMBL_TRANSCRIPT.value:
                # Process Ensembl transcripts and derive gene IDs
                for protein, transcripts in self.data.get(field, {}).items():
                    if transcripts:
                        # Clean transcript IDs
                        transcript_list = self._ensure_iterable(transcripts)
                        clean_transcripts = [t.split(" [")[0] for t in transcript_list]
                        self.data[field][protein] = clean_transcripts
                        
                        # Derive gene IDs if needed
                        if UniprotNodeField.ENSEMBL_GENE_ID.value in self.node_fields:
                            gene_ids = self._get_ensembl_genes(clean_transcripts)
                            if gene_ids:
                                self.data[UniprotNodeField.ENSEMBL_GENE_ID.value][protein] = gene_ids
            
            else:
                # General string cleaning
                for protein, value in self.data.get(field, {}).items():
                    if value:
                        self.data[field][protein] = self._clean_string(str(value))
    
    def _get_ensembl_genes(self, transcript_ids: list) -> list:
        """
        Get Ensembl gene IDs from transcript IDs using pypath mapping.
        """
        gene_ids = set()
        for transcript in transcript_ids:
            # Remove version number if present
            transcript_base = transcript.split(".")[0]
            mapped = mapping.map_name(transcript_base, "enst_biomart", "ensg_biomart")
            if mapped:
                gene_ids.update(mapped)
        return list(gene_ids)
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield nodes from UniProt data.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        if not self.uniprot_ids:
            logger.warning("No UniProt data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating nodes for types: {[t.name for t in self.node_types]}")
        
        # Yield protein nodes
        if UniprotNodeType.PROTEIN in self.node_types:
            for protein_id in tqdm(self.uniprot_ids, desc="Generating protein nodes"):
                properties = self._get_protein_properties(protein_id)
                if properties:
                    prefixed_id = self.add_prefix_to_id("uniprot", protein_id)
                    yield (prefixed_id, "protein", properties)
        
        # Yield gene nodes
        if UniprotNodeType.GENE in self.node_types:
            genes_yielded = set()
            for protein_id in tqdm(self.uniprot_ids, desc="Generating gene nodes"):
                gene_data = self._get_gene_data(protein_id)
                for gene_id, gene_props in gene_data:
                    if gene_id and gene_id not in genes_yielded:
                        genes_yielded.add(gene_id)
                        yield (gene_id, "gene", gene_props)
        
        # Yield organism nodes
        if UniprotNodeType.ORGANISM in self.node_types:
            organisms_yielded = set()
            for protein_id in self.uniprot_ids:
                organism_id, organism_props = self._get_organism_data(protein_id)
                if organism_id and organism_id not in organisms_yielded:
                    organisms_yielded.add(organism_id)
                    yield (organism_id, "organism", organism_props)
    
    def get_edges(self) -> Generator[tuple[None, str, str, str, dict], None, None]:
        """
        Yield edges from UniProt data.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        if not self.uniprot_ids:
            logger.warning("No UniProt data loaded. Call download_data() first.")
            return
        
        logger.info(f"Generating edges for types: {[t.name for t in self.edge_types]}")
        
        edge_props = self.get_metadata_dict()
        
        # Gene to protein edges
        if UniprotEdgeType.GENE_TO_PROTEIN in self.edge_types:
            for protein_id in tqdm(self.uniprot_ids, desc="Generating gene-protein edges"):
                protein_node_id = self.add_prefix_to_id("uniprot", protein_id)
                
                # Try Entrez gene IDs first
                gene_ids = self.data.get(UniprotNodeField.ENTREZ_GENE_ID.value, {}).get(protein_id)
                if gene_ids:
                    for gene_id in self._ensure_iterable(gene_ids):
                        if gene_id:
                            gene_node_id = self.add_prefix_to_id("ncbigene", str(gene_id))
                            yield (None, gene_node_id, protein_node_id, "gene_encodes_protein", edge_props)
                
                # Try Ensembl gene IDs
                elif UniprotNodeField.ENSEMBL_GENE_ID.value in self.data:
                    gene_ids = self.data[UniprotNodeField.ENSEMBL_GENE_ID.value].get(protein_id)
                    if gene_ids:
                        for gene_id in self._ensure_iterable(gene_ids):
                            if gene_id:
                                gene_node_id = self.add_prefix_to_id("ensembl", gene_id)
                                yield (None, gene_node_id, protein_node_id, "gene_encodes_protein", edge_props)
        
        # Protein to organism edges
        if UniprotEdgeType.PROTEIN_TO_ORGANISM in self.edge_types:
            for protein_id in tqdm(self.uniprot_ids, desc="Generating protein-organism edges"):
                protein_node_id = self.add_prefix_to_id("uniprot", protein_id)
                organism_id = self.data.get(UniprotNodeField.ORGANISM_ID.value, {}).get(protein_id)
                
                if organism_id:
                    organism_node_id = self.add_prefix_to_id("ncbitaxon", str(organism_id))
                    yield (None, protein_node_id, organism_node_id, "protein_belongs_to_organism", edge_props)
    
    def _get_protein_properties(self, protein_id: str) -> dict:
        """
        Get properties for a protein node.
        """
        properties = self.get_metadata_dict()
        
        # Map field names to property names
        field_mapping = {
            UniprotNodeField.LENGTH.value: "length",
            UniprotNodeField.MASS.value: "mass_daltons",
            UniprotNodeField.PROTEIN_NAME.value: "name",
            UniprotNodeField.EC.value: "ec_number",
            UniprotNodeField.SEQUENCE.value: "sequence",
            UniprotNodeField.FUNCTION.value: "function",
            UniprotNodeField.SUBCELLULAR_LOCATION.value: "subcellular_locations",
        }
        
        for field, prop_name in field_mapping.items():
            if field in self.data:
                field_data = self.data[field]
                
                # Handle different data formats from pypath
                if isinstance(field_data, dict):
                    if protein_id in field_data:
                        value = field_data[protein_id]
                        if value:
                            properties[prop_name] = value
                elif isinstance(field_data, list):
                    # For list format, we need to implement a different approach
                    # This is a limitation of current pypath data format
                    logger.debug(f"Field {field} is in list format, skipping for protein {protein_id}")
                    continue
                else:
                    logger.debug(f"Field {field} has unexpected format: {type(field_data)}")
                    continue
        
        return properties
    
    def _get_gene_data(self, protein_id: str) -> list[tuple[str, dict]]:
        """
        Get gene data associated with a protein.
        """
        gene_data = []
        
        # Try Entrez gene IDs first
        gene_ids = self.data.get(UniprotNodeField.ENTREZ_GENE_ID.value, {}).get(protein_id)
        if gene_ids:
            for gene_id in self._ensure_iterable(gene_ids):
                if gene_id:
                    properties = self.get_metadata_dict()
                    
                    # Add gene symbol if available
                    gene_name = self.data.get(UniprotNodeField.PRIMARY_GENE_NAME.value, {}).get(protein_id)
                    if gene_name:
                        properties["symbol"] = gene_name
                    
                    gene_node_id = self.add_prefix_to_id("ncbigene", str(gene_id))
                    gene_data.append((gene_node_id, properties))
        
        # Try Ensembl gene IDs if no Entrez IDs
        elif UniprotNodeField.ENSEMBL_GENE_ID.value in self.data:
            gene_ids = self.data[UniprotNodeField.ENSEMBL_GENE_ID.value].get(protein_id)
            if gene_ids:
                for gene_id in self._ensure_iterable(gene_ids):
                    if gene_id:
                        properties = self.get_metadata_dict()
                        
                        # Add gene symbol if available
                        gene_name = self.data.get(UniprotNodeField.PRIMARY_GENE_NAME.value, {}).get(protein_id)
                        if gene_name:
                            properties["symbol"] = gene_name
                        
                        gene_node_id = self.add_prefix_to_id("ensembl", gene_id)
                        gene_data.append((gene_node_id, properties))
        
        return gene_data
    
    def _get_organism_data(self, protein_id: str) -> tuple[str, dict]:
        """
        Get organism data for a protein.
        """
        organism_id = self.data.get(UniprotNodeField.ORGANISM_ID.value, {}).get(protein_id)
        if not organism_id:
            return None, {}
        
        properties = self.get_metadata_dict()
        
        # Add organism name if available
        organism_name = self.data.get(UniprotNodeField.ORGANISM_NAME.value, {}).get(protein_id)
        if organism_name:
            properties["name"] = organism_name
        
        organism_node_id = self.add_prefix_to_id("ncbitaxon", str(organism_id))
        return organism_node_id, properties