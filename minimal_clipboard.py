#!/usr/bin/env python3
"""
Minimal Clipboard to Pieces Service
Ultra-simple approach focused on core functionality
"""

import time
import hashlib
import base64
import tempfile
import os
from datetime import datetime
from pathlib import Path
import pyperclip
from PIL import Image

# Pieces OS imports
from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata

def main():
    print("Minimal Clipboard Service Starting...")
    
    # Initialize Pieces client
    try:
        client = PiecesClient()
        print("Connected to Pieces.app")
    except Exception as e:
        print(f"Failed to connect to Pieces.app: {e}")
        return
    
    # Create directory
    pieces_dir = Path.home() / ".clipboard-to-pieces"
    pieces_dir.mkdir(exist_ok=True)
    print(f"Files saved to: {pieces_dir}")
    
    processed_items = {}
    
    print("Service ready! Copy text or take screenshots.")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            try:
                # Get clipboard content
                content = pyperclip.paste()
                
                if not content:
                    time.sleep(2)
                    continue
                
                # Check for duplicates
                content_hash = hashlib.md5(content.encode()).hexdigest()
                if content_hash in processed_items:
                    if time.time() - processed_items[content_hash] < 30:
                        time.sleep(2)
                        continue
                
                processed_items[content_hash] = time.time()
                
                # Determine content type
                if content.startswith('iVBORw0KGgo') or content.startswith('/9j/'):
                    # Base64 image
                    print("Processing image content...")
                    
                    # Save image to temp file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                        image_data = base64.b64decode(content)
                        tmp_file.write(image_data)
                        temp_path = tmp_file.name
                    
                    # Try file path method first
                    try:
                        metadata = FragmentMetadata(
                            ext=ClassificationSpecificEnum.JPG,
                            tags=["image", "clipboard", "minimal"],
                            description=f"Image from clipboard: {datetime.now().isoformat()}"
                        )
                        asset_id = client.create_asset(temp_path, metadata)
                        print(f"SUCCESS: Image imported via file path: {asset_id}")
                    except Exception as e:
                        print(f"File path method failed: {e}")
                        # Fallback to base64
                        try:
                            asset_id = client.create_asset(content, metadata)
                            print(f"SUCCESS: Image imported via base64: {asset_id}")
                        except Exception as e2:
                            print(f"Base64 method also failed: {e2}")
                    
                    # Save locally
                    filename = f"Image_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
                    file_path = pieces_dir / filename
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Clean up
                    os.unlink(temp_path)
                    
                else:
                    # Text content
                    print(f"Processing text content ({len(content)} chars)...")
                    
                    # Create metadata
                    metadata = FragmentMetadata(
                        ext=ClassificationSpecificEnum.TXT,
                        tags=["text", "clipboard", "minimal"],
                        description=f"Text from clipboard: {datetime.now().isoformat()}"
                    )
                    
                    # Import to Pieces
                    asset_id = client.create_asset(content, metadata)
                    print(f"SUCCESS: Text imported: {asset_id}")
                    
                    # Save locally
                    filename = f"Text_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
                    file_path = pieces_dir / filename
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
            except Exception as e:
                print(f"Error processing clipboard: {e}")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nService stopped.")
    except Exception as e:
        print(f"Service error: {e}")

if __name__ == "__main__":
    main()


