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
    """
    Base metaclass for all adapter enums, providing membership checking.
    """
    def __contains__(cls, item):
        return item in cls.__members__.keys()


class BaseAdapter(ABC):
    """
    Abstract base class for all BioCypher adapters.
    
    Provides common functionality for:
    - ID prefixing and normalization
    - Data source metadata
    - Caching utilities
    - Common validation methods
    """
    
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
        """
        Abstract method to get nodes from the data source.
        Must be implemented by subclasses.
        
        Yields:
            Tuples of (node_id, node_label, node_properties)
        """
        pass
    
    @abstractmethod
    def get_edges(self) -> Generator[tuple[Optional[str], str, str, str, dict], None, None]:
        """
        Abstract method to get edges from the data source.
        Must be implemented by subclasses.
        
        Yields:
            Tuples of (edge_id, source_id, target_id, edge_label, edge_properties)
        """
        pass
    
    @lru_cache(maxsize=10000)
    def add_prefix_to_id(
        self, 
        prefix: str, 
        identifier: str, 
        sep: str = ":"
    ) -> str:
        """
        Add prefix to database identifier using bioregistry normalization.
        
        Args:
            prefix: Database prefix (e.g., "uniprot", "ncbigene")
            identifier: The identifier to prefix
            sep: Separator between prefix and identifier
            
        Returns:
            Normalized CURIE string
        """
        if not identifier:
            return None
            
        if self.add_prefix:
            return normalize_curie(f"{prefix}{sep}{identifier}")
        return identifier
    
    def get_metadata_dict(self) -> dict:
        """
        Get standard metadata dictionary for nodes/edges.
        
        Returns:
            Dictionary with source, version, and licence information
        """
        return {
            "source": self.data_source,
            "version": self.data_version,
            "licence": self.data_licence,
        }
    
    @contextmanager
    def timer(self, description: str):
        """
        Context manager for timing operations.
        
        Args:
            description: Description of the operation being timed
        """
        start_time = time.time()
        logger.info(f"Starting: {description}")
        yield
        elapsed_time = time.time() - start_time
        logger.info(f"Completed: {description} in {elapsed_time:.2f} seconds")
    
    def _ensure_iterable(self, value: Any) -> list:
        """
        Ensure a value is iterable (convert string to single-item list).
        
        Args:
            value: Value to ensure is iterable
            
        Returns:
            List containing the value(s)
        """
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]
    
    def _clean_string(self, value: str) -> str:
        """
        Clean string values for safe import into graph database.
        
        Args:
            value: String to clean
            
        Returns:
            Cleaned string
        """
        if not value:
            return value
        
        # Replace problematic characters
        return (
            str(value)
            .replace("|", ",")
            .replace("'", "^")
            .replace('"', "^")
            .strip()
        )
    
    def validate_identifier(self, identifier: str, id_type: str) -> bool:
        """
        Validate an identifier format.
        
        Args:
            identifier: The identifier to validate
            id_type: Type of identifier (e.g., "uniprot", "ncbigene")
            
        Returns:
            True if valid, False otherwise
        """
        if not identifier:
            return False
            
        # Add specific validation patterns here as needed
        validation_patterns = {
            "uniprot": lambda x: len(x) == 6 and x.isalnum(),
            "ncbigene": lambda x: x.isdigit(),
            "ensembl": lambda x: x.startswith("ENSG") and len(x) == 15,
            "chembl": lambda x: x.startswith("CHEMBL") and x[6:].isdigit(),
        }
        
        if id_type in validation_patterns:
            return validation_patterns[id_type](identifier)
        
        # Default: just check it's not empty
        return bool(identifier)
    
    def get_test_subset(self, data: list, limit: int = 100) -> list:
        """
        Get a test subset of data when in test mode.
        
        Args:
            data: Full dataset
            limit: Maximum number of items to return in test mode
            
        Returns:
            Subset of data if in test mode, otherwise full data
        """
        if self.test_mode and len(data) > limit:
            logger.info(f"Test mode: limiting data from {len(data)} to {limit} items")
            return data[:limit]
        return data


class DataDownloadMixin:
    """
    Mixin class providing data download functionality.
    """
    
    def download_file(
        self, 
        url: str, 
        filename: str, 
        force_download: bool = False
    ) -> str:
        """
        Download a file from URL with caching.
        
        Args:
            url: URL to download from
            filename: Local filename to save as
            force_download: Force re-download even if cached
            
        Returns:
            Path to downloaded file
        """
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
    
    def read_csv_cached(
        self, 
        url: str, 
        filename: str, 
        **pandas_kwargs
    ):
        """
        Download and read a CSV file with caching.
        
        Args:
            url: URL to download from
            filename: Local filename for caching
            **pandas_kwargs: Arguments to pass to pandas.read_csv
            
        Returns:
            pandas DataFrame
        """
        import pandas as pd
        
        filepath = self.download_file(url, filename)
        return pd.read_csv(filepath, **pandas_kwargs)