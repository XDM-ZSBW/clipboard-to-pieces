#!/usr/bin/env python3
"""
Debug Clipboard Service - with verbose output
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
    print("=== Debug Clipboard Service Starting ===")
    
    # Initialize Pieces client
    try:
        client = PiecesClient()
        print("+ Connected to Pieces.app")
    except Exception as e:
        print(f"- Failed to connect to Pieces.app: {e}")
        return
    
    # Create directory
    pieces_dir = Path.home() / ".clipboard-to-pieces"
    pieces_dir.mkdir(exist_ok=True)
    print(f"+ Files will be saved to: {pieces_dir}")
    
    processed_items = {}
    
    print("+ Service ready! Copy text or take screenshots.")
    print("+ Press Ctrl+C to stop.")
    print("+ Monitoring clipboard every 2 seconds...")
    
    try:
        while True:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking clipboard...")
            
            try:
                # Get clipboard content
                content = pyperclip.paste()
                
                if not content:
                    print("  - Clipboard is empty")
                    time.sleep(2)
                    continue
                
                print(f"  - Clipboard has content: {len(content)} chars")
                
                # Check for duplicates
                content_hash = hashlib.md5(content.encode()).hexdigest()
                if content_hash in processed_items:
                    last_time = processed_items[content_hash]
                    time_diff = time.time() - last_time
                    if time_diff < 30:
                        print(f"  - Duplicate content detected (processed {time_diff:.1f}s ago)")
                        time.sleep(2)
                        continue
                
                processed_items[content_hash] = time.time()
                print(f"  - New content detected, processing...")
                
                # Determine content type
                if content.startswith('iVBORw0KGgo') or content.startswith('/9j/'):
                    # Base64 image
                    print("  - Detected image content")
                    
                    # Save image to temp file
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                        image_data = base64.b64decode(content)
                        tmp_file.write(image_data)
                        temp_path = tmp_file.name
                    
                    print(f"  - Saved temp image: {temp_path}")
                    
                    # Try file path method first
                    try:
                        metadata = FragmentMetadata(
                            ext=ClassificationSpecificEnum.JPG,
                            tags=["image", "clipboard", "debug"],
                            description=f"Image from clipboard: {datetime.now().isoformat()}"
                        )
                        asset_id = client.create_asset(temp_path, metadata)
                        print(f"  + SUCCESS: Image imported via file path: {asset_id}")
                    except Exception as e:
                        print(f"  - File path method failed: {e}")
                        # Fallback to base64
                        try:
                            asset_id = client.create_asset(content, metadata)
                            print(f"  + SUCCESS: Image imported via base64: {asset_id}")
                        except Exception as e2:
                            print(f"  - Base64 method also failed: {e2}")
                    
                    # Save locally
                    filename = f"Image_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
                    file_path = pieces_dir / filename
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    print(f"  + Saved locally: {file_path}")
                    
                    # Clean up
                    os.unlink(temp_path)
                    
                else:
                    # Text content
                    print(f"  - Detected text content: {len(content)} chars")
                    
                    # Create metadata
                    metadata = FragmentMetadata(
                        ext=ClassificationSpecificEnum.TXT,
                        tags=["text", "clipboard", "debug"],
                        description=f"Text from clipboard: {datetime.now().isoformat()}"
                    )
                    
                    # Import to Pieces
                    try:
                        asset_id = client.create_asset(content, metadata)
                        print(f"  + SUCCESS: Text imported: {asset_id}")
                    except Exception as e:
                        print(f"  - Text import failed: {e}")
                    
                    # Save locally
                    filename = f"Text_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
                    file_path = pieces_dir / filename
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  + Saved locally: {file_path}")
                
                print("  - Processing complete")
                
            except Exception as e:
                print(f"  - Error processing clipboard: {e}")
            
            print("  - Waiting 2 seconds...")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n+ Service stopped by user.")
    except Exception as e:
        print(f"\n- Service error: {e}")

if __name__ == "__main__":
    main()
