from enum import Enum, auto
from typing import Optional, Generator, Union, Dict, Any
from biocypher._logger import logger
import os
import time
import gzip
import json
from pathlib import Path
import requests
from tqdm import tqdm
# Don't import at module level - check at runtime instead
# This prevents import issues between system Python and Poetry environment

def _check_pandas_available():
    """Check if pandas is available at runtime."""
    try:
        import pandas
        return True, pandas
    except ImportError:
        return False, None

def _check_duckdb_available():
    """Check if duckdb is available at runtime."""
    try:
        import duckdb
        return True, duckdb
    except ImportError:
        return False, None

# Import base classes directly to avoid dependency conflicts
from abc import ABC, abstractmethod
from typing import Generator, Optional, Union, Any
from enum import Enum, EnumMeta
from functools import lru_cache
from biocypher._logger import logger
from bioregistry import normalize_curie
import os
import time
from contextlib import contextmanager
from pathlib import Path


class BaseEnumMeta(EnumMeta):
    """Base metaclass for all adapter enums, providing membership checking."""
    def __contains__(cls, item):
        return item in cls.__members__.keys()


class DataDownloadMixin:
    """Mixin class providing data download functionality."""
    
    def download_file(
        self, 
        url: str, 
        filename: str, 
        force_download: bool = False
    ) -> str:
        """Download a file from URL with caching."""
        import requests
        
        filepath = os.path.join(self.cache_dir, filename)
        
        if os.path.exists(filepath) and not force_download:
            logger.info(f"Using cached file: {filepath}")
            return filepath
        
        logger.info(f"Downloading {url} to {filepath}")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Write with streaming to handle large files
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Downloaded successfully: {filepath}")
        return filepath


class BaseAdapter(ABC):
    """Abstract base class for all BioCypher adapters."""
    
    def __init__(
        self,
        add_prefix: bool = True,
        test_mode: bool = False,
        cache_dir: Optional[str] = None,
    ):
        self.add_prefix = add_prefix
        self.test_mode = test_mode
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), ".cache")
        
        # Ensure cache directory exists
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Data source metadata - should be overridden by subclasses
        self.data_source = "unknown"
        self.data_version = "unknown"
        self.data_licence = "unknown"
        
        # Initialize data storage
        self.data = {}
        
        logger.debug(f"Initialized {self.__class__.__name__} adapter")
    
    @abstractmethod
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """Abstract method to get nodes from the data source."""
        pass
    
    @abstractmethod
    def get_edges(self) -> Generator[tuple[Optional[str], str, str, str, dict], None, None]:
        """Abstract method to get edges from the data source."""
        pass
    
    @lru_cache(maxsize=10000)
    def add_prefix_to_id(
        self, 
        prefix: str, 
        identifier: str, 
        sep: str = ":"
    ) -> str:
        """Add prefix to database identifier using bioregistry normalization."""
        if not identifier:
            return None
            
        if self.add_prefix:
            return normalize_curie(f"{prefix}{sep}{identifier}")
        return identifier
    
    def get_metadata_dict(self) -> dict:
        """Get standard metadata dictionary for nodes/edges."""
        return {
            "source": self.data_source,
            "version": self.data_version,
            "licence": self.data_licence,
        }
    
    @contextmanager
    def timer(self, description: str):
        """Context manager for timing operations."""
        start_time = time.time()
        logger.info(f"Starting: {description}")
        yield
        elapsed_time = time.time() - start_time
        logger.info(f"Completed: {description} in {elapsed_time:.2f} seconds")

logger.debug(f"Loading module {__name__}.")


class OpenTargetsNodeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of nodes provided by the OpenTargets adapter.
    """
    TARGET = auto()
    DISEASE = auto()
    GENE_ONTOLOGY = auto()
    MOLECULE = auto()
    MOUSE_MODEL = auto()
    MOUSE_PHENOTYPE = auto()


class OpenTargetsNodeField(Enum, metaclass=BaseEnumMeta):
    """
    Fields available for OpenTargets nodes.
    """
    # Target fields
    TARGET_ID = "id"
    TARGET_SYMBOL = "approvedSymbol"
    TARGET_NAME = "approvedName"
    TARGET_BIOTYPE = "biotype"
    TARGET_CHROMOSOME = "chromosome"
    TARGET_START = "start"
    TARGET_END = "end"
    TARGET_STRAND = "strand"
    
    # Disease fields
    DISEASE_ID = "id"
    DISEASE_NAME = "name"
    DISEASE_DESCRIPTION = "description"
    DISEASE_SYNONYMS = "synonyms"
    DISEASE_ANCESTORS = "ancestors"
    
    # Molecule fields
    MOLECULE_ID = "id"
    MOLECULE_NAME = "name"
    MOLECULE_TYPE = "type"
    MOLECULE_MECHANISM = "mechanismOfAction"
    MOLECULE_MAX_PHASE = "maximumClinicalTrialPhase"
    
    # Gene Ontology fields
    GO_ID = "id"
    GO_NAME = "name"
    GO_NAMESPACE = "namespace"
    GO_DEFINITION = "definition"


class OpenTargetsEdgeType(Enum, metaclass=BaseEnumMeta):
    """
    Types of edges provided by the OpenTargets adapter.
    """
    TARGET_DISEASE_ASSOCIATION = auto()
    TARGET_GO_ASSOCIATION = auto()
    MOLECULE_TARGET_ASSOCIATION = auto()
    MOLECULE_DISEASE_ASSOCIATION = auto()


class OpenTargetsDataset(Enum):
    """
    Available Open Targets datasets.
    """
    TARGETS = "targets"
    DISEASES = "diseases"
    MOLECULES = "molecules"
    GO = "go"
    EVIDENCE = "evidence"
    ASSOCIATIONS = "associationByOverallDirect"
    DISEASE_TO_PHENOTYPE = "diseaseToPhenotype"
    DRUG_WARNINGS = "drugWarnings"
    INTERACTIONS = "interactions"
    MOUSE_PHENOTYPES = "mousePhenotypes"


class OpenTargetsAdapter(BaseAdapter, DataDownloadMixin):
    """
    BioCypher adapter for Open Targets data.
    
    Fetches and processes data from Open Targets Platform datasets.
    Uses streaming approach for memory-efficient processing.
    """
    
    # Open Targets FTP base URL - using latest stable version
    OPENTARGETS_BASE_URL = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/24.09/output/etl/parquet/"
    
    def __init__(
        self,
        node_types: Optional[list[OpenTargetsNodeType]] = None,
        node_fields: Optional[list[OpenTargetsNodeField]] = None,
        edge_types: Optional[list[OpenTargetsEdgeType]] = None,
        datasets: Optional[list[OpenTargetsDataset]] = None,
        use_real_data: bool = False,  # New parameter to fetch real data
        test_mode: bool = False,
        add_prefix: bool = True,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(add_prefix=add_prefix, test_mode=test_mode, cache_dir=cache_dir)
        
        # Set data source metadata
        self.data_source = "opentargets"
        self.data_version = "24.09" if use_real_data else "sample"
        self.data_licence = "Apache 2.0"
        self.use_real_data = use_real_data
        
        # Configure types and fields
        self.node_types = node_types or list(OpenTargetsNodeType)
        self.node_fields = [f.value for f in (node_fields or list(OpenTargetsNodeField))]
        self.edge_types = edge_types or list(OpenTargetsEdgeType)
        self.datasets = datasets or [
            OpenTargetsDataset.TARGETS,
            OpenTargetsDataset.DISEASES,
            OpenTargetsDataset.ASSOCIATIONS,
        ]
        
        # Storage for data processing
        self.nodes_data = {}
        self.edges_data = []
        
        # Set cache subdirectory
        self.cache_dir = os.path.join(self.cache_dir, "opentargets")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Validate availability for real data
        if self.use_real_data:
            duckdb_available, _ = _check_duckdb_available()
            pandas_available, _ = _check_pandas_available()
            
            if duckdb_available:
                logger.info("DuckDB available - will use for optimal Parquet processing")
            elif pandas_available:
                logger.info("Pandas available - will use for Parquet processing (slower than DuckDB)")
                logger.info("For better performance, install DuckDB: poetry add duckdb")
            else:
                logger.warning("Neither pandas nor DuckDB available - will fall back to sample data")
                self.use_real_data = False
        
        logger.info(f"Initialized OpenTargets adapter (real_data={self.use_real_data}) with cache dir: {self.cache_dir}")
    
    def download_dataset(self, dataset: OpenTargetsDataset, force_download: bool = False) -> str:
        """
        Download a dataset from Open Targets.
        
        Args:
            dataset: The dataset to download
            force_download: Force re-download even if cached
            
        Returns:
            Path to the downloaded file
        """
        if not self.use_real_data:
            # Use sample data
            filename = f"{dataset.value}_sample.json"
            filepath = os.path.join(self.cache_dir, filename)
            
            if os.path.exists(filepath) and not force_download:
                logger.info(f"Using cached sample dataset: {filepath}")
                return filepath
            
            logger.info(f"Creating sample {dataset.value} data for demonstration")
            self._create_sample_data(dataset, filepath)
            return filepath
        
        # For real data, first check if we can actually process parquet files
        duckdb_available, _ = _check_duckdb_available()
        pandas_available, _ = _check_pandas_available()
        
        if not pandas_available and not duckdb_available:
            logger.warning("Neither pandas nor DuckDB available in current environment")
            logger.info("Falling back to sample data (install pandas or duckdb for real data)")
            self.use_real_data = False
            return self.download_dataset(dataset, force_download=False)
        
        logger.info(f"Data processing available: pandas={pandas_available}, duckdb={duckdb_available}")
        
        # Download real data from Open Targets
        return self._download_real_dataset(dataset, force_download)
    
    def _download_real_dataset(self, dataset: OpenTargetsDataset, force_download: bool = False) -> str:
        """
        Download real dataset from Open Targets FTP.
        
        Args:
            dataset: The dataset to download
            force_download: Force re-download even if cached
            
        Returns:
            Path to the downloaded parquet file
        """
        # Map dataset enum to actual FTP paths
        dataset_mapping = {
            OpenTargetsDataset.TARGETS: "targets/",
            OpenTargetsDataset.DISEASES: "diseases/", 
            OpenTargetsDataset.ASSOCIATIONS: "associationByOverallDirect/",
            OpenTargetsDataset.MOLECULES: "molecule/",
            OpenTargetsDataset.GO: "go/",
        }
        
        if dataset not in dataset_mapping:
            raise ValueError(f"Unknown dataset: {dataset}")
        
        # Construct download URL
        base_path = dataset_mapping[dataset]
        # Most Open Targets datasets have multiple part files, we'll download the first one
        parquet_filename = f"{dataset.value}.parquet"
        parquet_filepath = os.path.join(self.cache_dir, parquet_filename)
        
        if os.path.exists(parquet_filepath) and not force_download:
            logger.info(f"Using cached real dataset: {parquet_filepath}")
            return parquet_filepath
        
        # Try to download the first part file (part-00000) from each dataset
        # Note: Real filenames have unique UUIDs, so we'll try a generic approach
        if dataset == OpenTargetsDataset.ASSOCIATIONS:
            # Use associationByOverallDirect for the main target-disease associations
            download_url = f"{self.OPENTARGETS_BASE_URL}associationByOverallDirect/"
        elif dataset == OpenTargetsDataset.TARGETS:
            download_url = f"{self.OPENTARGETS_BASE_URL}targets/"
        elif dataset == OpenTargetsDataset.DISEASES:
            download_url = f"{self.OPENTARGETS_BASE_URL}diseases/"
        else:
            download_url = f"{self.OPENTARGETS_BASE_URL}{base_path}"
        
        # Use a more robust approach to find actual parquet files
        try:
            import re
            
            # Get directory listing
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML to find .parquet files
            parquet_pattern = r'href="([^"]*\.snappy\.parquet)"'
            parquet_files = re.findall(parquet_pattern, response.text)
            
            if not parquet_files:
                # Try alternative pattern
                parquet_pattern = r'href="([^"]*\.parquet)"'
                parquet_files = re.findall(parquet_pattern, response.text)
            
            if parquet_files:
                # Use the first parquet file found (typically part-00000)
                actual_filename = sorted(parquet_files)[0]  # Sort to get part-00000 first
                download_url = download_url + actual_filename
                logger.info(f"Found parquet file: {actual_filename}")
            else:
                logger.warning(f"No parquet files found in {download_url}")
                logger.info("Directory contents sample:")
                # Show first few lines for debugging
                lines = response.text.split('\n')[:10]
                for line in lines:
                    if 'href=' in line:
                        logger.info(f"  {line.strip()}")
                raise ValueError("No parquet files found in directory")
                
        except Exception as e:
            logger.error(f"Failed to discover parquet files: {str(e)}")
            logger.info("Falling back to sample data")
            self.use_real_data = False
            return self.download_dataset(dataset, force_download=False)
        
        try:
            logger.info(f"Downloading real Open Targets data from: {download_url}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Download with progress bar
            total_size = int(response.headers.get('content-length', 0))
            with open(parquet_filepath, 'wb') as f, tqdm(
                desc=f"Downloading {dataset.value}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            logger.info(f"Successfully downloaded: {parquet_filepath}")
            return parquet_filepath
            
        except Exception as e:
            logger.error(f"Failed to download real data: {str(e)}")
            logger.info("Falling back to sample data")
            self.use_real_data = False
            return self.download_dataset(dataset, force_download=False)
    
    def _create_sample_data(self, dataset: OpenTargetsDataset, filepath: str):
        """
        Create sample data for demonstration purposes.
        
        Args:
            dataset: The dataset type
            filepath: Path to save the sample data
        """
        sample_data = {
            OpenTargetsDataset.TARGETS: [
                {
                    "id": "ENSG00000139618",
                    "approvedSymbol": "BRCA2",
                    "approvedName": "BRCA2 DNA repair associated",
                    "biotype": "protein_coding",
                    "genomicLocation": {
                        "chromosome": "13",
                        "start": 32315474,
                        "end": 32400266,
                        "strand": 1
                    }
                },
                {
                    "id": "ENSG00000141510",
                    "approvedSymbol": "TP53",
                    "approvedName": "tumor protein p53",
                    "biotype": "protein_coding",
                    "genomicLocation": {
                        "chromosome": "17",
                        "start": 7661779,
                        "end": 7687550,
                        "strand": -1
                    }
                },
                {
                    "id": "ENSG00000133703",
                    "approvedSymbol": "KRAS",
                    "approvedName": "KRAS proto-oncogene, GTPase",
                    "biotype": "protein_coding",
                    "genomicLocation": {
                        "chromosome": "12",
                        "start": 25205246,
                        "end": 25250929,
                        "strand": -1
                    }
                }
            ],
            OpenTargetsDataset.DISEASES: [
                {
                    "id": "EFO_0000305",
                    "name": "breast carcinoma",
                    "description": "A carcinoma that arises from epithelial cells of the breast",
                    "synonyms": ["breast cancer", "mammary carcinoma", "breast tumor"]
                },
                {
                    "id": "EFO_0000684",
                    "name": "lung carcinoma",
                    "description": "A carcinoma that arises from epithelial cells of the lung",
                    "synonyms": ["lung cancer", "pulmonary carcinoma"]
                },
                {
                    "id": "EFO_0005842",
                    "name": "colorectal carcinoma",
                    "description": "A carcinoma that arises from epithelial cells of the colon or rectum",
                    "synonyms": ["colorectal cancer", "CRC"]
                }
            ],
            OpenTargetsDataset.ASSOCIATIONS: [
                {
                    "targetId": "ENSG00000139618",
                    "diseaseId": "EFO_0000305",
                    "score": 0.89,
                    "datasourceScores": {
                        "genetic_association": 0.95,
                        "literature": 0.85,
                        "known_drug": 0.0
                    }
                },
                {
                    "targetId": "ENSG00000141510",
                    "diseaseId": "EFO_0000684",
                    "score": 0.92,
                    "datasourceScores": {
                        "genetic_association": 0.98,
                        "literature": 0.90,
                        "known_drug": 0.0
                    }
                },
                {
                    "targetId": "ENSG00000133703",
                    "diseaseId": "EFO_0005842",
                    "score": 0.88,
                    "datasourceScores": {
                        "genetic_association": 0.91,
                        "literature": 0.87,
                        "known_drug": 0.75
                    }
                }
            ]
        }
        
        # Write sample data as JSON (not gzipped for simplicity)
        data_to_write = sample_data.get(dataset, [])
        logger.info(f"Creating sample data for {dataset}: {len(data_to_write)} items")
        
        with open(filepath, 'w') as f:
            for item in data_to_write:
                json.dump(item, f)
                f.write('\n')
        
        logger.info(f"Wrote sample data to: {filepath}")
    
    def stream_data(self, filepath: str) -> Generator[dict, None, None]:
        """
        Stream data from a file (JSON, Parquet, or gzipped).
        
        Args:
            filepath: Path to the data file
            
        Yields:
            Parsed data objects
        """
        if filepath.endswith('.parquet'):
            # Check availability at runtime
            duckdb_available, duckdb = _check_duckdb_available()
            pandas_available, pandas = _check_pandas_available()
            
            if duckdb_available:
                logger.info("Using DuckDB for Parquet processing")
                conn = duckdb.connect()
                
                # Limit rows in test mode
                limit_clause = "LIMIT 100" if self.test_mode else ""
                query = f"SELECT * FROM '{filepath}' {limit_clause}"
                
                try:
                    result = conn.execute(query)
                    while True:
                        batch = result.fetchmany(1000)  # Process in batches
                        if not batch:
                            break
                        
                        columns = [desc[0] for desc in result.description]
                        for row in batch:
                            yield dict(zip(columns, row))
                finally:
                    conn.close()
                    
            elif pandas_available:
                # Fallback to pandas (works but slower)
                logger.info("Using pandas for Parquet processing (install duckdb for better performance)")
                try:
                    # Read parquet file
                    logger.info(f"Reading parquet file: {filepath}")
                    df = pandas.read_parquet(filepath)
                    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
                    
                    # Limit rows in test mode
                    if self.test_mode and len(df) > 100:
                        original_len = len(df)
                        df = df.head(100)
                        logger.info(f"Test mode: limiting to 100 rows from {original_len} total")
                    
                    # Convert to dictionaries and yield
                    for idx, row in df.iterrows():
                        yield row.to_dict()
                        
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Failed to read Parquet file with pandas: {error_msg}")
                    
                    # Check for specific pyarrow/fastparquet missing error
                    if "pyarrow" in error_msg and "fastparquet" in error_msg:
                        logger.info("💡 Install pyarrow for Parquet support: poetry add pyarrow")
                        logger.info("   Alternative: poetry add fastparquet")
                    else:
                        logger.info(f"Error details: {type(e).__name__}: {error_msg}")
                    
                    logger.info("Falling back to sample data")
                    # Switch to sample data and try again
                    sample_path = filepath.replace('.parquet', '_sample.json')
                    if os.path.exists(sample_path):
                        logger.info(f"Using sample data from: {sample_path}")
                        yield from self.stream_data(sample_path)
                    return
                    
            else:
                # Neither pandas nor DuckDB available
                logger.error("Neither pandas nor DuckDB available for Parquet processing")
                logger.info("Install pandas or duckdb for real data processing")
                # Fall back to sample data
                sample_path = filepath.replace('.parquet', '_sample.json')
                if os.path.exists(sample_path):
                    logger.info(f"Using sample data from: {sample_path}")
                    yield from self.stream_data(sample_path)
                return
        else:
            # Handle JSON files (sample data)
            if filepath.endswith('.gz'):
                open_func = gzip.open
                mode = 'rt'
            else:
                open_func = open
                mode = 'r'
            
            with open_func(filepath, mode) as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)
    
    def process_targets(self):
        """Process targets dataset."""
        if OpenTargetsNodeType.TARGET not in self.node_types:
            return
        
        filepath = self.download_dataset(OpenTargetsDataset.TARGETS)
        logger.info("Processing targets...")
        
        count = 0
        for target in tqdm(self.stream_data(filepath), desc="Targets"):
            if self.test_mode and count >= 100:
                break
            
            # Handle both real data and sample data field names
            target_id = target.get("id") or target.get("targetId")
            node_id = self.add_prefix_to_id("ensembl", target_id)
            
            properties = {
                "symbol": target.get("approvedSymbol") or target.get("symbol"),
                "name": target.get("approvedName") or target.get("name"),
                "biotype": target.get("biotype"),
            }
            
            # Add genomic location if available (real data structure)
            if "genomicLocation" in target:
                loc = target["genomicLocation"]
                properties.update({
                    "chromosome": loc.get("chromosome"),
                    "start": loc.get("start"),
                    "end": loc.get("end"),
                    "strand": loc.get("strand"),
                })
            # Handle simplified structure for sample data
            elif any(key in target for key in ["chromosome", "start", "end"]):
                properties.update({
                    "chromosome": target.get("chromosome"),
                    "start": target.get("start"),
                    "end": target.get("end"),
                    "strand": target.get("strand"),
                })
            
            # Add metadata
            properties.update(self.get_metadata_dict())
            
            self.nodes_data.setdefault("target", []).append({
                "id": node_id,
                "label": "target",
                "properties": properties
            })
            
            count += 1
        
        logger.info(f"Processed {count} targets")
    
    def process_diseases(self):
        """Process diseases dataset."""
        if OpenTargetsNodeType.DISEASE not in self.node_types:
            return
        
        filepath = self.download_dataset(OpenTargetsDataset.DISEASES)
        logger.info("Processing diseases...")
        
        count = 0
        for disease in tqdm(self.stream_data(filepath), desc="Diseases"):
            if self.test_mode and count >= 100:
                break
            
            node_id = self.add_prefix_to_id("efo", disease.get("id"))
            
            properties = {
                "name": disease.get("name"),
                "description": disease.get("description"),
                "synonyms": disease.get("synonyms", []),
            }
            
            # Add metadata
            properties.update(self.get_metadata_dict())
            
            self.nodes_data.setdefault("disease", []).append({
                "id": node_id,
                "label": "disease",
                "properties": properties
            })
            
            count += 1
        
        logger.info(f"Processed {count} diseases")
    
    def process_associations(self):
        """Process target-disease associations."""
        if OpenTargetsEdgeType.TARGET_DISEASE_ASSOCIATION not in self.edge_types:
            logger.info("Skipping associations - not in edge_types")
            return
        
        filepath = self.download_dataset(OpenTargetsDataset.ASSOCIATIONS)
        logger.info(f"Processing associations from file: {filepath}")
        logger.info(f"File exists: {os.path.exists(filepath)}")
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"File size: {file_size} bytes")
        
        count = 0
        try:
            for assoc in tqdm(self.stream_data(filepath), desc="Associations"):
                if self.test_mode and count >= 100:
                    break
                
                # Handle both real data and sample data field names
                source_target_id = assoc.get("targetId") or assoc.get("targetFromSourceId") 
                target_disease_id = assoc.get("diseaseId") or assoc.get("diseaseFromSourceMappedId")
                
                source_id = self.add_prefix_to_id("ensembl", source_target_id)
                target_id = self.add_prefix_to_id("efo", target_disease_id)
                
                # Handle different score field names in real vs sample data
                score = assoc.get("score") or assoc.get("harmonic-sum") or assoc.get("overall") or 0
                
                properties = {
                    "score": float(score),
                    "datasources": list(assoc.get("datasourceScores", {}).keys()),
                }
                
                # Add individual datasource scores if available
                datasource_scores = assoc.get("datasourceScores", {})
                for datasource, ds_score in datasource_scores.items():
                    if ds_score is not None:
                        properties[f"{datasource}_score"] = float(ds_score)
                
                # Add metadata
                properties.update(self.get_metadata_dict())
                
                self.edges_data.append({
                    "source_id": source_id,
                    "target_id": target_id,
                    "label": "associated_with_disease",
                    "properties": properties
                })
                
                count += 1
                
        except Exception as e:
            logger.error(f"Error processing associations: {str(e)}")
            logger.info("Check if the file format is correct or if pandas can read it")
        
        logger.info(f"Processed {count} associations")
    
    def get_nodes(self) -> Generator[tuple[str, str, dict], None, None]:
        """
        Get nodes from Open Targets data.
        
        Yields:
            Tuples of (node_id, node_label, node_properties)
        """
        # Process each dataset if not already done
        if not self.nodes_data:
            with self.timer("Processing Open Targets nodes"):
                self.process_targets()
                self.process_diseases()
        
        # Yield all nodes
        for node_type, nodes in self.nodes_data.items():
            for node in nodes:
                yield (node["id"], node["label"], node["properties"])
    
    def get_edges(self) -> Generator[tuple[Optional[str], str, str, str, dict], None, None]:
        """
        Get edges from Open Targets data.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, edge_properties)
        """
        # Process associations if not already done
        if not self.edges_data:
            with self.timer("Processing Open Targets edges"):
                self.process_associations()
        
        # Yield all edges
        for i, edge in enumerate(self.edges_data):
            edge_id = f"opentargets_edge_{i}"
            yield (
                edge_id,
                edge["source_id"],
                edge["target_id"],
                edge["label"],
                edge["properties"]
            )
    
    def get_node_count(self) -> int:
        """Get the total number of nodes."""
        return sum(len(nodes) for nodes in self.nodes_data.values())
    
    def get_edge_count(self) -> int:
        """Get the total number of edges."""
        return len(self.edges_data)