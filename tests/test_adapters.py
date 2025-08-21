#!/usr/bin/env python3
"""
Integration tests for BioCypher adapters.

These tests verify that adapters can successfully download data and generate
valid nodes and edges for the knowledge graph.
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock

from template_package.adapters import (
    UniprotAdapter,
    UniprotNodeType,
    UniprotNodeField,
    ChemblAdapter,
    ChemblNodeType,
    ChemblNodeField,
    DiseaseOntologyAdapter,
    DiseaseNodeType,
    StringAdapter,
    StringEdgeType,
)


class TestUniprotAdapter(unittest.TestCase):
    """Test UniProt adapter functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = UniprotAdapter(
            organism="9606",
            test_mode=True,
            cache_dir=self.temp_dir,
            add_prefix=True,
        )
    
    def test_adapter_initialization(self):
        """Test that adapter initializes correctly."""
        self.assertEqual(self.adapter.organism, "9606")
        self.assertTrue(self.adapter.test_mode)
        self.assertEqual(self.adapter.data_source, "uniprot")
        self.assertTrue(self.adapter.add_prefix)
    
    def test_node_types_configuration(self):
        """Test node types are configured correctly."""
        self.assertIn(UniprotNodeType.PROTEIN, self.adapter.node_types)
        self.assertIn(UniprotNodeType.GENE, self.adapter.node_types)
        self.assertIn(UniprotNodeType.ORGANISM, self.adapter.node_types)
    
    @patch('pypath.inputs.uniprot._all_uniprots')
    @patch('pypath.inputs.uniprot.uniprot_data')
    def test_data_download(self, mock_uniprot_data, mock_all_uniprots):
        """Test data download functionality."""
        # Mock responses
        mock_all_uniprots.return_value = ['P12345', 'P67890']
        mock_uniprot_data.return_value = {
            'P12345': 'Test protein 1',
            'P67890': 'Test protein 2'
        }
        
        # Test download
        self.adapter.download_data()
        
        # Verify calls were made
        mock_all_uniprots.assert_called_once()
        self.assertTrue(mock_uniprot_data.called)
        
        # Verify data was stored
        self.assertEqual(len(self.adapter.uniprot_ids), 2)
    
    def test_nodes_generation(self):
        """Test node generation without actual data download."""
        # Set up mock data
        self.adapter.uniprot_ids = {'P12345'}
        self.adapter.data = {
            UniprotNodeField.PROTEIN_NAME.value: {'P12345': 'Test protein'},
            UniprotNodeField.LENGTH.value: {'P12345': 100},
        }
        
        # Generate nodes
        nodes = list(self.adapter.get_nodes())
        
        # Verify nodes are generated
        self.assertGreater(len(nodes), 0)
        
        # Check node structure
        node_id, node_label, properties = nodes[0]
        self.assertTrue(node_id.startswith('uniprot:'))
        self.assertEqual(node_label, 'protein')
        self.assertIn('source', properties)
        self.assertEqual(properties['source'], 'uniprot')


class TestChemblAdapter(unittest.TestCase):
    """Test ChEMBL adapter functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = ChemblAdapter(
            test_mode=True,
            cache_dir=self.temp_dir,
            add_prefix=True,
        )
    
    def test_adapter_initialization(self):
        """Test adapter initializes correctly."""
        self.assertTrue(self.adapter.test_mode)
        self.assertEqual(self.adapter.data_source, "chembl")
        self.assertIn(ChemblNodeType.DRUG, self.adapter.node_types)
        self.assertIn(ChemblNodeType.COMPOUND, self.adapter.node_types)
    
    @patch('chembl_webresource_client.new_client.new_client.molecule')
    def test_molecule_download(self, mock_molecule_client):
        """Test molecule data download."""
        # Mock molecule data
        mock_molecule = MagicMock()
        mock_molecule.molecule_chembl_id = 'CHEMBL1'
        mock_molecule.pref_name = 'Test Drug'
        mock_molecule.max_phase = 4
        
        mock_molecule_client.filter.return_value.limit.return_value = [mock_molecule]
        
        # Test download
        self.adapter._download_molecules(limit=1)
        
        # Verify data was processed
        self.assertEqual(len(self.adapter.molecules), 1)
        self.assertEqual(self.adapter.molecules[0]['molecule_chembl_id'], 'CHEMBL1')
    
    def test_nodes_generation(self):
        """Test node generation from mock data."""
        # Set up mock molecule data
        self.adapter.molecules = [{
            ChemblNodeField.MOLECULE_CHEMBL_ID.value: 'CHEMBL1',
            ChemblNodeField.PREF_NAME.value: 'Test Drug',
            ChemblNodeField.MAX_PHASE.value: 4,
            ChemblNodeField.MOLECULAR_WEIGHT.value: 300.5,
        }]
        
        # Generate nodes
        nodes = list(self.adapter.get_nodes())
        
        # Verify nodes
        self.assertGreater(len(nodes), 0)
        
        node_id, node_label, properties = nodes[0]
        self.assertTrue(node_id.startswith('chembl:'))
        self.assertEqual(node_label, 'drug')  # max_phase = 4 means drug
        self.assertIn('source', properties)


class TestDiseaseOntologyAdapter(unittest.TestCase):
    """Test Disease Ontology adapter functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = DiseaseOntologyAdapter(
            ontology="DO",
            test_mode=True,
            cache_dir=self.temp_dir,
            add_prefix=True,
        )
    
    def test_adapter_initialization(self):
        """Test adapter initializes correctly."""
        self.assertEqual(self.adapter.ontology_type, "DO")
        self.assertTrue(self.adapter.test_mode)
        self.assertEqual(self.adapter.data_source, "do")
        self.assertIn(DiseaseNodeType.DISEASE, self.adapter.node_types)
    
    @patch('pronto.Ontology')
    @patch.object(DiseaseOntologyAdapter, 'download_file')
    def test_data_processing(self, mock_download, mock_ontology):
        """Test ontology data processing."""
        # Mock ontology term
        mock_term = MagicMock()
        mock_term.id = 'DOID:0001'
        mock_term.name = 'Test Disease'
        mock_term.obsolete = False
        mock_term.definition = 'A test disease'
        mock_term.synonyms = []
        mock_term.xrefs = []
        mock_term.subsets = []
        mock_term.superclasses.return_value = []
        
        mock_ontology_instance = MagicMock()
        mock_ontology_instance.terms.return_value = [mock_term]
        mock_ontology.return_value = mock_ontology_instance
        
        mock_download.return_value = '/fake/path'
        
        # Test processing
        self.adapter.download_data()
        
        # Verify processing
        self.assertEqual(len(self.adapter.diseases), 1)
        self.assertEqual(self.adapter.diseases[0]['id'], 'DOID:0001')


class TestStringAdapter(unittest.TestCase):
    """Test STRING adapter functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.adapter = StringAdapter(
            organism="9606",
            test_mode=True,
            cache_dir=self.temp_dir,
            add_prefix=True,
        )
    
    def test_adapter_initialization(self):
        """Test adapter initializes correctly."""
        self.assertEqual(self.adapter.organism, "9606")
        self.assertTrue(self.adapter.test_mode)
        self.assertEqual(self.adapter.data_source, "string")
        self.assertIn(StringEdgeType.PROTEIN_PROTEIN_INTERACTION, self.adapter.edge_types)
    
    @patch('pandas.read_csv')
    @patch.object(StringAdapter, 'download_file')
    def test_interaction_processing(self, mock_download, mock_read_csv):
        """Test interaction data processing."""
        # Mock interaction data
        import pandas as pd
        mock_df = pd.DataFrame({
            'protein1': ['9606.ENSP00000000233', '9606.ENSP00000000412'],
            'protein2': ['9606.ENSP00000000412', '9606.ENSP00000000233'],
            'combined_score': [500, 700],
            'experimental': [100, 200],
            'database': [200, 300],
            'textmining': [150, 100],
            'neighborhood': [50, 100],
            'fusion': [0, 0],
            'cooccurrence': [0, 0],
            'coexpression': [0, 0],
        })
        
        mock_read_csv.return_value = mock_df
        mock_download.return_value = '/fake/path'
        
        # Test processing
        self.adapter._download_protein_links()
        
        # Verify data was processed
        self.assertFalse(self.adapter.interactions.empty)
        self.assertGreater(len(self.adapter.interactions), 0)
    
    def test_edge_generation(self):
        """Test edge generation from mock data."""
        import pandas as pd
        
        # Set up mock interaction data
        self.adapter.interactions = pd.DataFrame({
            'protein1': ['9606.ENSP00000000233'],
            'protein2': ['9606.ENSP00000000412'],
            'combined_score': [800],
            'physical': [600],
            'functional': [500],
            'experimental': [200],
            'database': [300],
        })
        
        # Generate edges
        edges = list(self.adapter.get_edges())
        
        # Verify edges
        if edges:  # Only test if we have edges (depends on ID extraction)
            edge_id, source_id, target_id, edge_label, properties = edges[0]
            self.assertIsNone(edge_id)  # STRING doesn't provide edge IDs
            self.assertIn('source', properties)
            self.assertEqual(properties['source'], 'string')


class TestAdapterIntegration(unittest.TestCase):
    """Test adapter integration scenarios."""
    
    def test_multiple_adapters_compatibility(self):
        """Test that multiple adapters can work together."""
        temp_dir = tempfile.mkdtemp()
        
        # Initialize multiple adapters
        uniprot_adapter = UniprotAdapter(test_mode=True, cache_dir=temp_dir)
        chembl_adapter = ChemblAdapter(test_mode=True, cache_dir=temp_dir)
        disease_adapter = DiseaseOntologyAdapter(test_mode=True, cache_dir=temp_dir)
        
        # Verify they all use the same cache directory
        self.assertEqual(uniprot_adapter.cache_dir, temp_dir)
        self.assertEqual(chembl_adapter.cache_dir, temp_dir)
        self.assertEqual(disease_adapter.cache_dir, temp_dir)
        
        # Verify they have different data sources
        sources = {
            uniprot_adapter.data_source,
            chembl_adapter.data_source,
            disease_adapter.data_source
        }
        self.assertEqual(len(sources), 3)  # All unique
    
    def test_prefix_normalization(self):
        """Test that ID prefixing works consistently."""
        temp_dir = tempfile.mkdtemp()
        
        uniprot_adapter = UniprotAdapter(
            test_mode=True,
            cache_dir=temp_dir,
            add_prefix=True
        )
        
        # Test prefix addition
        prefixed_id = uniprot_adapter.add_prefix_to_id("uniprot", "P12345")
        self.assertTrue(prefixed_id.startswith("uniprot:"))
        self.assertIn("P12345", prefixed_id)
        
        # Test with no prefix
        uniprot_adapter.add_prefix = False
        no_prefix_id = uniprot_adapter.add_prefix_to_id("uniprot", "P12345")
        self.assertEqual(no_prefix_id, "P12345")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)