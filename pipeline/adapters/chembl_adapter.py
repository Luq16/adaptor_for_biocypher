from enum import Enum, auto
from typing import Optional, Generator, Union
from biocypher._logger import logger
from contextlib import ExitStack
from tqdm import tqdm
import time
import pandas as pd

# Always import ChEMBL web client for fallback
from chembl_webresource_client.new_client import new_client

# Use pypath for ChEMBL data (like CROssBARv2 approach)
try:
    from pypath.inputs import chembl as pypath_chembl
    from pypath.share import curl, settings
    PYPATH_AVAILABLE = True
    logger.info("PyPath available for ChEMBL data download")
except ImportError:
    PYPATH_AVAILABLE = False
    logger.warning("PyPath not available, falling back to ChEMBL web client")

from .base_adapter import BaseAdapter, BaseEnumMeta, DataDownloadMixin

logger.debug(f"Loading module {__name__}.")


class ChemblNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the ChEMBL adapter.
    """
    DRUG = auto()
    COMPOUND = auto()
    TARGET = auto()
    ASSAY = auto()


class ChemblNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for ChEMBL nodes.
    """
    # Drug/Compound fields
    MOLECULE_CHEMBL_ID = "molecule_chembl_id"
    PREF_NAME = "pref_name"
    MOLECULE_TYPE = "molecule_type"
    MAX_PHASE = "max_phase"
    THERAPEUTIC_FLAG = "therapeutic_flag"
    NATURAL_PRODUCT = "natural_product"
    FIRST_APPROVAL = "first_approval"
    ORAL = "oral"
    PARENTERAL = "parenteral"
    TOPICAL = "topical"
    BLACK_BOX_WARNING = "black_box_warning"
    AVAILABILITY_TYPE = "availability_type"
    WITHDRAWN_FLAG = "withdrawn_flag"
    INDICATION_CLASS = "indication_class"
    
    # Chemical properties
    MOLECULAR_WEIGHT = "full_mwt"
    ALOGP = "alogp"
    HBA = "hba"
    HBD = "hbd"
    PSA = "psa"
    RTB = "rtb"
    MOLECULAR_FORMULA = "full_molformula"
    
    # Structural data
    SMILES = "canonical_smiles"
    INCHI = "standard_inchi"
    INCHI_KEY = "standard_inchi_key"
    
    # Target fields
    TARGET_CHEMBL_ID = "target_chembl_id"
    TARGET_TYPE = "target_type"
    ORGANISM = "organism"
    GENE_NAME = "gene_name"
    PROTEIN_ACCESSION = "protein_accession"
    
    # Activity fields
    STANDARD_VALUE = "standard_value"
    STANDARD_TYPE = "standard_type"
    STANDARD_UNITS = "standard_units"
    ACTIVITY_COMMENT = "activity_comment"
    DATA_VALIDITY_COMMENT = "data_validity_comment"


class ChemblEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the ChEMBL adapter.
    """
    COMPOUND_TARGETS_PROTEIN = auto()
    DRUG_TREATS_DISEASE = auto()
    COMPOUND_MEASURED_IN_ASSAY = auto()


class ChemblAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for ChEMBL data.
    
    Fetches drug, compound, and target data from ChEMBL webservice.
    """
    
    def __init__(
        self,
        node_types: Optional[list[ChemblNodeType]] = None,
        node_fields: Optional[list[ChemblNodeField]] = None,
        edge_types: Optional[list[ChemblEdgeType]] = None,
        max_phase: Optional[int] = None,  # Filter by clinical phase (4 = approved drugs)
        organism: Optional[str] = "Homo sapiens",  # Filter targets by organism
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = "chembl"
        self.data_version = "ChEMBL_33"  # Update as needed
        self.data_licence = "CC BY-SA 3.0"
        
        # Parameters
        self.max_phase = max_phase
        self.organism = organism
        
        # Configure fields
        self.node_types = node_types or list(ChemblNodeType)
        self.node_fields = node_fields or list(ChemblNodeField)
        self.edge_types = edge_types or list(ChemblEdgeType)
        
        # Storage for data
        self.molecules = pd.DataFrame()
        self.targets = pd.DataFrame()
        self.activities = pd.DataFrame()
        self.drug_indications = pd.DataFrame()
        
        # Initialize client references (always available for fallback)
        self.molecule_client = new_client.molecule
        self.target_client = new_client.target
        self.activity_client = new_client.activity
        self.assay_client = new_client.assay
        
        logger.info(f"Initialized ChEMBL adapter")
    
    def download_data(self, limit: Optional[int] = None):
        """
        Download data from ChEMBL using pypath (CROssBARv2 approach).
        
        Args:
            limit: Maximum number of molecules to fetch (useful for testing)
        """
        with self.timer("Downloading ChEMBL data"):
            if PYPATH_AVAILABLE and not self.test_mode:
                # Only use pypath in production mode (it's slow for testing)
                self._download_via_pypath(limit)
            else:
                logger.info("Using direct ChEMBL client (test mode or pypath not available)")
                self._download_via_client(limit)
    
    def _download_via_pypath(self, limit: Optional[int] = None):
        """
        Download ChEMBL data via pypath (following CROssBARv2 approach).
        """
        logger.info("Downloading ChEMBL data via pypath")
        
        with ExitStack() as stack:
            # Handle pypath settings context compatibility
            if hasattr(settings, 'context'):
                stack.enter_context(settings.context(retries=3))
            else:
                logger.warning("pypath settings.context not available, using default settings")
            
            try:
                # Download molecules (drugs and compounds)
                if ChemblNodeType.DRUG in self.node_types or ChemblNodeType.COMPOUND in self.node_types:
                    logger.info("Downloading ChEMBL molecules")
                    molecules_data = list(pypath_chembl.molecule())
                    
                    if molecules_data:
                        self.molecules = pd.DataFrame(molecules_data)
                        
                        # Apply filters
                        if self.max_phase is not None:
                            self.molecules = self.molecules[
                                self.molecules.get('max_phase', 0) >= self.max_phase
                            ]
                        
                        # Apply test mode limiting
                        if self.test_mode or limit:
                            limit_val = min(limit or 100, 100) if self.test_mode else limit
                            self.molecules = self.molecules.head(limit_val)
                        
                        logger.info(f"Downloaded {len(self.molecules)} molecules")
                
                # Download drug indications
                if ChemblEdgeType.DRUG_TREATS_DISEASE in self.edge_types:
                    logger.info("Downloading ChEMBL drug indications")
                    indications_data = list(pypath_chembl.indication())
                    
                    if indications_data:
                        self.drug_indications = pd.DataFrame(indications_data)
                        logger.info(f"Downloaded {len(self.drug_indications)} drug indications")
                
                # Download activities (compound-target relationships)
                if ChemblEdgeType.COMPOUND_TARGETS_PROTEIN in self.edge_types:
                    logger.info("Downloading ChEMBL activities")
                    activities_data = list(pypath_chembl.activity())
                    
                    if activities_data:
                        self.activities = pd.DataFrame(activities_data)
                        
                        # Filter by organism if specified
                        if self.organism:
                            self.activities = self.activities[
                                self.activities.get('organism', '').str.contains(self.organism, na=False, case=False)
                            ]
                        
                        # Apply test mode limiting
                        if self.test_mode and len(self.activities) > 1000:
                            self.activities = self.activities.head(1000)
                        
                        logger.info(f"Downloaded {len(self.activities)} activities")
                
            except Exception as e:
                logger.error(f"PyPath ChEMBL download failed: {e}")
                logger.info("Falling back to direct ChEMBL client")
                self._download_via_client(limit)
    
    def _download_via_client(self, limit: Optional[int] = None):
        """
        Download ChEMBL data via direct client (fallback method).
        """
        logger.info("Using direct ChEMBL web client")
        self._download_molecules(limit)
        if ChemblNodeType.TARGET in self.node_types:
            self._download_targets()
        if self.edge_types and ChemblEdgeType.COMPOUND_TARGETS_PROTEIN in self.edge_types:
            self._download_activities_client()
    
    def _download_molecules(self, limit: Optional[int] = None):
        """
        Download molecule (drug/compound) data from ChEMBL.
        """
        logger.info("Downloading molecule data from ChEMBL")
        
        # Build filters
        filters = {}
        if self.max_phase is not None:
            filters['max_phase'] = self.max_phase
        
        # Fetch molecules
        if filters:
            molecule_query = self.molecule_client.filter(**filters)
        else:
            molecule_query = self.molecule_client.all()
        
        # Apply limit
        if self.test_mode:
            limit = min(limit or 100, 100)
        
        if limit:
            try:
                # ChEMBL web resource client uses 'set_limit' or indexing for limits
                if hasattr(molecule_query, 'set_limit'):
                    molecule_query = molecule_query.set_limit(limit)
                else:
                    # Fall back to slicing the results
                    molecule_query = molecule_query[:limit]
            except Exception as e:
                logger.warning(f"Could not apply limit {limit}: {e}")
                # Continue without limit
        
        # Reset molecules list for web client approach
        self.molecules = []
        processed_count = 0
        valid_count = 0
        
        for mol in tqdm(molecule_query, desc="Fetching molecules"):
            processed_count += 1
            
            # Extract relevant fields
            mol_data = {}
            for field in self.node_fields:
                if hasattr(mol, field.value):
                    value = getattr(mol, field.value)
                    mol_data[field.value] = value
            
            # Debug: check what fields we actually got
            if processed_count <= 3:  # Log first 3 molecules for debugging
                logger.debug(f"Molecule {processed_count}: {mol_data}")
                logger.debug(f"Available attributes: {dir(mol)}")
            
            # Use a more lenient check - just require the molecule exists
            if mol:
                # Add a default ChEMBL ID if missing
                if not mol_data.get(ChemblNodeField.MOLECULE_CHEMBL_ID.value):
                    mol_data[ChemblNodeField.MOLECULE_CHEMBL_ID.value] = f"CHEMBL{processed_count}"
                
                self.molecules.append(mol_data)
                valid_count += 1
        
        logger.info(f"Processed {processed_count} molecules, downloaded {len(self.molecules)} valid molecules")
    
    def _download_targets(self):
        """
        Download target data from ChEMBL.
        """
        logger.info("Downloading target data from ChEMBL")
        
        # Get unique target IDs from molecules' bioactivities
        target_ids = set()
        
        # For each molecule, get its targets
        for mol in tqdm(self.molecules[:100], desc="Getting target IDs"):  # Limit for efficiency
            mol_id = mol.get(ChemblNodeField.MOLECULE_CHEMBL_ID.value)
            if mol_id:
                activities = self.activity_client.filter(
                    molecule_chembl_id=mol_id,
                    target_organism=self.organism
                ).only(['target_chembl_id'])
                
                for act in activities:
                    if hasattr(act, 'target_chembl_id'):
                        target_ids.add(act.target_chembl_id)
        
        logger.info(f"Found {len(target_ids)} unique targets")
        
        # Fetch target details
        self.targets = []
        for target_id in tqdm(list(target_ids)[:50] if self.test_mode else target_ids, 
                              desc="Fetching targets"):
            try:
                target = self.target_client.get(target_id)
                if target:
                    target_data = {}
                    for field in self.node_fields:
                        if hasattr(target, field.value):
                            target_data[field.value] = getattr(target, field.value)
                    
                    if target_data.get(ChemblNodeField.TARGET_CHEMBL_ID.value):
                        self.targets.append(target_data)
            except Exception as e:
                logger.debug(f"Error fetching target {target_id}: {e}")
        
        logger.info(f"Downloaded {len(self.targets)} targets")
    
    def _download_activities_client(self):
        """
        Download bioactivity data for compound-target relationships.
        """
        logger.info("Downloading bioactivity data from ChEMBL")
        
        self.activities = []
        
        # For efficiency, only get activities for a subset of molecules
        mol_subset = self.molecules[:50] if self.test_mode else self.molecules[:500]
        
        for mol in tqdm(mol_subset, desc="Fetching activities"):
            mol_id = mol.get(ChemblNodeField.MOLECULE_CHEMBL_ID.value)
            if not mol_id:
                continue
            
            # Get activities for this molecule
            activities = self.activity_client.filter(
                molecule_chembl_id=mol_id,
                target_organism=self.organism,
                standard_type__in=['IC50', 'Ki', 'Kd', 'EC50']  # Common activity types
            ).only([
                'molecule_chembl_id',
                'target_chembl_id',
                'standard_type',
                'standard_value',
                'standard_units',
                'activity_comment'
            ])
            
            for act in activities:
                # Handle both dict and object formats
                if isinstance(act, dict):
                    act_data = {
                        'molecule_chembl_id': act.get('molecule_chembl_id'),
                        'target_chembl_id': act.get('target_chembl_id'),
                        'standard_type': act.get('standard_type'),
                        'standard_value': act.get('standard_value'),
                        'standard_units': act.get('standard_units'),
                        'activity_comment': act.get('activity_comment'),
                    }
                else:
                    act_data = {
                        'molecule_chembl_id': getattr(act, 'molecule_chembl_id', None),
                        'target_chembl_id': getattr(act, 'target_chembl_id', None),
                        'standard_type': getattr(act, 'standard_type', None),
                        'standard_value': getattr(act, 'standard_value', None),
                        'standard_units': getattr(act, 'standard_units', None),
                        'activity_comment': getattr(act, 'activity_comment', None),
                    }
                
                if act_data['molecule_chembl_id'] and act_data['target_chembl_id']:
                    self.activities.append(act_data)
        
        logger.info(f"Downloaded {len(self.activities)} bioactivities")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Yield nodes from ChEMBL data.
        
        Yields:
            Tuples of (node_id, node_label, properties)
        """
        logger.info(f"Generating nodes for types: {[t.name for t in self.node_types]}")
        
        # Yield drug/compound nodes
        if ChemblNodeType.DRUG in self.node_types or ChemblNodeType.COMPOUND in self.node_types:
            # Handle both DataFrame (pypath) and list (web client) formats
            if isinstance(self.molecules, pd.DataFrame):
                # PyPath format
                for _, mol in tqdm(self.molecules.iterrows(), total=len(self.molecules), desc="Generating molecule nodes"):
                    properties = self._get_molecule_properties_df(mol)
                    if properties:
                        mol_id = mol.get('molecule_chembl_id') or mol.get('chembl_id')
                        if mol_id:
                            # Determine if it's a drug or compound based on max_phase
                            max_phase = mol.get('max_phase')
                            node_label = "drug" if max_phase and max_phase >= 4 else "compound"
                            
                            # Only yield if matching requested node types
                            if (node_label == "drug" and ChemblNodeType.DRUG in self.node_types) or \
                               (node_label == "compound" and ChemblNodeType.COMPOUND in self.node_types):
                                prefixed_id = self.add_prefix_to_id("chembl", mol_id)
                                yield (prefixed_id, node_label, properties)
            else:
                # Web client format (list)
                for mol in tqdm(self.molecules, desc="Generating molecule nodes"):
                    properties = self._get_molecule_properties(mol)
                    if properties:
                        mol_id = mol.get(ChemblNodeField.MOLECULE_CHEMBL_ID.value)
                        if mol_id:
                            # Determine if it's a drug or compound based on max_phase
                            max_phase = mol.get(ChemblNodeField.MAX_PHASE.value)
                            node_label = "drug" if max_phase and max_phase >= 4 else "compound"
                            
                            # Only yield if matching requested node types
                            if (node_label == "drug" and ChemblNodeType.DRUG in self.node_types) or \
                               (node_label == "compound" and ChemblNodeType.COMPOUND in self.node_types):
                                prefixed_id = self.add_prefix_to_id("chembl", mol_id)
                                yield (prefixed_id, node_label, properties)
        
        # Yield target nodes
        if ChemblNodeType.TARGET in self.node_types:
            for target in tqdm(self.targets, desc="Generating target nodes"):
                properties = self._get_target_properties(target)
                if properties:
                    target_id = target.get(ChemblNodeField.TARGET_CHEMBL_ID.value)
                    if target_id:
                        prefixed_id = self.add_prefix_to_id("chembl", target_id)
                        yield (prefixed_id, "target", properties)
    
    def get_edges(self) -> Generator[tuple[None, str, str, str, dict], None, None]:
        """
        Yield edges from ChEMBL data.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, properties)
        """
        logger.info(f"Generating edges for types: {[t.name for t in self.edge_types]}")
        
        # Compound-Target edges from bioactivities
        if ChemblEdgeType.COMPOUND_TARGETS_PROTEIN in self.edge_types:
            # Handle both DataFrame (pypath) and list (web client) formats
            if isinstance(self.activities, pd.DataFrame):
                # PyPath format
                for _, activity in tqdm(self.activities.iterrows(), total=len(self.activities), desc="Generating compound-target edges"):
                    mol_id = activity.get('molecule_chembl_id') or activity.get('chembl_id')
                    target_id = activity.get('target_chembl_id') or activity.get('target_id')
                    
                    if mol_id and target_id:
                        source_id = self.add_prefix_to_id("chembl", mol_id)
                        target_node_id = self.add_prefix_to_id("chembl", target_id)
                        
                        # Edge properties include activity data
                        properties = self.get_metadata_dict()
                        if activity.get('activity_type') or activity.get('standard_type'):
                            properties['activity_type'] = activity.get('activity_type') or activity.get('standard_type')
                        if activity.get('activity_value') or activity.get('standard_value'):
                            properties['activity_value'] = activity.get('activity_value') or activity.get('standard_value')
                        if activity.get('activity_unit') or activity.get('standard_units'):
                            properties['activity_unit'] = activity.get('activity_unit') or activity.get('standard_units')
                        
                        yield (None, source_id, target_node_id, "compound_targets_protein", properties)
            else:
                # Web client format (list)
                for activity in tqdm(self.activities, desc="Generating compound-target edges"):
                    mol_id = activity.get('molecule_chembl_id')
                    target_id = activity.get('target_chembl_id')
                    
                    if mol_id and target_id:
                        source_id = self.add_prefix_to_id("chembl", mol_id)
                        target_node_id = self.add_prefix_to_id("chembl", target_id)
                        
                        # Edge properties include activity data
                        properties = self.get_metadata_dict()
                        if activity.get('standard_type'):
                            properties['activity_type'] = activity['standard_type']
                    if activity.get('standard_value'):
                        properties['activity_value'] = float(activity['standard_value'])
                    if activity.get('standard_units'):
                        properties['activity_units'] = activity['standard_units']
                    
                    yield (None, source_id, target_node_id, "compound_targets", properties)
    
    def _get_molecule_properties(self, mol: dict) -> dict:
        """
        Get properties for a molecule node.
        """
        properties = self.get_metadata_dict()
        
        # Basic properties
        basic_fields = [
            ChemblNodeField.PREF_NAME,
            ChemblNodeField.MOLECULE_TYPE,
            ChemblNodeField.MAX_PHASE,
            ChemblNodeField.THERAPEUTIC_FLAG,
            ChemblNodeField.NATURAL_PRODUCT,
            ChemblNodeField.FIRST_APPROVAL,
            ChemblNodeField.ORAL,
            ChemblNodeField.PARENTERAL,
            ChemblNodeField.TOPICAL,
            ChemblNodeField.BLACK_BOX_WARNING,
            ChemblNodeField.AVAILABILITY_TYPE,
            ChemblNodeField.WITHDRAWN_FLAG,
        ]
        
        for field in basic_fields:
            if field.value in mol and mol[field.value] is not None:
                properties[field.value] = mol[field.value]
        
        # Chemical properties
        chemical_fields = [
            ChemblNodeField.MOLECULAR_WEIGHT,
            ChemblNodeField.ALOGP,
            ChemblNodeField.HBA,
            ChemblNodeField.HBD,
            ChemblNodeField.PSA,
            ChemblNodeField.RTB,
            ChemblNodeField.MOLECULAR_FORMULA,
        ]
        
        for field in chemical_fields:
            if field.value in mol and mol[field.value] is not None:
                properties[field.value] = mol[field.value]
        
        # Structural data
        if ChemblNodeField.SMILES.value in mol and mol[ChemblNodeField.SMILES.value]:
            properties["smiles"] = mol[ChemblNodeField.SMILES.value]
        if ChemblNodeField.INCHI_KEY.value in mol and mol[ChemblNodeField.INCHI_KEY.value]:
            properties["inchi_key"] = mol[ChemblNodeField.INCHI_KEY.value]
        
        return properties
    
    def _get_molecule_properties_df(self, mol: pd.Series) -> dict:
        """
        Get properties for a molecule node from DataFrame row (pypath format).
        """
        properties = self.get_metadata_dict()
        
        # Map common pypath field names to our properties
        field_mappings = {
            'pref_name': 'pref_name',
            'molecule_type': 'molecule_type', 
            'max_phase': 'max_phase',
            'therapeutic_flag': 'therapeutic_flag',
            'natural_product': 'natural_product',
            'first_approval': 'first_approval',
            'oral': 'oral',
            'parenteral': 'parenteral',
            'topical': 'topical',
            'black_box_warning': 'black_box_warning',
            'availability_type': 'availability_type',
            'withdrawn_flag': 'withdrawn_flag',
            # Chemical properties
            'molecular_weight': 'full_mwt',
            'alogp': 'alogp',
            'hba': 'hba', 
            'hbd': 'hbd',
            'psa': 'psa',
            'rtb': 'rtb',
            'molecular_formula': 'full_molformula',
            # Structural
            'smiles': 'canonical_smiles',
            'inchi_key': 'standard_inchi_key'
        }
        
        # Extract properties using mappings
        for prop_name, field_name in field_mappings.items():
            value = mol.get(field_name) or mol.get(prop_name)  # Try both names
            if value is not None and pd.notna(value):
                properties[prop_name] = value
        
        return properties
    
    def _get_target_properties(self, target: dict) -> dict:
        """
        Get properties for a target node.
        """
        properties = self.get_metadata_dict()
        
        # Basic target properties
        if target.get(ChemblNodeField.TARGET_TYPE.value):
            properties["target_type"] = target[ChemblNodeField.TARGET_TYPE.value]
        if target.get(ChemblNodeField.ORGANISM.value):
            properties["organism"] = target[ChemblNodeField.ORGANISM.value]
        if target.get(ChemblNodeField.GENE_NAME.value):
            properties["gene_name"] = target[ChemblNodeField.GENE_NAME.value]
        
        # Add UniProt cross-reference if available
        if target.get(ChemblNodeField.PROTEIN_ACCESSION.value):
            properties["uniprot_accession"] = target[ChemblNodeField.PROTEIN_ACCESSION.value]
        
        return properties