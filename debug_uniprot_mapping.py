#!/usr/bin/env python3
"""
Debug UniProt to STRING mapping.
"""

try:
    from pypath.inputs import uniprot
    print("✅ Successfully imported pypath.inputs.uniprot")
    
    print("\n1. Testing UniProt xref_string download...")
    try:
        uniprot_to_string = uniprot.uniprot_data("xref_string", "*", True)
        print(f"✅ Downloaded {len(uniprot_to_string)} UniProt entries with STRING cross-references")
        
        # Show sample mappings
        print("\nSample mappings:")
        sample_items = list(uniprot_to_string.items())[:5]
        for k, v in sample_items:
            print(f"  {k} → {v}")
        
        # Test the parsing logic
        print("\n2. Testing parsing logic...")
        import collections
        string_to_uniprot = collections.defaultdict(list)
        
        for k, v in uniprot_to_string.items():
            if v:  # Make sure v is not empty
                for string_id in list(filter(None, v.split(";"))):
                    if "." in string_id:
                        protein_part = string_id.split(".")[1]
                        string_to_uniprot[protein_part].append(k)
        
        print(f"✅ Created mapping for {len(string_to_uniprot)} STRING proteins")
        
        # Show sample reverse mappings
        print("\nSample reverse mappings:")
        sample_reverse = list(string_to_uniprot.items())[:5]
        for string_id, uniprot_ids in sample_reverse:
            print(f"  {string_id} → {uniprot_ids}")
            
    except Exception as e:
        print(f"❌ Failed to download UniProt xref_string: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Testing SwissProt download...")
    try:
        swissprots = set(uniprot._all_uniprots("*", True))
        print(f"✅ Downloaded {len(swissprots)} SwissProt IDs")
        print(f"Sample SwissProt IDs: {list(swissprots)[:5]}")
    except Exception as e:
        print(f"❌ Failed to download SwissProt: {e}")
        
except ImportError as e:
    print(f"❌ Failed to import pypath: {e}")