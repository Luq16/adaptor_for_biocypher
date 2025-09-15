#!/usr/bin/env python3
"""
Flexible BioCypher pipeline that supports running single adapters,
multiple adapters, or all available adapters.
"""

import os
import sys
import logging
import argparse
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biocypher import BioCypher
from adapters import (
    # UniProt adapter
    UniprotAdapter,
    UniprotNodeType,
    UniprotNodeField,
    UniprotEdgeType,
    # ChEMBL adapter
    ChemblAdapter,
    ChemblNodeType,
    ChemblNodeField,
    ChemblEdgeType,
    # Disease Ontology adapter
    DiseaseOntologyAdapter,
    DiseaseNodeType,
    DiseaseNodeField,
    DiseaseEdgeType,
    # STRING adapter
    StringAdapter,
    StringNodeType,
    StringEdgeType,
    StringEdgeField,
    # Gene Ontology adapter
    GOAdapter,
    GONodeType,
    GONodeField,
    GOEdgeType,
    # Reactome adapter
    ReactomeAdapter,
    ReactomeNodeType,
    ReactomeNodeField,
    ReactomeEdgeType,
    # DisGeNET adapter
    DisGeNETAdapter,
    DisGeNETEdgeType,
    DisGeNETEdgeField,
    # OpenTargets adapter
    OpenTargetsAdapter,
    OpenTargetsNodeType,
    OpenTargetsEdgeType,
    OpenTargetsEdgeField,
    # SideEffect adapter
    SideEffectAdapter,
    SideEffectNodeType,
    SideEffectNodeField,
    SideEffectEdgeType,
    SideEffectEdgeField,
    # Phenotype adapter
    PhenotypeAdapter,
    PhenotypeNodeType,
    PhenotypeNodeField,
    PhenotypeEdgeType,
    PhenotypeEdgeField,
    # Orthology adapter
    OrthologyAdapter,
    OrthologyNodeType,
    OrthologyNodeField,
    OrthologyEdgeType,
    OrthologyEdgeField,
    # PPI adapter
    PPIAdapter,
    PPINodeType,
    PPINodeField,
    PPIEdgeType,
    PPIEdgeField,
    # Check which adapters are available
    _adapters_available,
)

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdapterConfig:
    """Configuration for each adapter"""
    
    def __init__(self, name: str, adapter_class: Any, config: Dict[str, Any]):
        self.name = name
        self.adapter_class = adapter_class
        self.config = config
        self.enabled = False
        
    def create_instance(self):
        """Create an instance of the adapter with its configuration"""
        return self.adapter_class(**self.config)


def get_adapter_configs(test_mode: bool = False) -> Dict[str, AdapterConfig]:
    """Get all available adapter configurations"""
    
    configs = {}
    
    # UniProt configuration
    if _adapters_available.get('uniprot', False):
        configs['uniprot'] = AdapterConfig(
            name='UniProt',
            adapter_class=UniprotAdapter,
            config={
                'organism': '9606',  # Human
                'node_types': [
                    UniprotNodeType.PROTEIN,
                    UniprotNodeType.GENE,
                ],
                'node_fields': [
                    UniprotNodeField.PROTEIN_NAME,
                    UniprotNodeField.GENE_NAMES,
                    UniprotNodeField.ORGANISM_NAME,
                    UniprotNodeField.LENGTH,
                    UniprotNodeField.FUNCTION,
                ],
                'test_mode': test_mode,
            }
        )
    
    # ChEMBL configuration
    if _adapters_available.get('chembl', False):
        configs['chembl'] = AdapterConfig(
            name='ChEMBL',
            adapter_class=ChemblAdapter,
            config={
                'node_types': [
                    ChemblNodeType.DRUG,
                    ChemblNodeType.COMPOUND,
                    ChemblNodeType.TARGET,
                ],
                'node_fields': [
                    ChemblNodeField.MOLECULE_CHEMBL_ID,
                    ChemblNodeField.PREF_NAME,
                    ChemblNodeField.MOLECULE_TYPE,
                    ChemblNodeField.MAX_PHASE,
                    ChemblNodeField.TARGET_CHEMBL_ID,
                    ChemblNodeField.TARGET_TYPE,
                ],
                'edge_types': [
                    ChemblEdgeType.COMPOUND_TARGETS_PROTEIN,
                    ChemblEdgeType.DRUG_TREATS_DISEASE,
                ],
                'test_mode': test_mode,
            }
        )
    
    # Disease Ontology configuration
    if _adapters_available.get('disease', False):
        configs['disease'] = AdapterConfig(
            name='Disease Ontology',
            adapter_class=DiseaseOntologyAdapter,
            config={
                'node_types': [DiseaseNodeType.DISEASE],
                'node_fields': [
                    DiseaseNodeField.NAME,
                    DiseaseNodeField.DEFINITION,
                    DiseaseNodeField.SYNONYMS,
                    DiseaseNodeField.XREFS,
                ],
                'edge_types': [DiseaseEdgeType.DISEASE_IS_A_DISEASE],
                'test_mode': test_mode,
            }
        )
    
    # STRING configuration
    if _adapters_available.get('string', False):
        configs['string'] = AdapterConfig(
            name='STRING',
            adapter_class=StringAdapter,
            config={
                'organism': '9606',  # Human
                'node_types': [],  # Usually empty - proteins come from UniProt
                'edge_types': [
                    StringEdgeType.PROTEIN_PROTEIN_INTERACTION,
                ],
                'edge_fields': [
                    StringEdgeField.COMBINED_SCORE,
                    StringEdgeField.EXPERIMENTAL_SCORE,
                    StringEdgeField.DATABASE_SCORE,
                ],
                'score_threshold': "high_confidence",  # CROssBARv2 approach: biologically meaningful threshold
                'test_mode': test_mode,
            }
        )
    
    # Gene Ontology configuration
    if _adapters_available.get('go', False):
        configs['go'] = AdapterConfig(
            name='Gene Ontology',
            adapter_class=GOAdapter,
            config={
                'organism': '9606',
                'node_types': [
                    GONodeType.GO_TERM,
                ],
                'node_fields': [
                    GONodeField.NAME,
                    GONodeField.NAMESPACE,
                    GONodeField.DEFINITION,
                ],
                'edge_types': [
                    GOEdgeType.GO_TERM_IS_A_GO_TERM,
                    GOEdgeType.GO_TERM_PART_OF_GO_TERM,
                    GOEdgeType.GO_TERM_REGULATES_GO_TERM,
                    GOEdgeType.PROTEIN_TO_GO_TERM,
                ],
                'test_mode': test_mode,
            }
        )
    
    # Reactome configuration
    if _adapters_available.get('reactome', False):
        configs['reactome'] = AdapterConfig(
            name='Reactome',
            adapter_class=ReactomeAdapter,
            config={
                'organism': '9606',
                'node_types': [ReactomeNodeType.PATHWAY],
                'node_fields': [
                    ReactomeNodeField.NAME,
                    ReactomeNodeField.SPECIES,
                ],
                'edge_types': [ReactomeEdgeType.PATHWAY_CHILD_OF_PATHWAY, ReactomeEdgeType.PROTEIN_IN_PATHWAY],
                'test_mode': test_mode,
            }
        )
    
    # DisGeNET configuration
    if _adapters_available.get('disgenet', False):
        configs['disgenet'] = AdapterConfig(
            name='DisGeNET',
            adapter_class=DisGeNETAdapter,
            config={
                'node_types': [],  # Usually empty - genes and diseases come from other adapters
                'edge_types': [DisGeNETEdgeType.GENE_DISEASE_ASSOCIATION],
                'edge_fields': [
                    DisGeNETEdgeField.GENE_DISEASE_SCORE,
                    DisGeNETEdgeField.EVIDENCE_INDEX,
                    DisGeNETEdgeField.SOURCE,
                ],
                'score_threshold': 0.3,
                'test_mode': test_mode,
            }
        )
    
    # OpenTargets configuration - CROssBARv2 approach
    if _adapters_available.get('opentargets', False):
        configs['opentargets'] = AdapterConfig(
            name='OpenTargets',
            adapter_class=OpenTargetsAdapter,
            config={
                'node_types': [],  # CROssBARv2: no nodes, only edges
                'edge_types': [OpenTargetsEdgeType.TARGET_DISEASE_ASSOCIATION],
                'edge_fields': [
                    OpenTargetsEdgeField.OPENTARGETS_SCORE,
                    OpenTargetsEdgeField.SOURCE,
                    OpenTargetsEdgeField.EVIDENCE_COUNT,
                ],
                'score_threshold': 0.0,  # CROssBARv2 approach: filter != 0.0
                'test_mode': test_mode,
            }
        )
    
    # SideEffect configuration - CROssBARv2 approach
    if _adapters_available.get('side_effect', False):
        configs['side_effect'] = AdapterConfig(
            name='SideEffect',
            adapter_class=SideEffectAdapter,
            config={
                'node_types': [SideEffectNodeType.SIDE_EFFECT],  # Authoritative source for side effects
                'node_fields': [
                    SideEffectNodeField.NAME,
                    SideEffectNodeField.MEDDRA_ID,
                    SideEffectNodeField.CATEGORY,
                    SideEffectNodeField.SYNONYMS,
                ],
                'edge_types': [SideEffectEdgeType.DRUG_HAS_SIDE_EFFECT],
                'edge_fields': [
                    SideEffectEdgeField.FREQUENCY,
                    SideEffectEdgeField.PROPORTIONAL_REPORTING_RATIO,
                    SideEffectEdgeField.SOURCE,
                ],
                'frequency_threshold': 0.0,  # Minimum frequency threshold
                'test_mode': test_mode,
            }
        )
    
    # Phenotype configuration - CROssBARv2 approach
    if _adapters_available.get('phenotype', False):
        configs['phenotype'] = AdapterConfig(
            name='Phenotype',
            adapter_class=PhenotypeAdapter,
            config={
                'node_types': [PhenotypeNodeType.PHENOTYPE],  # Authoritative source for phenotypes
                'node_fields': [
                    PhenotypeNodeField.NAME,
                    PhenotypeNodeField.SYNONYMS,
                    PhenotypeNodeField.DEFINITION,
                ],
                'edge_types': [
                    PhenotypeEdgeType.PROTEIN_TO_PHENOTYPE,
                    PhenotypeEdgeType.PHENOTYPE_IS_A_PHENOTYPE,
                    PhenotypeEdgeType.PHENOTYPE_TO_DISEASE,
                ],
                'edge_fields': [
                    PhenotypeEdgeField.EVIDENCE_CODE,
                    PhenotypeEdgeField.RELATIONSHIP_TYPE,
                    PhenotypeEdgeField.PUBMED_IDS,
                ],
                'test_mode': test_mode,
            }
        )
    
    # Orthology configuration - CROssBARv2 approach
    if _adapters_available.get('orthology', False):
        configs['orthology'] = AdapterConfig(
            name='Orthology',
            adapter_class=OrthologyAdapter,
            config={
                'node_types': [],  # CROssBARv2: no nodes, only edges between existing genes
                'edge_types': [OrthologyEdgeType.GENE_ORTHOLOGOUS_WITH_GENE],
                'edge_fields': [
                    OrthologyEdgeField.SOURCE,
                    OrthologyEdgeField.RELATION_TYPE,
                    OrthologyEdgeField.OMA_ORTHOLOGY_SCORE,
                    OrthologyEdgeField.SOURCE_ORGANISM,
                    OrthologyEdgeField.TARGET_ORGANISM,
                ],
                'target_organisms': [10090, 10116, 7955, 7227],  # Mouse, rat, zebrafish, fruitfly
                'test_mode': test_mode,
            }
        )
    
    # PPI configuration - CROssBARv2 approach
    if _adapters_available.get('ppi', False):
        configs['ppi'] = AdapterConfig(
            name='PPI',
            adapter_class=PPIAdapter,
            config={
                'node_types': [],  # CROssBARv2: no nodes, only edges between existing proteins
                'edge_types': [PPIEdgeType.PROTEIN_PROTEIN_INTERACTION],
                'edge_fields': [
                    PPIEdgeField.SOURCE,
                    PPIEdgeField.PUBMED_IDS,
                    PPIEdgeField.INTACT_SCORE,
                    PPIEdgeField.METHODS,
                    PPIEdgeField.INTERACTION_TYPES,
                    PPIEdgeField.EXPERIMENTAL_SYSTEM,
                ],
                'organism': 9606,  # Human
                'test_mode': test_mode,
            }
        )
    
    return configs


def run_adapters(adapter_names: List[str], test_mode: bool = False):
    """Run specified adapters"""
    
    # Initialize BioCypher
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
    bc = BioCypher(
        biocypher_config_path=os.path.join(config_dir, "biocypher_config.yaml"),
        schema_config_path=os.path.join(config_dir, "schema_config.yaml"),
    )
    
    # Get adapter configurations
    all_configs = get_adapter_configs(test_mode)
    
    # Validate adapter names
    if 'all' in adapter_names:
        adapter_names = list(all_configs.keys())
        logger.info(f"Running all available adapters: {adapter_names}")
    else:
        # Check if requested adapters are available
        for name in adapter_names:
            if name not in all_configs:
                logger.error(f"Adapter '{name}' not found or not available.")
                logger.info(f"Available adapters: {list(all_configs.keys())}")
                return
    
    # Run each adapter
    for adapter_name in adapter_names:
        config = all_configs[adapter_name]
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {config.name} adapter...")
        logger.info(f"{'='*50}")
        
        try:
            # Create adapter instance
            adapter = config.create_instance()
            
            # Download data
            logger.info(f"Downloading {config.name} data...")
            adapter.download_data()
            
            # Process nodes if adapter provides them
            if hasattr(adapter, 'get_nodes'):
                logger.info(f"Processing {config.name} nodes...")
                try:
                    bc.write_nodes(adapter.get_nodes())
                except StopIteration:
                    # This is expected for edge-only adapters (STRING, OpenTargets)
                    logger.debug(f"{config.name} adapter has no nodes (edge-only adapter)")
            
            # Process edges if adapter provides them
            if hasattr(adapter, 'get_edges'):
                logger.info(f"Processing {config.name} edges...")
                bc.write_edges(adapter.get_edges())
            
            logger.info(f"✓ {config.name} adapter completed successfully")
            
        except Exception as e:
            logger.error(f"✗ {config.name} adapter failed: {e}")
            logger.debug("Error details:", exc_info=True)
    
    # Finalize - only if data was written
    try:
        # Check if any data was actually written
        if hasattr(bc, '_writer') and bc._writer is not None:
            bc.write_import_call()
            bc.summary()
        else:
            logger.warning("No data was written by any adapters - skipping import call generation")
            logger.info("This usually happens when:")
            logger.info("  1. Adapters only generate edges but no nodes were created")
            logger.info("  2. All requested node_types are empty lists")
            logger.info("  3. Adapters failed to generate any output")
            logger.info("Consider running adapters that generate nodes (uniprot, chembl, disease, etc.)")
    except AttributeError as e:
        logger.warning(f"Could not write import call: {e}")
        logger.info("This is usually because no CSV files were generated")
    except Exception as e:
        logger.error(f"Error during finalization: {e}")
        logger.debug("Finalization error details:", exc_info=True)


def main():
    """Main entry point for flexible pipeline"""
    
    parser = argparse.ArgumentParser(
        description='Flexible BioCypher Knowledge Graph Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single adapter
  python flexible_pipeline.py --adapters chembl
  
  # Run multiple adapters
  python flexible_pipeline.py --adapters uniprot chembl opentargets
  
  # Run all available adapters
  python flexible_pipeline.py --adapters all
  
  # Run in test mode (limited data)
  python flexible_pipeline.py --adapters chembl --test-mode
  
  # List available adapters
  python flexible_pipeline.py --list
        """
    )
    
    parser.add_argument(
        '--adapters', 
        nargs='+',
        help='Adapters to run (e.g., uniprot chembl string)',
        default=['all']
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode with limited data'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available adapters'
    )
    
    args = parser.parse_args()
    
    # Set test mode environment variable
    if args.test_mode:
        os.environ['BIOCYPHER_TEST_MODE'] = 'true'
    
    # List available adapters
    if args.list:
        configs = get_adapter_configs()
        print("\nAvailable adapters:")
        for name, config in configs.items():
            status = "✓" if _adapters_available.get(name, False) else "✗"
            print(f"  {status} {name:15} - {config.name}")
        return
    
    # Run adapters
    logger.info("Starting BioCypher Flexible Pipeline")
    logger.info(f"Test mode: {args.test_mode}")
    logger.info(f"Adapters: {args.adapters}")
    
    run_adapters(args.adapters, test_mode=args.test_mode)


if __name__ == "__main__":
    main()