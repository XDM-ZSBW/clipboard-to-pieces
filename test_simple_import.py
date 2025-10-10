#!/usr/bin/env python3
"""
Test simple Pieces import
"""

from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata

def main():
    print("Testing simple Pieces import...")
    
    try:
        client = PiecesClient()
        print("+ Connected to Pieces.app")
        
        # Test simple text import
        test_content = "Hello from clipboard service test"
        
        metadata = FragmentMetadata(
            ext=ClassificationSpecificEnum.TXT,
            tags=["test"],
            description="Simple test import"
        )
        
        print("+ Calling create_asset...")
        result = client.create_asset(test_content, metadata)
        print(f"+ SUCCESS: Imported with result: {result}")
        print(f"+ Result type: {type(result)}")
        
        return True
        
    except Exception as e:
        print(f"- Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    exit(0 if success else 1)

