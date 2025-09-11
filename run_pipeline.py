#!/usr/bin/env python3
"""Entry point for running the BioCypher knowledge graph pipeline."""

import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(
        description='Run BioCypher Knowledge Graph Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all adapters (default)
  python run_pipeline.py
  
  # Run specific adapters
  python run_pipeline.py --adapters chembl
  python run_pipeline.py --adapters uniprot string
  python run_pipeline.py --adapters chembl opentargets uniprot
  
  # Run in test mode
  python run_pipeline.py --test-mode
  python run_pipeline.py --adapters chembl --test-mode
  
  # List available adapters
  python run_pipeline.py --list
        """
    )
    
    parser.add_argument(
        '--adapters', 
        nargs='+',
        help='Adapters to run (e.g., uniprot chembl string). Use "all" for all adapters.',
        default=['all']
    )
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with limited data')
    parser.add_argument('--real-data', action='store_true', help='Use real OpenTargets data')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--list', action='store_true', help='List available adapters')
    
    args = parser.parse_args()
    
    # Set environment variables
    env = os.environ.copy()
    if args.test_mode:
        env['BIOCYPHER_TEST_MODE'] = 'true'
    if args.real_data:
        env['OPENTARGETS_USE_REAL_DATA'] = 'true'
    if args.debug:
        env['BIOCYPHER_DEBUG'] = 'true'
    
    # Build command
    cmd = ['poetry', 'run', 'python', 'pipeline/workflows/flexible_pipeline.py']
    
    # Add arguments
    if args.list:
        cmd.append('--list')
    else:
        cmd.extend(['--adapters'] + args.adapters)
        if args.test_mode:
            cmd.append('--test-mode')
    
    # Run the pipeline
    subprocess.run(cmd, env=env)

if __name__ == '__main__':
    main()