#!/usr/bin/env python3
"""
Robust Clipboard Service with Image Compression
Handles large images by compressing them before upload
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
import msvcrt
from datetime import datetime
from pathlib import Path
import pyperclip
from PIL import Image
import io
import win32clipboard
import win32con
from pieces_os_client.wrapper import PiecesClient
from pieces_os_client.models.classification_specific_enum import ClassificationSpecificEnum
from pieces_os_client.models.fragment_metadata import FragmentMetadata
from pieces_os_client.models.seed import Seed
from pieces_os_client.models.seeded_asset import SeededAsset
from pieces_os_client.models.seeded_format import SeededFormat
from pieces_os_client.models.seeded_file import SeededFile
from pieces_os_client.models.transferable_bytes import TransferableBytes
from pieces_os_client.models.seeded_classification import SeededClassification
from pieces_os_client.models.application import Application
from pieces_os_client.models.application_name_enum import ApplicationNameEnum
from pieces_os_client.models.platform_enum import PlatformEnum
from pieces_os_client.models.privacy_enum import PrivacyEnum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'robust_clipboard_service.log')),
        logging.StreamHandler()
    ]
)

class RobustClipboardService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pieces_client = PiecesClient(host="http://localhost:39300")
        
        # Only use .pieces directory for persistence
        self.pieces_dir = Path.home() / ".pieces"
        self.pieces_dir.mkdir(exist_ok=True)
        
        # Track processed clipboard items with timestamps
        self.processed_items = {}
        self.max_cache_size = 100
        
        # Get application info once
        self.application = self._get_application()
        
        # Image compression settings
        self.max_image_size = 100000  # 100KB limit
        self.max_dimensions = (1920, 1080)  # Max width/height
        
        self.logger.info("Robust Clipboard Monitoring Service Initialized")
        self.logger.info(f"Will import text as text, screenshots as compressed binary files")
        self.logger.info(f"Files will be saved in: {self.pieces_dir}")
        if self.application:
            self.logger.info(f"Using application: {self.application.name}")
        else:
            self.logger.warning("No application available - image imports may fail")
        self.logger.info(f"Max image size: {self.max_image_size} bytes")
    
    def _get_application(self):
        """Get the current application for asset creation"""
        try:
            applications = self.pieces_client.applications_api.applications_snapshot()
            if applications.iterable and len(applications.iterable) > 0:
                # Try to find a working application
                for app in applications.iterable:
                    try:
                        # Test if this application works by checking its properties
                        if hasattr(app, 'name') and app.name:
                            self.logger.info(f"Using existing application: {app.name}")
                            return app
                    except Exception as app_error:
                        self.logger.warning(f"Application {app} failed validation: {app_error}")
                        continue
                
                # If no working application found, create default
                self.logger.warning("No working applications found, creating default")
                return self._create_default_application()
            else:
                self.logger.warning("No applications found, creating default OS_SERVER application")
                return self._create_default_application()
        except Exception as e:
            self.logger.warning(f"Failed to get application info: {e}")
            self.logger.info("Creating default application for asset creation")
            return self._create_default_application()
    
    def _create_default_application(self):
        """Create a default application for asset creation"""
        try:
            # Create a complete application object with all required fields
            default_app = Application(
                id="clipboard-to-pieces-service",
                name=ApplicationNameEnum.OS_SERVER,
                version="2.0.0",
                platform=PlatformEnum.WINDOWS,
                onboarded=True,
                privacy=PrivacyEnum.CLOSED
            )
            self.logger.info("Created default OS_SERVER application")
            return default_app
        except Exception as e:
            self.logger.error(f"Failed to create default application: {e}")
            return None
    
    def clear_processed_cache(self):
        """Clear the processed items cache for testing"""
        self.processed_items.clear()
        self.logger.info("Processed items cache cleared")
    
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
                for quality in [85, 70, 50, 30]:
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
    
    def import_text_content(self, text_content):
        """Import text content to Pieces OS as text (simple method)"""
        try:
            self.logger.info(f"Importing text content ({len(text_content)} chars)")
            
            # Create metadata for text
            metadata = FragmentMetadata(
                ext=ClassificationSpecificEnum.TXT,
                tags=["text", "clipboard", "auto-imported"],
                description=f"Text content captured from clipboard: {datetime.now().isoformat()}"
            )
            
            # Create asset with text content (simple method)
            asset_id = self.pieces_client.create_asset(text_content, metadata)
            
            self.logger.info(f"SUCCESS: Text content imported with ID: {asset_id}")
            return asset_id
            
        except Exception as e:
            self.logger.error(f"Error importing text content: {e}")
            return None
    
    def import_image_as_binary_file(self, image_path, filename):
        """Import image file to Pieces OS using proper binary upload with compression"""
        try:
            self.logger.info(f"Importing image file as compressed binary: {filename}")
            
            # Compress the image first
            compressed_path = self.compress_image(image_path)
            if not compressed_path:
                self.logger.error("Failed to compress image")
                return None
            
            try:
                # Read compressed image file
                with open(compressed_path, 'rb') as f:
                    image_data = f.read()
                
                file_size = len(image_data)
                self.logger.info(f"Compressed image size: {file_size} bytes")
                
                if file_size > self.max_image_size:
                    self.logger.warning(f"Image still too large after compression: {file_size} bytes")
                    return None
                
                # Convert bytes to array of integers
                byte_array = list(image_data)
                self.logger.debug(f"Converted {file_size} bytes to {len(byte_array)} integers")
                
                # Create TransferableBytes
                transferable_bytes = TransferableBytes(raw=byte_array)
                
                # Create SeededFile
                seeded_file = SeededFile(bytes=transferable_bytes)
                
                # Create SeededClassification (use JPEG since we compressed to JPEG)
                seeded_classification = SeededClassification(specific=ClassificationSpecificEnum.JPG)
                
                # Create SeededFormat
                seeded_format = SeededFormat(
                    file=seeded_file,
                    classification=seeded_classification
                )
                
                # Try creating SeededAsset without application first
                try:
                    seeded_asset = SeededAsset(
                        format=seeded_format
                    )
                    self.logger.info("Created SeededAsset without application")
                except Exception as e:
                    self.logger.warning(f"Failed to create SeededAsset without application: {e}")
                    if self.application is None:
                        self.logger.error("No application available for image import - skipping image")
                        return None
                    
                    try:
                        seeded_asset = SeededAsset(
                            application=self.application,
                            format=seeded_format
                        )
                        self.logger.info("Created SeededAsset with application")
                    except Exception as e2:
                        self.logger.error(f"Failed to create SeededAsset with application: {e2}")
                        return None
                
                # Create Seed
                seed = Seed(asset=seeded_asset)
                
                # Try simple create_asset method first (like text imports)
                try:
                    self.logger.info("Trying simple create_asset method for image...")
                    # Read the compressed image file
                    with open(compressed_path, 'rb') as f:
                        image_data = f.read()
                    
                    # Create metadata for image
                    metadata = FragmentMetadata(
                        ext=ClassificationSpecificEnum.JPG,
                        tags=["image", "clipboard", "auto-imported", "compressed"],
                        description=f"Compressed image captured from clipboard: {datetime.now().isoformat()}"
                    )
                    
                    # Use simple create_asset method (same as text)
                    result_id = self.pieces_client.create_asset(image_data, metadata)
                    self.logger.info(f"Simple method successful: {result_id}")
                    return result_id
                    
                except Exception as simple_error:
                    self.logger.warning(f"Simple method failed: {simple_error}")
                    # Fall back to complex binary upload method
                    try:
                        self.logger.info("Trying complex binary upload method...")
                        result = self.pieces_client.assets_api.assets_create_new_asset(
                            transferables=True,
                            seed=seed,
                            _request_timeout=30
                        )
                        self.logger.info(f"Complex method successful: {result.id}")
                        return result.id
                    except Exception as complex_error:
                        self.logger.error(f"Complex method also failed: {complex_error}")
                        return None
                
            finally:
                # Clean up compressed file
                try:
                    os.unlink(compressed_path)
                except:
                    pass
            
        except Exception as e:
            self.logger.error(f"Error importing image file: {e}")
            if hasattr(e, 'response'):
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response text: {e.response.text}")
            return None
    
    def save_to_pieces_dir(self, content_or_path, filename, content_type):
        """Save files to .pieces directory only"""
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
            
            self.logger.info(f"Saved files to: {self.pieces_dir}")
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
            
            # Check if we've processed this exact item recently (within last 30 minutes)
            if item_hash in self.processed_items:
                last_processed = self.processed_items[item_hash]
                time_diff = (current_time - last_processed).total_seconds()
                
                if time_diff < 1800:  # 30 minutes
                    self.logger.debug(f"Item processed {time_diff:.1f}s ago, skipping duplicate")
                    return None  # Return None to indicate no processing was done
                else:
                    self.logger.debug(f"Item processed {time_diff:.1f}s ago, processing again")
            
            self.logger.info(f"Processing new {content_type} content...")
            
            # Create filename
            filename = self.create_filename(content_type)
            
            if content_type == "text":
                # Import text content (simple method)
                asset_id = self.import_text_content(content)
                
                # Save to .pieces directory
                save_success = self.save_to_pieces_dir(content, filename, content_type)
                
            elif content_type == "image":
                # Save image to temporary file
                temp_image_path = self.save_image_to_file(content)
                if not temp_image_path:
                    self.logger.warning("Failed to save clipboard image")
                    return False
                
                try:
                    # Import image as compressed binary file (proper method)
                    asset_id = self.import_image_as_binary_file(temp_image_path, filename)
                    
                    # Save original to .pieces directory
                    save_success = self.save_to_pieces_dir(temp_image_path, filename, content_type)
                    
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_image_path)
                    except:
                        pass
            else:
                self.logger.warning(f"Unknown content type: {content_type}")
                return False
            
            # Mark as processed if file was saved successfully (regardless of API success)
            if save_success:
                self.processed_items[item_hash] = current_time
                
                if asset_id:
                    self.logger.info(f"SUCCESS: {content_type.title()} content imported as {filename}")
                    self.logger.info(f"Asset ID: {asset_id}")
                    self.logger.info(f"Files saved to .pieces directory")
                else:
                    self.logger.info(f"SUCCESS: {content_type.title()} content saved to .pieces directory")
                    self.logger.info(f"Note: API import failed, but file saved for Pieces.app auto-import")
                
                # Clean up old entries to prevent memory growth
                if len(self.processed_items) > self.max_cache_size:
                    sorted_items = sorted(self.processed_items.items(), key=lambda x: x[1])
                    for key, _ in sorted_items[:len(sorted_items) - self.max_cache_size]:
                        del self.processed_items[key]
                
                return True
            else:
                self.logger.error(f"FAILED: {content_type.title()} content save failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {content_type} content: {e}")
            return False
    
    def run_service(self, check_interval=2):
        """Run the clipboard monitoring service"""
        self.logger.info(f"Starting robust clipboard monitoring service (checking every {check_interval} seconds)")
        
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
                                self.logger.info(f"{content_type.title()} content successfully imported!")
                            else:
                                self.logger.warning(f"{content_type.title()} content import failed")
                    
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
            self.pieces_client.close()
            self.logger.info("Service shutdown complete")

def main():
    # Create a lock file to prevent multiple instances (Windows compatible)
    lock_file_path = Path(__file__).parent / "clipboard_service.lock"
    
    try:
        # Try to create and lock the file (Windows compatible)
        lock_file = open(lock_file_path, 'w')
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        
        print("Robust Clipboard Monitoring Service")
        print("=" * 60)
        print("⚠️  SECURITY WARNING: This service monitors ALL clipboard content!")
        print("⚠️  Sensitive data (passwords, API keys, etc.) will be captured!")
        print("⚠️  Use only on trusted development machines!")
        print("=" * 60)
        print("This service monitors clipboard and imports:")
        print("- Text content -> as text assets (simple method)")
        print("- Screenshots -> as compressed binary file uploads (robust method)")
        print("- Fixed duplicate detection (30 minute window)")
        print("- Fixed Windows + Shift + A screenshot detection")
        print("- Image compression for large screenshots")
        print("- Files saved to: C:\\Users\\dash\\.pieces")
        print("=" * 60)
        
        # Check .pieces directory
        service = RobustClipboardService()
        
        if not service.pieces_dir.exists():
            print(f"Creating .pieces directory: {service.pieces_dir}")
            service.pieces_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created: {service.pieces_dir}")
        
        print("\nService ready! Copy text or take screenshots.")
        print("The service will automatically detect and import them correctly.")
        print("Large images will be compressed for reliable upload!")
        print("Press Ctrl+C to stop the service.")
        
        # Start service
        service.run_service()
        
    except (IOError, OSError):
        print("ERROR: Another instance of the clipboard service is already running!")
        print("Please stop the existing service before starting a new one.")
        print("Use 'taskkill /f /im python.exe' to stop all instances if needed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
