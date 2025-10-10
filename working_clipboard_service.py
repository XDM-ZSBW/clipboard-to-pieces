#!/usr/bin/env python3
"""
Working Clipboard Service - File-based approach
Saves files to .pieces directory for Pieces.app auto-import
"""

import time
import os
import json
import base64
import tempfile
import shutil
import logging
import hashlib
import sys
from datetime import datetime
from pathlib import Path
import pyperclip
from PIL import Image
import io
import win32clipboard
import win32con

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('clipboard_service.log'),
        logging.StreamHandler()
    ]
)

class WorkingClipboardService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Pieces client for direct upload
        try:
            self.pieces_client = PiecesClient()
            self.logger.info("Connected to Pieces.app")
        except Exception as e:
            self.logger.error(f"Failed to connect to Pieces.app: {e}")
            self.pieces_client = None
        
        # Use .pieces directory for backup storage
        self.pieces_dir = Path.home() / ".pieces"
        self.pieces_dir.mkdir(exist_ok=True)
        
        # Track processed clipboard items with timestamps
        self.processed_items = {}
        self.max_cache_size = 100
        
        # Image compression settings
        self.max_image_size = 500000  # 500KB limit
        self.max_dimensions = (1920, 1080)  # Max width/height
        
        self.logger.info("Working Clipboard Monitoring Service Initialized")
        self.logger.info(f"Files will be saved to: {self.pieces_dir}")
        self.logger.info(f"Max image size: {self.max_image_size} bytes")
    
    def detect_clipboard_content_type(self):
        """Detect if clipboard contains text or image data"""
        try:
            # First try to get image data from Windows clipboard
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                    # Get image data from clipboard
                    image_data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                    win32clipboard.CloseClipboard()
                    
                    if image_data:
                        self.logger.debug("Detected Windows clipboard image data")
                        return "image", image_data
            except Exception as e:
                self.logger.debug(f"Windows clipboard check failed: {e}")
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass
            
            # Fallback to pyperclip for text and base64 images
            clipboard_content = pyperclip.paste()
            
            if not clipboard_content:
                return None, None
            
            # Check if it's image data (base64)
            if isinstance(clipboard_content, str):
                # Check for common image base64 patterns
                if (clipboard_content.startswith('iVBORw0KGgo') or  # PNG
                    clipboard_content.startswith('/9j/') or          # JPEG
                    clipboard_content.startswith('data:image/') or  # Data URL
                    len(clipboard_content) > 1000 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in clipboard_content[:100])):
                    self.logger.debug("Detected base64 image data")
                    return "image", clipboard_content
            
            # Check if it's text content
            if isinstance(clipboard_content, str) and len(clipboard_content.strip()) > 0:
                self.logger.debug("Detected text content")
                return "text", clipboard_content
            
            return None, None
            
        except Exception as e:
            self.logger.debug(f"Error checking clipboard: {e}")
            return None, None
    
    def compress_image(self, image_path):
        """Compress image to reduce size for upload"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large
                if img.size[0] > self.max_dimensions[0] or img.size[1] > self.max_dimensions[1]:
                    img.thumbnail(self.max_dimensions, Image.Resampling.LANCZOS)
                    self.logger.info(f"Resized image to {img.size}")
                
                # Save compressed version
                compressed_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                
                # Try different quality levels to get under size limit
                for quality in [90, 85, 70, 50]:
                    img.save(compressed_path.name, 'JPEG', quality=quality, optimize=True)
                    
                    # Check file size
                    file_size = os.path.getsize(compressed_path.name)
                    self.logger.info(f"Compressed image: {file_size} bytes (quality: {quality})")
                    
                    if file_size <= self.max_image_size:
                        break
                
                return compressed_path.name
                
        except Exception as e:
            self.logger.error(f"Error compressing image: {e}")
            return None
    
    def save_image_to_file(self, image_data):
        """Save clipboard image data to temporary file"""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = Path(temp_file.name)
            
            # Handle different image data formats
            if isinstance(image_data, bytes):
                # Windows clipboard image data
                temp_file.write(image_data)
            elif image_data.startswith('data:image/'):
                # Data URL format
                base64_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(base64_data)
                temp_file.write(image_bytes)
            elif image_data.startswith('iVBORw0KGgo'):
                # PNG base64
                image_bytes = base64.b64decode(image_data)
                temp_file.write(image_bytes)
            else:
                # Assume base64
                image_bytes = base64.b64decode(image_data)
                temp_file.write(image_bytes)
            
            temp_file.close()
            
            # Verify it's a valid image
            try:
                with Image.open(temp_path) as img:
                    img.verify()
                self.logger.info(f"Saved valid image: {temp_path}")
                return temp_path
            except Exception:
                os.unlink(temp_path)
                self.logger.warning("Invalid image data in clipboard")
                return None
                
        except Exception as e:
            self.logger.error(f"Error saving clipboard image: {e}")
            return None
    
    def create_filename(self, content_type):
        """Create a unique filename based on content type"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if content_type == "image":
            return f"Screenshot_{timestamp}.jpg"  # Use JPG for compressed images
        else:
            return f"Text_{timestamp}.txt"
    
    def upload_to_pieces(self, content_or_path, content_type):
        """Upload content directly to Pieces.app"""
        try:
            if self.pieces_client is None:
                self.logger.warning("Pieces client not available, skipping upload")
                return None
            
            # Create metadata
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.JPG if content_type == "image" else ClassificationSpecificEnum.TXT,
                tags=["clipboard", "auto-imported"],
                description=f"{content_type.title()} content captured from clipboard: {datetime.now().isoformat()}"
            )
            
            # Upload based on content type
            if content_type == "text":
                asset_id = self.pieces_client.create_asset(content_or_path, metadata)
            else:
                # For images, upload the file path
                asset_id = self.pieces_client.create_asset(content_or_path, metadata)
            
            self.logger.info(f"SUCCESS: Uploaded to Pieces.app with ID: {asset_id}")
            return asset_id
            
        except Exception as e:
            self.logger.error(f"Error uploading to Pieces.app: {e}")
            return None
    
    def save_to_pieces_dir(self, content_or_path, filename, content_type):
        """Save files to .pieces directory as backup"""
        try:
            # Create the file in .pieces directory
            file_path = self.pieces_dir / filename
            
            if content_type == "text":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content_or_path)
            else:
                shutil.copy2(content_or_path, file_path)
            
            # Create metadata file
            metadata_path = self.pieces_dir / f"{filename}.pieces.json"
            metadata = {
                "filename": filename,
                "content_type": content_type,
                "timestamp": datetime.now().isoformat(),
                "source": "clipboard_monitor"
            }
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Saved backup files to: {self.pieces_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving to .pieces directory: {e}")
            return False
    
    def process_clipboard_item(self, content_type, content):
        """Process clipboard item based on its type"""
        try:
            # Create unique identifier for this clipboard item
            if isinstance(content, bytes):
                item_hash = hashlib.md5(content).hexdigest()
            else:
                item_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            current_time = datetime.now()
            
            # Check if we've processed this exact item recently (within last 30 seconds)
            if item_hash in self.processed_items:
                last_processed = self.processed_items[item_hash]
                time_diff = (current_time - last_processed).total_seconds()
                
                if time_diff < 30:  # 30 seconds
                    self.logger.debug(f"Item processed {time_diff:.1f}s ago, skipping duplicate")
                    return None  # Return None to indicate no processing was done
                else:
                    self.logger.debug(f"Item processed {time_diff:.1f}s ago, processing again")
            
            self.logger.info(f"Processing new {content_type} content...")
            
            # Create filename
            filename = self.create_filename(content_type)
            
            if content_type == "text":
                # Upload text content directly to Pieces.app
                asset_id = self.upload_to_pieces(content, content_type)
                
                # Also save as backup
                save_success = self.save_to_pieces_dir(content, filename, content_type)
                
            elif content_type == "image":
                # Save image to temporary file
                temp_image_path = self.save_image_to_file(content)
                if not temp_image_path:
                    self.logger.warning("Failed to save clipboard image")
                    return False
                
                try:
                    # Compress the image
                    compressed_path = self.compress_image(temp_image_path)
                    if not compressed_path:
                        self.logger.error("Failed to compress image")
                        return False
                    
                    # Upload compressed image directly to Pieces.app
                    asset_id = self.upload_to_pieces(compressed_path, content_type)
                    
                    # Also save as backup
                    save_success = self.save_to_pieces_dir(compressed_path, filename, content_type)
                    
                finally:
                    # Clean up temporary files
                    try:
                        os.unlink(temp_image_path)
                    except:
                        pass
                    try:
                        if compressed_path:
                            os.unlink(compressed_path)
                    except:
                        pass
            else:
                self.logger.warning(f"Unknown content type: {content_type}")
                return False
            
            # Mark as processed if upload or save was successful
            if asset_id or save_success:
                self.processed_items[item_hash] = current_time
                
                if asset_id:
                    self.logger.info(f"SUCCESS: {content_type.title()} content uploaded to Pieces.app")
                    self.logger.info(f"Asset ID: {asset_id}")
                if save_success:
                    self.logger.info(f"SUCCESS: {content_type.title()} content saved as backup")
                
                # Clean up old entries to prevent memory growth
                if len(self.processed_items) > self.max_cache_size:
                    sorted_items = sorted(self.processed_items.items(), key=lambda x: x[1])
                    for key, _ in sorted_items[:len(sorted_items) - self.max_cache_size]:
                        del self.processed_items[key]
                
                return True
            else:
                self.logger.error(f"FAILED: {content_type.title()} content upload/save failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {content_type} content: {e}")
            return False
    
    def run_service(self, check_interval=2):
        """Run the clipboard monitoring service"""
        self.logger.info(f"Starting working clipboard monitoring service (checking every {check_interval} seconds)")
        
        try:
            while True:
                try:
                    # Check clipboard content type
                    content_type, content = self.detect_clipboard_content_type()
                    
                    if content_type and content:
                        self.logger.debug(f"{content_type.title()} detected in clipboard ({len(content)} chars)")
                        
                        # Process the clipboard item
                        success = self.process_clipboard_item(content_type, content)
                        
                        # Only log if there was an actual processing attempt (not just skipped duplicate)
                        if success is not None:
                            if success:
                                self.logger.info(f"{content_type.title()} content successfully saved!")
                            else:
                                self.logger.warning(f"{content_type.title()} content save failed")
                    
                    # Wait before next check
                    time.sleep(check_interval)
                    
                except KeyboardInterrupt:
                    self.logger.info("Service stopped by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in service loop: {e}")
                    time.sleep(check_interval)
                    
        except KeyboardInterrupt:
            self.logger.info("Service stopped")
        finally:
            self.logger.info("Service shutdown complete")

def main():
    print("Working Clipboard Monitoring Service")
    print("=" * 60)
    print("This service monitors clipboard and uploads directly to Pieces.app")
    print("with backup files saved to .pieces directory")
    print("- Text content -> uploaded directly to Pieces.app")
    print("- Screenshots -> compressed and uploaded directly to Pieces.app")
    print("- Backup files saved to: C:\\Users\\dash\\.pieces")
    print("=" * 60)
    
    # Check .pieces directory
    service = WorkingClipboardService()
    
    if not service.pieces_dir.exists():
        print(f"Creating .pieces directory: {service.pieces_dir}")
        service.pieces_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created: {service.pieces_dir}")
    
    print("\nService ready! Copy text or take screenshots.")
    print("The service will automatically detect and upload them directly to Pieces.app.")
    print("Backup files will be saved to .pieces directory.")
    print("Press Ctrl+C to stop the service.")
    
    # Start service
    service.run_service()

if __name__ == "__main__":
    main()
