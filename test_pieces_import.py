#!/usr/bin/env python3
"""
Test Pieces import functionality
"""

import pyperclip
import base64
import tempfile
import os
from datetime import datetime
from pathlib import Path

# Pieces OS imports
from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata

def test_text_import():
    print("Testing text import...")
    
    try:
        client = PiecesClient()
        print("+ Connected to Pieces.app")
        
        # Test text content
        test_text = "This is a test text import from clipboard service"
        
        metadata = FragmentMetadata(
            ext=ClassificationSpecificEnum.TXT,
            tags=["test", "text", "clipboard"],
            description=f"Test text import: {datetime.now().isoformat()}"
        )
        
        asset_id = client.create_asset(test_text, metadata)
        print(f"+ SUCCESS: Text imported with ID: {asset_id}")
        return True
        
    except Exception as e:
        print(f"- Text import failed: {e}")
        return False

def test_image_import():
    print("Testing image import...")
    
    try:
        client = PiecesClient()
        print("+ Connected to Pieces.app")
        
        # Create a simple test image (1x1 pixel PNG)
        test_image_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(test_image_data)
            temp_path = tmp_file.name
        
        print(f"+ Created test image: {temp_path}")
        
        # Try file path method
        try:
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.JPG,
                tags=["test", "image", "clipboard"],
                description=f"Test image import: {datetime.now().isoformat()}"
            )
            
            asset_id = client.create_asset(temp_path, metadata)
            print(f"+ SUCCESS: Image imported via file path with ID: {asset_id}")
            return True
            
        except Exception as e:
            print(f"- File path method failed: {e}")
            
            # Try base64 method
            try:
                base64_data = base64.b64encode(test_image_data).decode('utf-8')
                asset_id = client.create_asset(base64_data, metadata)
                print(f"+ SUCCESS: Image imported via base64 with ID: {asset_id}")
                return True
                
            except Exception as e2:
                print(f"- Base64 method also failed: {e2}")
                return False
        
        finally:
            # Clean up
            os.unlink(temp_path)
        
    except Exception as e:
        print(f"- Image import failed: {e}")
        return False

def main():
    print("=== Pieces Import Test ===")
    
    # Test text import
    text_ok = test_text_import()
    print()
    
    # Test image import
    image_ok = test_image_import()
    print()
    
    print("=== Test Results ===")
    print(f"Text import: {'+ PASS' if text_ok else '- FAIL'}")
    print(f"Image import: {'+ PASS' if image_ok else '- FAIL'}")
    
    if text_ok and image_ok:
        print("\n+ All tests passed! Pieces import is working.")
        return True
    else:
        print("\n- Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

