#!/usr/bin/env python3
"""
Test direct upload to Pieces.app using file path
"""

import os
import tempfile
from pathlib import Path
from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata

def test_direct_upload():
    print("Testing direct upload to Pieces.app...")
    
    try:
        client = PiecesClient()
        print("+ Connected to Pieces.app")
        
        # Create a test image file
        test_image_path = Path.home() / ".pieces" / "Screenshot_2025-10-09_19-14-29.jpg"
        
        if not test_image_path.exists():
            print(f"- Test image not found: {test_image_path}")
            return False
        
        print(f"+ Found test image: {test_image_path}")
        
        # Try different upload methods
        methods = [
            ("create_asset with file path", lambda: client.create_asset(str(test_image_path), None)),
            ("create_asset with binary data", lambda: client.create_asset(test_image_path.read_bytes(), None)),
            ("assets_api.assets_create_new_asset_from_file", lambda: client.assets_api.assets_create_new_asset_from_file(str(test_image_path))),
        ]
        
        for method_name, method_func in methods:
            try:
                print(f"  Testing: {method_name}")
                result = method_func()
                print(f"  + SUCCESS: {result}")
                return True
            except Exception as e:
                print(f"  - FAILED: {e}")
        
        return False
        
    except Exception as e:
        print(f"- Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_direct_upload()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
    exit(0 if success else 1)

