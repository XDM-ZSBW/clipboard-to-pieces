#!/usr/bin/env python3
"""
Simple Clipboard to Pieces Service
Minimal implementation focused on core functionality
"""

import time
import os
import hashlib
import base64
import tempfile
from datetime import datetime
from pathlib import Path
import pyperclip
from PIL import Image
import win32clipboard
import win32con

# Pieces OS imports
from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata

class SimpleClipboardService:
    def __init__(self):
        self.client = PiecesClient()
        self.processed_items = {}
        self.pieces_dir = Path.home() / ".clipboard-to-pieces"
        self.pieces_dir.mkdir(exist_ok=True)
        
        print("Simple Clipboard Service initialized")
        print(f"Files will be saved to: {self.pieces_dir}")
    
    def detect_clipboard_content(self):
        """Detect clipboard content type"""
        try:
            # Try Windows clipboard for images
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                image_data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                win32clipboard.CloseClipboard()
                if image_data:
                    return "image", image_data
            win32clipboard.CloseClipboard()
        except:
            pass
        
        # Try pyperclip for text
        try:
            content = pyperclip.paste()
            if content:
                # Check if it's base64 image
                if (content.startswith('iVBORw0KGgo') or content.startswith('/9j/')):
                    return "image", content
                return "text", content
        except:
            pass
        
        return None, None
    
    def process_text(self, text_content):
        """Process text content"""
        try:
            # Create metadata
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.TXT,
                tags=["text", "clipboard", "simple"],
                description=f"Text from clipboard: {datetime.now().isoformat()}"
            )
            
            # Import to Pieces
            asset_id = self.client.create_asset(text_content, metadata)
            print(f"Text imported: {asset_id}")
            
            # Save locally
            filename = f"Text_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
            file_path = self.pieces_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            return asset_id
            
        except Exception as e:
            print(f"Error processing text: {e}")
            return None
    
    def process_image(self, image_content):
        """Process image content"""
        try:
            # Save image to temp file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                if isinstance(image_content, str):
                    # Base64 content
                    image_data = base64.b64decode(image_content)
                    tmp_file.write(image_data)
                else:
                    # Binary content
                    tmp_file.write(image_content)
                temp_path = tmp_file.name
            
            # Try simple file upload approach
            try:
                metadata = FragmentMetadata(
                    ext=ClassificationSpecificEnum.JPG,
                    tags=["image", "clipboard", "simple"],
                    description=f"Image from clipboard: {datetime.now().isoformat()}"
                )
                
                # Use create_asset with file path
                asset_id = self.client.create_asset(temp_path, metadata)
                print(f"Image imported via file path: {asset_id}")
                
            except Exception as e:
                print(f"File path method failed: {e}")
                
                # Fallback: read file and use base64
                with open(temp_path, 'rb') as f:
                    image_data = f.read()
                
                base64_data = base64.b64encode(image_data).decode('utf-8')
                asset_id = self.client.create_asset(base64_data, metadata)
                print(f"Image imported via base64: {asset_id}")
            
            # Save locally
            filename = f"Image_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
            file_path = self.pieces_dir / filename
            if isinstance(image_content, str):
                with open(file_path, 'wb') as f:
                    f.write(base64.b64decode(image_content))
            else:
                with open(file_path, 'wb') as f:
                    f.write(image_content)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return asset_id
            
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    
    def run(self):
        """Main service loop"""
        print("Service ready! Copy text or take screenshots.")
        print("Press Ctrl+C to stop.")
        
        try:
            while True:
                content_type, content = self.detect_clipboard_content()
                
                if content is None:
                    time.sleep(2)
                    continue
                
                # Check for duplicates
                content_hash = hashlib.md5(str(content).encode()).hexdigest()
                if content_hash in self.processed_items:
                    if time.time() - self.processed_items[content_hash] < 30:  # 30 seconds
                        time.sleep(2)
                        continue
                
                self.processed_items[content_hash] = time.time()
                
                print(f"Processing {content_type} content...")
                
                if content_type == "text":
                    self.process_text(content)
                elif content_type == "image":
                    self.process_image(content)
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\nService stopped.")
        except Exception as e:
            print(f"Service error: {e}")

if __name__ == "__main__":
    service = SimpleClipboardService()
    service.run()


