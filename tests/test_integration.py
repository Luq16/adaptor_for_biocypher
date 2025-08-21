#!/usr/bin/env python3
"""
Integration tests for the complete BioCypher pipeline.

These tests verify that the adapters can work together to create a valid
knowledge graph.
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from biocypher import BioCypher

from template_package.adapters import (
    UniprotAdapter,
    ChemblAdapter,
    DiseaseOntologyAdapter,
    StringAdapter,
)


class TestPipelineIntegration(unittest.TestCase):
    """Test the complete knowledge graph creation pipeline."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def test_biocypher_initialization(self):
        """Test BioCypher can be initialized with our configuration."""
        # Test with default config
        bc = BioCypher()
        self.assertIsNotNone(bc)
        
        # Test summary works (even with no data)
        try:
            bc.summary()
        except Exception as e:
            self.fail(f"BioCypher summary failed: {e}")
    
    def test_adapter_data_flow(self):
        """Test that adapters can provide data to BioCypher."""
        bc = BioCypher()
        
        # Create a simple adapter with mock data
        adapter = UniprotAdapter(test_mode=True, cache_dir=self.temp_dir)
        
        # Mock some basic data
        adapter.uniprot_ids = {'P12345'}
        adapter.data = {
            'protein_name': {'P12345': 'Test Protein'},
            'length': {'P12345': 100},
            'organism_id': {'P12345': 9606},
        }
        
        # Test that nodes can be generated and consumed by BioCypher
        nodes_generator = adapter.get_nodes()
        nodes_list = list(nodes_generator)
        
        self.assertGreater(len(nodes_list), 0)
        
        # Test BioCypher can consume the nodes
        try:
            bc.write_nodes(iter(nodes_list))  # Convert back to generator
        except Exception as e:
            self.fail(f"BioCypher failed to consume nodes: {e}")
    
    def test_schema_validation(self):
        """Test that our schema configuration is valid."""
        from biocypher._config import BiocypherConfig
        
        # Test loading our schema config
        try:
            config = BiocypherConfig(
                schema_config_path="config/schema_config.yaml"
            )
            self.assertIsNotNone(config)
        except Exception as e:
            self.fail(f"Schema configuration is invalid: {e}")
    
    def test_node_id_consistency(self):
        """Test that node IDs are consistent across adapters."""
        # Test UniProt IDs
        uniprot_adapter = UniprotAdapter(
            test_mode=True,
            cache_dir=self.temp_dir,
            add_prefix=True
        )
        
        # Test ChEMBL IDs
        chembl_adapter = ChemblAdapter(
            test_mode=True,
            cache_dir=self.temp_dir,
            add_prefix=True
        )
        
        # Test that they produce valid, consistent IDs
        uniprot_id = uniprot_adapter.add_prefix_to_id("uniprot", "P12345")
        chembl_id = chembl_adapter.add_prefix_to_id("chembl", "CHEMBL1")
        
        self.assertTrue(uniprot_id.startswith("uniprot:"))
        self.assertTrue(chembl_id.startswith("chembl:"))
        self.assertNotEqual(uniprot_id, chembl_id)
    
    @patch('biocypher.BioCypher.write_import_call')
    @patch('biocypher.BioCypher.summary')
    def test_complete_pipeline_mock(self, mock_summary, mock_import_call):
        """Test the complete pipeline with mocked external dependencies."""
        from create_biological_knowledge_graph import main
        
        # Mock environment for test mode
        with patch.dict(os.environ, {'BIOCYPHER_TEST_MODE': 'true'}):
            with patch.object(UniprotAdapter, 'download_data'), \
                 patch.object(ChemblAdapter, 'download_data'), \
                 patch.object(DiseaseOntologyAdapter, 'download_data'), \
                 patch.object(StringAdapter, 'download_data'), \
                 patch.object(UniprotAdapter, 'get_nodes', return_value=iter([])), \
                 patch.object(UniprotAdapter, 'get_edges', return_value=iter([])), \
                 patch.object(ChemblAdapter, 'get_nodes', return_value=iter([])), \
                 patch.object(ChemblAdapter, 'get_edges', return_value=iter([])), \
                 patch.object(DiseaseOntologyAdapter, 'get_nodes', return_value=iter([])), \
                 patch.object(DiseaseOntologyAdapter, 'get_edges', return_value=iter([])), \
                 patch.object(StringAdapter, 'get_edges', return_value=iter([])):
                
                try:
                    main()
                    
                    # Verify that the pipeline completed
                    mock_import_call.assert_called_once()
                    mock_summary.assert_called_once()
                    
                except Exception as e:
                    self.fail(f"Complete pipeline failed: {e}")


class TestDataValidation(unittest.TestCase):
    """Test data validation and quality checks."""
    
    def test_node_structure_validation(self):
        """Test that nodes have the correct structure."""
        adapter = UniprotAdapter(test_mode=True)
        adapter.uniprot_ids = {'P12345'}
        adapter.data = {
            'protein_name': {'P12345': 'Test Protein'},
            'length': {'P12345': 100},
        }
        
        nodes = list(adapter.get_nodes())
        
        for node in nodes:
            # Check tuple structure
            self.assertEqual(len(node), 3)
            node_id, node_label, properties = node
            
            # Check types
            self.assertIsInstance(node_id, str)
            self.assertIsInstance(node_label, str)
            self.assertIsInstance(properties, dict)
            
            # Check required properties
            self.assertIn('source', properties)
            self.assertIn('version', properties)
            self.assertIn('licence', properties)
    
    def test_edge_structure_validation(self):
        """Test that edges have the correct structure."""
        import pandas as pd
        
        adapter = StringAdapter(test_mode=True)
        adapter.interactions = pd.DataFrame({
            'protein1': ['9606.ENSP00000000233'],
            'protein2': ['9606.ENSP00000000412'],
            'combined_score': [800],
            'physical': [600],
            'functional': [500],
            'experimental': [200],
            'database': [300],
        })
        
        edges = list(adapter.get_edges())
        
        for edge in edges:
            # Check tuple structure
            self.assertEqual(len(edge), 5)
            edge_id, source_id, target_id, edge_label, properties = edge
            
            # Check types
            self.assertTrue(edge_id is None or isinstance(edge_id, str))
            self.assertIsInstance(source_id, str)
            self.assertIsInstance(target_id, str)
            self.assertIsInstance(edge_label, str)
            self.assertIsInstance(properties, dict)
            
            # Check required properties
            self.assertIn('source', properties)
    
    def test_id_format_validation(self):
        """Test that generated IDs follow expected formats."""
        adapter = UniprotAdapter(test_mode=True, add_prefix=True)
        
        # Test various ID types
        test_cases = [
            ("uniprot", "P12345", "uniprot:P12345"),
            ("ncbigene", "123456", "ncbigene:123456"),
            ("ensembl", "ENSG00000000003", "ensembl:ENSG00000000003"),
        ]
        
        for prefix, identifier, expected in test_cases:
            result = adapter.add_prefix_to_id(prefix, identifier)
            self.assertTrue(result.startswith(f"{prefix}:"))
            self.assertIn(identifier, result)


if __name__ == '__main__':
    unittest.main(verbosity=2)